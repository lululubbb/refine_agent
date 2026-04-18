"""
refine_agent.py  (Issues 2 & 3 fixes)

Issue 2 fix (redundancy score):
  bigSims.csv 'redundancy_score' column = 1 - similarity (higher = more redundant).
  The previous code did `diags[tc].redundancy_score = 1 - round(score, 4)`,
  inverting it AGAIN back to similarity.  Fixed to store it directly.

  scoring.py checks `if diag.redundancy_score > 0.7 → HIGH_REDUNDANCY`.
  With the correct value (redundancy = 1 - similarity, higher = worse),
  the threshold logic is correct: > 0.7 means highly redundant.

Issue 3 fix (per-test priority, not suite-level):
  Previously, issues_at_priority_level() was applied across ALL tests to find
  the globally highest priority, then only tests with that priority were sent
  to the Refiner.  This caused: if Test A has COMPILE_FAIL and Test B has
  EXEC_FAIL, only Test A was repaired.

  Fix: EVERY problematic test is sent to the Refiner.  The per-test top
  priority is computed individually and stored in the diagnostic data so the
  Refiner LLM knows which issue to tackle first for each test.
"""
from __future__ import annotations

import csv
import glob
import json
import logging
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from jinja2 import Environment, FileSystemLoader

from llm_client import LLMClient, LLMCallResult
from scoring import TestScore, SuiteScore, sort_issues_by_priority, issues_at_priority_level
from compile_error_analyzer import enrich_diag_with_fix_hints, get_error_summary
from scoring_ablation import (
    compute_test_score_ablation as compute_test_score,
    compute_suite_score_ablation as compute_suite_score,
    global_ablation_config,
)
_cfg = global_ablation_config()
logger = logging.getLogger(__name__)
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)


# ════════════════════════════════════════════════════════════════════
# TestDiag
# ════════════════════════════════════════════════════════════════════

@dataclass
class TestDiag:
    test_name: str

    compile_ok:     bool      = False
    exec_ok:        bool      = False
    exec_timeout:   bool      = False
    compile_errors: List[str] = field(default_factory=list)
    exec_errors:    List[str] = field(default_factory=list)

    focal_line_rate:   Optional[float] = None
    focal_branch_rate: Optional[float] = None
    focal_line_covered: Optional[int]  = None
    focal_line_total:   Optional[int]  = None

    missed_methods:    List[str] = field(default_factory=list)
    partial_methods:   List[str] = field(default_factory=list)

    bug_revealing: Optional[bool] = None
    redundancy_score: Optional[float] = None
    most_similar_to:  Optional[str]   = None

    diag_data_valid: bool = False

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class RefineResult:
    focal_method: str
    class_name:   str
    iteration:    int

    test_diags:  Dict[str, TestDiag]  = field(default_factory=dict)
    test_scores: Dict[str, TestScore] = field(default_factory=dict)
    suite_score: Optional[SuiteScore] = None

    instructions:  Dict[str, List[str]] = field(default_factory=dict)
    delete_tests:  List[str]            = field(default_factory=list)
    suite_summary: str                  = ""

    refiner_prompt_tokens:     int   = 0
    refiner_completion_tokens: int   = 0
    refiner_elapsed_seconds:   float = 0.0
    _files_written: int = field(default=0, repr=False)

    def has_actionable_instructions(self) -> bool:
        return bool(self.instructions) or bool(self.delete_tests)

    def to_dict(self) -> dict:
        return {
            "focal_method":  self.focal_method,
            "class_name":    self.class_name,
            "iteration":     self.iteration,
            "suite_score":   self.suite_score.to_dict() if self.suite_score else {},
            "suite_summary": self.suite_summary,
            "test_scores":   {k: v.to_dict() for k, v in self.test_scores.items()},
            "test_diags":    {k: v.to_dict() for k, v in self.test_diags.items()},
            "instructions":  self.instructions,
            "delete_tests":  self.delete_tests,
            "refiner_usage": {
                "prompt_tokens":     self.refiner_prompt_tokens,
                "completion_tokens": self.refiner_completion_tokens,
                "elapsed_seconds":   round(self.refiner_elapsed_seconds, 3),
            },
        }

    def save(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)


# ════════════════════════════════════════════════════════════════════
# Utilities
# ════════════════════════════════════════════════════════════════════

