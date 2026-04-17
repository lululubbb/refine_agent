"""
refine_agent.py  (v4 — focal-method coverage feedback + priority-based issue filtering)

Key changes:
  - TestDiag gains focal_line_covered / focal_line_total fields (Issue 3)
  - tool_compile_run_and_coverage populates these from suite_diagnosis.json (Issue 3)
  - Issues are filtered to highest-priority group before calling Refiner LLM (Issue 5)
  - Priority order: COMPILE > EXEC > BUG_REVEALING > COVERAGE > REDUNDANCY (Issue 5)
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

    # NEW (Issue 3): focal method line counts for richer coverage feedback
    focal_line_covered: Optional[int] = None
    focal_line_total:   Optional[int] = None

    # Class-level missed/partial methods (kept for backward compat but
    # NOT shown in fix prompt when focal coverage is the issue — see Issue 3)
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
# Utility
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
        logger.warning("[Tool 1+2] TestRunner failed, all diags remain default")
        return diags, None

    # 读取统一 JSON（一次调用，包含 compile/exec/coverage 全部数据）
    diag_map = load_suite_diagnosis(tests_output_dir)
    if not diag_map:
        logger.warning("[Tool 1+2] suite_diagnosis.json empty")
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

        # ── Issue 3: populate focal line counts ──────────────────
        flc = raw.get("focal_line_covered")
        flt = raw.get("focal_line_total")
        if flc is not None:
            try:
                d.focal_line_covered = int(flc)
            except (TypeError, ValueError):
                pass
        if flt is not None:
            try:
                d.focal_line_total = int(flt)
            except (TypeError, ValueError):
                pass

        # If not stored directly, derive from rate + total where possible
        if d.focal_line_covered is None and d.focal_line_rate is not None and d.focal_line_total:
            d.focal_line_covered = round(d.focal_line_rate / 100.0 * d.focal_line_total)

        d.diag_data_valid = True
        matched += 1

    logger.info("[Tool 1+2] matched %d/%d tests from suite_diagnosis.json", matched, len(diags))
    if matched == 0:
        logger.warning("[Tool 1+2] diag_map has %d entries but none matched test_names=%s",
                       len(diag_map), list(test_names)[:3])

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
    compile_ok_tests = [name for name, d in diags.items() if d.compile_ok]
    if not compile_ok_tests:
        logger.info("[Tool 3] skip: no compile_ok tests")
        return

    script = os.path.join(HERE, "scripts", "bug_revealing.py")
    if not os.path.exists(script):
        logger.warning("[Tool 3] bug_revealing.py not found: %s", script)
        return

    cmd = [sys.executable, script,
           "--buggy", buggy_dir,
           "--fixed", fixed_dir,
           "--tests", focal_method_result_dir]
    rc, _, err = _run(cmd, timeout=300)
    if rc != 0:
        logger.warning("[Tool 3] bug_revealing rc=%d: %s", rc, err[:300])
        return

    proj_basename = os.path.basename(buggy_dir)
    if proj_basename.lower().endswith('_b') or proj_basename.lower().endswith('_f'):
        proj_prefix = proj_basename[:-2]
    else:
        proj_prefix = proj_basename

    _tgt_slug = "unknown"
    meta_file = os.path.join(buggy_dir, 'modified_classes.src')
    if os.path.exists(meta_file):
        try:
            with open(meta_file) as f:
                line = f.readline().strip()
            if line:
                _tgt_slug = line.split('.')[-1]
        except Exception:
            pass
    else:
        prop_file = os.path.join(buggy_dir, 'defects4j.build.properties')
        if os.path.exists(prop_file):
            try:
                with open(prop_file) as f:
                    for l in f:
                        if 'd4j.classes.modified' in l and '=' in l:
                            val = l.split('=', 1)[1].strip()
                            first_class = val.split(',')[0].strip()
                            if first_class:
                                _tgt_slug = first_class.split('.')[-1]
                            break
            except Exception:
                pass

    expected_filename = f"{proj_prefix}_{_tgt_slug}_bugrevealing.csv"
    out_csv = os.path.join(focal_method_result_dir, expected_filename)

    if not os.path.exists(out_csv):
        logger.warning("[Tool 3] Expected output file not found: %s", out_csv)
        return

    try:
        with open(out_csv, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                tc = _short(row.get("test_class", row.get("full_class_name", "")).strip())
                if tc in diags:
                    diags[tc].bug_revealing = (
                        str(row.get("bug_revealing", "false")).lower() == "true"
                    )
    except Exception as e:
        logger.warning("[Tool 3] CSV parse: %s", e)


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
        logger.warning("[Tool 4] test_cases dir not found: %s", tc_dir)
        return []

    for sname, timeout in [("code_to_ast.py", 120), ("measure_similarity.py", 300)]:
        sc = os.path.join(scripts_dir, sname)
        if not os.path.exists(sc):
            logger.warning("[Tool 4] %s not found", sname)
            return []
        rc, stdout, stderr = _run([sys.executable, sc, tc_dir], timeout=timeout)
        if rc != 0:
            logger.warning("[Tool 4] %s rc=%d stderr=%s", sname, rc, stderr[:300])
        else:
            logger.info("[Tool 4] %s OK", sname)

    sim_dir    = os.path.join(focal_method_result_dir, "Similarity")
    bsim_files = sorted(glob.glob(os.path.join(sim_dir, "*_bigSims.csv")))
    if not bsim_files:
        logger.warning("[Tool 4] No bigSims.csv found in %s", sim_dir)
        return []

    all_pairs: List[Tuple[str, str, float]] = []
    best: Dict[str, Tuple[float, str]] = {}

    try:
        with open(bsim_files[-1], newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                tc1 = _short(row.get("test_case_1", "").strip())
                tc2 = _short(row.get("test_case_2", "").strip())
                try:
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
                diags[tc].redundancy_score = 1 - round(score, 4)
                diags[tc].most_similar_to  = partner

        logger.info("[Tool 4] %d pairs loaded", len(all_pairs))
    except Exception as e:
        logger.warning("[Tool 4] bigSims parse: %s", e)

    return all_pairs


# ════════════════════════════════════════════════════════════════════
# Refiner Prompt
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
        entry["source_code"] = test_file_codes.get(tname, "// [source not available]")

        if not cfg.use_compile_exec:
            entry["compile_ok"] = True
            entry["exec_ok"] = True
            entry["compile_errors"] = []
            entry["exec_errors"] = []
            entry["auto_fix_hints"] = []
            entry["error_summary"] = ""
        else:
            entry["error_summary"] = get_error_summary(
                diags[tname].compile_errors, diags[tname].exec_errors
            )

        if not cfg.use_coverage:
            entry["focal_line_rate"] = None
            entry["focal_branch_rate"] = None
            entry["focal_line_covered"] = None
            entry["focal_line_total"] = None
            entry["missed_methods"] = []
            entry["partial_methods"] = []

        if not cfg.use_bug_revealing:
            entry["bug_revealing"] = None

        if not cfg.use_redundancy:
            entry["redundancy_score"] = None
            entry["most_similar_to"] = None

        # ── Issue 5: show only top-priority issues to Refiner ────
        top_issues = issues_at_priority_level(score.issues)
        entry["top_priority_issues"] = top_issues
        entry["all_issues"]          = score.issues

        problematic_data.append(entry)

    try:
        from jinja2 import Environment, FileSystemLoader
        tenv = Environment(loader=FileSystemLoader(template_dir))
        user = tenv.get_template("refine_agent.jinja2").render(
            focal_method      = focal_method,
            class_name        = class_name,
            focal_method_code = focal_method_code,
            suite_score       = suite_score.to_dict(),
            test_diagnostics  = problematic_data,
            iteration         = iteration,
        )
    except Exception as e:
        logger.warning("Template render failed (%s), using fallback", e)
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
        focal_method=focal_method,
        class_name=class_name,
        focal_method_code=focal_method_code,
        suite_json=suite_json,
        tests_json=tests_json,
        iteration=iteration,
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

        logger.info("[RefineAgent] iter=%d  Suite=%d Tests: %s",
                    iteration, len(test_names), test_names)

        # ── Tool 1+2 ──────────────────────────────────────────────
        t0 = time.time()
        diags, tests_output_dir = tool_compile_run_and_coverage(
            focal_method_result_dir, project_dir, test_names
        )
        logger.info(
            "[RefineAgent] [Tool 1+2] %.1fs  tests_dir=%s  "
            "compile_ok=%d/%d  exec_ok=%d/%d",
            time.time() - t0, tests_output_dir,
            sum(1 for d in diags.values() if d.compile_ok), len(diags),
            sum(1 for d in diags.values() if d.exec_ok),    len(diags),
        )

        # ── Tool 3: Bug Revealing ─────────────────────────────────
        if not self.skip_bug_revealing and self.buggy_dir and self.fixed_dir:
            t0 = time.time()
            tool_bug_revealing(
                focal_method_result_dir, self.buggy_dir, self.fixed_dir, diags
            )
            logger.info("[RefineAgent] [Tool 3] %.1fs", time.time() - t0)
        else:
            reason = "fixed_dir not provided" if not self.fixed_dir else "skip_bug_revealing=True"
            logger.info("[RefineAgent] [Tool 3] skipped: %s", reason)

        # ── Tool 4: Similarity ────────────────────────────────────
        pairwise_sims: List[Tuple[str, str, float]] = []
        if not self.skip_similarity and len(test_names) > 1:
            t0 = time.time()
            pairwise_sims = tool_similarity(focal_method_result_dir, diags)
            logger.info("[RefineAgent] [Tool 4] %.1fs  %d pairs",
                        time.time() - t0, len(pairwise_sims))

        # ── Compute scores ────────────────────────────────────────
        test_scores = {name: compute_test_score(diag, _cfg) for name, diag in diags.items()}
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
                "pairwise_sims": [
                    {"tc1": t1, "tc2": t2, "score": round(s, 4)}
                    for t1, t2, s in pairwise_sims
                ],
            }, f, indent=2, ensure_ascii=False)
        step += 1; files_written += 1

        # ── Check for problems ────────────────────────────────────
        problematic = [n for n, s in test_scores.items() if s.issues]
        if not problematic:
            logger.info("[RefineAgent] all Tests OK, skipping Refiner LLM")
            return RefineResult(
                focal_method=focal_method, class_name=class_name, iteration=iteration,
                test_diags=diags, test_scores=test_scores, suite_score=suite_score,
                suite_summary="All Tests in this Suite pass all quality checks.",
                _files_written=files_written,
            )

        logger.info("[RefineAgent] %d/%d Tests have issues: %s",
                    len(problematic), len(test_names), problematic)

        # ── Issue 5: filter to highest-priority problematic tests ─
        # Find the global top priority across all problematic tests
        all_issues_flat = []
        for n in problematic:
            all_issues_flat.extend(test_scores[n].issues)

        top_priority_issues = issues_at_priority_level(all_issues_flat)

        # Only send tests that have issues at the top priority level
        top_priority_problematic = [
            n for n in problematic
            if any(i in top_priority_issues for i in test_scores[n].issues)
        ]

        logger.info("[RefineAgent] Top priority issues: %s, affected tests: %s",
                    top_priority_issues, top_priority_problematic)

        # ── Refiner LLM ───────────────────────────────────────────
        filtered_diags  = {n: diags[n]       for n in top_priority_problematic}
        filtered_scores = {n: test_scores[n] for n in top_priority_problematic}
        filtered_codes  = {n: test_file_codes.get(n, "") for n in top_priority_problematic}

        messages = _build_refiner_messages(
            focal_method=focal_method, class_name=class_name,
            focal_method_code=focal_method_code,
            test_file_codes=filtered_codes,
            diags=filtered_diags, test_scores=filtered_scores,
            suite_score=suite_score,
            iteration=iteration, template_dir=self.template_dir,
            cfg=_cfg,
        )
        parsed, llm_result = self.client.chat_json(messages)

        ref_path = os.path.join(save_dir, f"{step}_REFINE_{iteration}.json")
        with open(ref_path, "w", encoding="utf-8") as f:
            json.dump({
                "raw":    llm_result.content,
                "parsed": parsed,
                "usage":  llm_result.to_usage_dict(),
            }, f, indent=2, ensure_ascii=False)
        files_written += 1

        # ── Collect instructions ──────────────────────────────────
        llm_instructions = {
            t: instr for t, instr in parsed.get("test_instructions", {}).items()
            if t in diags and isinstance(instr, list) and instr
        }

        instructions = dict(llm_instructions)
        fallback_used_for = []

        for tname in top_priority_problematic:
            if tname not in instructions:
                fallback_hints = enrich_diag_with_fix_hints(diags[tname])
                if fallback_hints:
                    instructions[tname] = fallback_hints
                    fallback_used_for.append(tname)

        if fallback_used_for:
            logger.info("[RefineAgent] Rule-based fallback for %d tests: %s",
                        len(fallback_used_for), fallback_used_for)

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