def _run(cmd: List[str], timeout: int = 120) -> Tuple[int, str, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"
    except Exception as e:
        return -2, "", str(e)


def _short(full_name: str) -> str:
    return full_name.rsplit(".", 1)[-1]


# ════════════════════════════════════════════════════════════════════
# Tool 1+2: Compile + Run + Coverage  (Issue 3 fix)
# ════════════════════════════════════════════════════════════════════

def tool_compile_run_and_coverage(
    focal_method_result_dir: str,
    project_dir: str,
    test_names: List[str],
) -> Tuple[Dict[str, TestDiag], Optional[str]]:
    from tool_runner_adapter import run_and_export, load_suite_diagnosis

    diags: Dict[str, TestDiag] = {n: TestDiag(test_name=n) for n in test_names}

    # 调用 TestRunner + 导出 suite_diagnosis.json
    tests_output_dir = run_and_export(focal_method_result_dir, project_dir)
    if not tests_output_dir:
        return diags, None

    # 读取统一 JSON（一次调用，包含 compile/exec/coverage 全部数据）
    diag_map = load_suite_diagnosis(tests_output_dir)
    if not diag_map:
        return diags, tests_output_dir

    matched = 0
    for tc_name, raw in diag_map.items():
        if tc_name not in diags:
            short = _short(tc_name)
            if short not in diags:
                continue
            tc_name = short
        d = diags[tc_name]
        cs = raw.get("compile_status", "unknown")
        es = raw.get("exec_status",    "unknown")
        d.compile_ok     = (cs == "pass")
        d.exec_ok        = (es == "pass")
        d.exec_timeout   = (es == "timeout")
        d.compile_errors = raw.get("compile_errors", [])
        d.exec_errors    = raw.get("exec_errors",    [])
        d.missed_methods = raw.get("missed_methods", [])
        d.partial_methods= raw.get("partial_methods",[])

        # Focal method line/branch rates
        lr = raw.get("focal_line_rate")
        br = raw.get("focal_branch_rate")
        d.focal_line_rate   = float(lr) if lr is not None else None
        d.focal_branch_rate = float(br) if br is not None else None

        flc = raw.get("focal_line_covered")
        flt = raw.get("focal_line_total")
        if flc is not None:
            try: d.focal_line_covered = int(flc)
            except Exception: pass
        if flt is not None:
            try: d.focal_line_total = int(flt)
            except Exception: pass

        d.diag_data_valid = True
        matched += 1

    logger.info("[Tool 1+2] matched %d/%d", matched, len(diags))
    return diags, tests_output_dir


def tool_compile_run(focal_method_result_dir, project_dir, test_names):
    return tool_compile_run_and_coverage(focal_method_result_dir, project_dir, test_names)


# ════════════════════════════════════════════════════════════════════
# Tool 3: Bug Revealing
# ════════════════════════════════════════════════════════════════════

def tool_bug_revealing(
    focal_method_result_dir: str,
    buggy_dir: str,
    fixed_dir: str,
    diags: Dict[str, TestDiag],
):
    compile_ok_tests = [n for n, d in diags.items() if d.compile_ok]
    if not compile_ok_tests:
        return

    script = os.path.join(HERE, "scripts", "bug_revealing.py")
    if not os.path.exists(script):
        logger.warning("[Tool 3] bug_revealing.py not found")
        return

    cmd = [sys.executable, script,
           "--buggy", buggy_dir,
           "--fixed", fixed_dir,
           "--tests", focal_method_result_dir]
    rc, _, err = _run(cmd, timeout=300)
    if rc != 0:
        logger.warning("[Tool 3] rc=%d: %s", rc, err[:300])
        return

    proj_basename = os.path.basename(buggy_dir)
    proj_prefix = proj_basename[:-2] if proj_basename.lower().endswith(("_b","_f")) else proj_basename

    _tgt_slug = "unknown"
    for meta_path, extractor in [
        (os.path.join(buggy_dir, "modified_classes.src"),
         lambda lines: lines[0].strip().split(".")[-1] if lines else ""),
        (os.path.join(buggy_dir, "defects4j.build.properties"),
         lambda lines: next(
             (l.split("=",1)[1].strip().split(",")[0].strip().split(".")[-1]
              for l in lines if "d4j.classes.modified" in l and "=" in l), "")),
    ]:
        if os.path.exists(meta_path):
            try:
                with open(meta_path) as f:
                    val = extractor(f.readlines())
                if val:
                    _tgt_slug = val
                    break
            except Exception:
                pass

    out_csv = os.path.join(focal_method_result_dir, f"{proj_prefix}_{_tgt_slug}_bugrevealing.csv")
    if not os.path.exists(out_csv):
        logger.warning("[Tool 3] csv not found: %s", out_csv)
        return

    try:
        with open(out_csv, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                tc = _short(row.get("test_class", "").strip())
                if tc in diags:
                    diags[tc].bug_revealing = (
                        str(row.get("bug_revealing","false")).lower() == "true")
    except Exception as e:
        logger.warning("[Tool 3] csv parse: %s", e)


# ════════════════════════════════════════════════════════════════════
# Tool 4: Similarity
# ════════════════════════════════════════════════════════════════════

def tool_similarity(
    focal_method_result_dir: str,
    diags: Dict[str, TestDiag],
) -> List[Tuple[str, str, float]]:
    scripts_dir = os.path.join(HERE, "scripts")
    tc_dir = os.path.join(focal_method_result_dir, "test_cases")
    if not os.path.isdir(tc_dir):
        return []

    for sname, timeout in [("code_to_ast.py", 120), ("measure_similarity.py", 300)]:
        sc = os.path.join(scripts_dir, sname)
        if not os.path.exists(sc):
            return []
        rc, _, stderr = _run([sys.executable, sc, tc_dir], timeout=timeout)
        if rc != 0:
            logger.warning("[Tool 4] %s rc=%d", sname, rc)

    sim_dir    = os.path.join(focal_method_result_dir, "Similarity")
    bsim_files = sorted(glob.glob(os.path.join(sim_dir, "*_bigSims.csv")))
    if not bsim_files:
        return []

    all_pairs: List[Tuple[str, str, float]] = []
    # best[tc] = (redundancy_score, partner) — highest redundancy_score = worst
    best: Dict[str, Tuple[float, str]] = {}

    try:
        with open(bsim_files[-1], newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                tc1 = _short(row.get("test_case_1", "").strip())
                tc2 = _short(row.get("test_case_2", "").strip())
                try:
                    # Issue 2 fix: 'redundancy_score' column = 1 - similarity
                    # Store it directly — do NOT invert again.
                    rs = float(row.get("redundancy_score", 0))
                except Exception:
                    rs = 0.0
                if tc1 in diags and tc2 in diags:
                    all_pairs.append((tc1, tc2, rs))
                    for tc, partner in [(tc1, tc2), (tc2, tc1)]:
                        if rs > best.get(tc, (0.0, ""))[0]:
                            best[tc] = (rs, partner)

        for tc, (score, partner) in best.items():
            if tc in diags:
                # redundancy_score = 1 - similarity: high → redundant
                diags[tc].redundancy_score = round(score, 4)
                diags[tc].most_similar_to  = partner

        logger.info("[Tool 4] %d pairs", len(all_pairs))
    except Exception as e:
        logger.warning("[Tool 4] parse: %s", e)

    return all_pairs


# ════════════════════════════════════════════════════════════════════
# Refiner prompt builder
# ════════════════════════════════════════════════════════════════════

def _build_refiner_messages(
    focal_method, class_name, focal_method_code,
    test_file_codes, diags, test_scores, suite_score,
    iteration, template_dir, cfg=None,
):
    from scoring_ablation import AblationConfig
    if cfg is None:
        cfg = AblationConfig()

    problematic_data = []
    for tname in diags:
        score = test_scores.get(tname, TestScore(tname))
        if not score.issues:
            continue
        entry = diags[tname].to_dict()
        entry["scores"]      = test_scores[tname].to_dict() if tname in test_scores else {}
        entry["source_code"] = test_file_codes.get(tname, "")

        if not cfg.use_compile_exec:
            entry["compile_ok"] = True; entry["exec_ok"] = True
            entry["compile_errors"] = []; entry["exec_errors"] = []
            entry["error_summary"] = ""
        else:
            entry["error_summary"] = get_error_summary(
                diags[tname].compile_errors, diags[tname].exec_errors)

        if not cfg.use_coverage:
            entry["focal_line_rate"] = None; entry["focal_branch_rate"] = None
            entry["focal_line_covered"] = None; entry["focal_line_total"] = None
            entry["missed_methods"] = []; entry["partial_methods"] = []

        if not cfg.use_bug_revealing:
            entry["bug_revealing"] = None

        if not cfg.use_redundancy:
            entry["redundancy_score"] = None; entry["most_similar_to"] = None

        # Issue 3: per-test top priority (not global suite priority)
        entry["top_priority_issues"] = issues_at_priority_level(score.issues)
        entry["all_issues"]          = score.issues
        problematic_data.append(entry)

    try:
        from jinja2 import Environment, FileSystemLoader
        tenv = Environment(loader=FileSystemLoader(template_dir))
        user = tenv.get_template("refine_agent.jinja2").render(
            focal_method=focal_method, class_name=class_name,
            focal_method_code=focal_method_code,
            suite_score=suite_score.to_dict(),
            test_diagnostics=problematic_data, iteration=iteration,
        )
    except Exception as e:
        logger.warning("Template render failed (%s), fallback", e)
        user = _fallback_prompt(focal_method, class_name, focal_method_code,
                                problematic_data, suite_score, iteration, template_dir)

    messages = []
    sys_path = os.path.join(template_dir, "refine_agent_system.jinja2")
    if os.path.exists(sys_path):
        with open(sys_path, encoding="utf-8") as sf:
            messages.append({"role": "system", "content": sf.read()})
    messages.append({"role": "user", "content": user})
    return messages


def _fallback_prompt(focal_method, class_name, focal_method_code,
                     problematic_data, suite_score, iteration, template_dir) -> str:
    suite_json = json.dumps(suite_score.to_dict(), indent=2, ensure_ascii=False)
    tests_json = json.dumps(problematic_data,      indent=2, ensure_ascii=False)
    tenv = Environment(loader=FileSystemLoader(template_dir))
    return tenv.get_template("fallback_refine_agent.jinja2").render(
        focal_method=focal_method, class_name=class_name,
        focal_method_code=focal_method_code,
        suite_json=suite_json, tests_json=tests_json, iteration=iteration,
    )


# ════════════════════════════════════════════════════════════════════
# RefineAgent
# ════════════════════════════════════════════════════════════════════

class RefineAgent:

    def __init__(
        self,
        refiner_client: LLMClient,
        template_dir: str,
        buggy_dir: Optional[str] = None,
        fixed_dir: Optional[str] = None,
        skip_bug_revealing: bool = False,
        skip_similarity: bool = False,
    ):
        self.client             = refiner_client
        self.template_dir       = template_dir
        self.buggy_dir          = buggy_dir
        self.fixed_dir          = fixed_dir
        self.skip_bug_revealing = skip_bug_revealing
        self.skip_similarity    = skip_similarity

    def run(
        self,
        focal_method_result_dir: str,
        project_dir: str,
        focal_method: str,
        class_name: str,
        target_class_fqn: str,
        focal_method_code: str,
        test_file_codes: Dict[str, str],
        iteration: int,
        save_dir: str,
        step_counter_start: int = 1,
    ) -> RefineResult:
        """
        完整 Agent 流程：
          1. Tool 1: 编译 + 执行（所有 Test 文件）
          2. Tool 2: 覆盖率（每个 Test 文件）
          3. Tool 3: Bug Revealing（每个 Test 文件，可选）
          4. Tool 4: Suite 内 Test 间相似度（pairwise）
          5. 计算 TestScore × N + SuiteScore
          6. Refiner LLM 生成 per-Test 指令

        Parameters
        ----------
        test_file_codes : {test_name: java_source}
            所有 Test 文件的名称和源码，用于传给 Refiner LLM 分析
        """
        test_names    = list(test_file_codes.keys())
        files_written = 0
        step          = step_counter_start

        # ── Tool 1+2 ──────────────────────────────────────────────
        t0 = time.time()
        diags, tests_output_dir = tool_compile_run_and_coverage(
            focal_method_result_dir, project_dir, test_names)
        logger.info("[RefineAgent] [Tool 1+2] %.1fs compile_ok=%d/%d exec_ok=%d/%d",
                    time.time()-t0,
                    sum(1 for d in diags.values() if d.compile_ok), len(diags),
                    sum(1 for d in diags.values() if d.exec_ok),    len(diags))

        # ── Tool 3 ────────────────────────────────────────────────
        if not self.skip_bug_revealing and self.buggy_dir and self.fixed_dir:
            t0 = time.time()
            tool_bug_revealing(focal_method_result_dir, self.buggy_dir, self.fixed_dir, diags)
            logger.info("[RefineAgent] [Tool 3] %.1fs", time.time()-t0)
        else:
            logger.info("[RefineAgent] [Tool 3] skipped")

        # ── Tool 4 ────────────────────────────────────────────────
        pairwise_sims = []
        if not self.skip_similarity and len(test_names) > 1:
            t0 = time.time()
            pairwise_sims = tool_similarity(focal_method_result_dir, diags)
            logger.info("[RefineAgent] [Tool 4] %.1fs %d pairs", time.time()-t0, len(pairwise_sims))

        # ── Scores ────────────────────────────────────────────────
        test_scores = {n: compute_test_score(d, _cfg) for n, d in diags.items()}
        suite_score = compute_suite_score(test_scores, pairwise_sims, _cfg)

        if self.skip_bug_revealing or not self.fixed_dir:
            suite_score._bug_reveal_skip_reason = (
                "fixed_dir not provided" if not self.fixed_dir else "skip_bug_revealing=True"
            )
        else:
            suite_score._bug_reveal_skip_reason = None

        logger.info(
            "[RefineAgent] SuiteScore: tests=%d compile=%d/%d exec=%d/%d "
            "line_cov_avg=%s bug_reveal=%d/%d",
            suite_score.n_tests,
            suite_score.compile_pass_count, suite_score.n_tests,
            suite_score.exec_pass_count,    suite_score.n_tests,
            f"{suite_score.coverage_line_avg:.2f}" if suite_score.coverage_line_avg is not None else "N/A",
            suite_score.bug_reveal_count,   suite_score.bug_reveal_checked,
        )
        if suite_score.problem_tests:
            logger.info("[RefineAgent] Problems: %s", suite_score.problem_tests)

        # ── Save diagnostics ──────────────────────────────────────
        diag_path = os.path.join(save_dir, f"{step}_tool_diag_{iteration}.json")
        with open(diag_path, "w", encoding="utf-8") as f:
            json.dump({
                "test_diags":    {k: v.to_dict() for k, v in diags.items()},
                "test_scores":   {k: v.to_dict() for k, v in test_scores.items()},
                "suite_score":   suite_score.to_dict(),
                "pairwise_sims": [{"tc1":t1,"tc2":t2,"score":round(s,4)}
                                   for t1,t2,s in pairwise_sims],
            }, f, indent=2, ensure_ascii=False)
        step += 1; files_written += 1

        # ── Check for problems ────────────────────────────────────
        problematic = [n for n, s in test_scores.items() if s.issues]
        if not problematic:
            logger.info("[RefineAgent] all Tests OK, skipping Refiner LLM")
            return RefineResult(
                focal_method=focal_method, class_name=class_name, iteration=iteration,
                test_diags=diags, test_scores=test_scores, suite_score=suite_score,
                suite_summary="All Tests pass all quality checks.", _files_written=files_written)

        logger.info("[RefineAgent] %d/%d problematic: %s", len(problematic), len(test_names), problematic)

        # ── Issue 3 fix: send ALL problematic tests to Refiner ────
        # Per-test priority is computed individually and embedded in each
        # test's diagnostic data so the Refiner LLM knows what to focus on.
        # We do NOT filter by suite-level top priority here.
        filtered_diags  = {n: diags[n]       for n in problematic}
        filtered_scores = {n: test_scores[n] for n in problematic}
        filtered_codes  = {n: test_file_codes.get(n, "") for n in problematic}

        messages = _build_refiner_messages(
            focal_method=focal_method, class_name=class_name,
            focal_method_code=focal_method_code,
            test_file_codes=filtered_codes,
            diags=filtered_diags, test_scores=filtered_scores,
            suite_score=suite_score,
            iteration=iteration, template_dir=self.template_dir, cfg=_cfg,
        )
        parsed, llm_result = self.client.chat_json(messages)

        ref_path = os.path.join(save_dir, f"{step}_REFINE_{iteration}.json")
        with open(ref_path, "w", encoding="utf-8") as f:
            json.dump({"raw": llm_result.content, "parsed": parsed,
                       "usage": llm_result.to_usage_dict()}, f, indent=2, ensure_ascii=False)
        files_written += 1

        # ── Collect instructions ──────────────────────────────────
        llm_instructions = {
            t: instr for t, instr in parsed.get("test_instructions", {}).items()
            if t in diags and isinstance(instr, list) and instr
        }
        instructions = dict(llm_instructions)

        # Fallback: rule-based for any problematic test without LLM instructions
        for tname in problematic:
            if tname not in instructions:
                hints = enrich_diag_with_fix_hints(diags[tname])
                if hints:
                    instructions[tname] = hints

        delete_tests = [t for t in parsed.get("delete_tests", []) if t in diags]

        return RefineResult(
            focal_method=focal_method, class_name=class_name, iteration=iteration,
            test_diags=diags, test_scores=test_scores, suite_score=suite_score,
            instructions=instructions, delete_tests=delete_tests,
            suite_summary=parsed.get("suite_summary", ""),
            refiner_prompt_tokens=llm_result.prompt_tokens,
            refiner_completion_tokens=llm_result.completion_tokens,
            refiner_elapsed_seconds=llm_result.elapsed_seconds,
            _files_written=files_written,
        )