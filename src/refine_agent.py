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

from llm_client import LLMClient, LLMCallResult
from scoring import TestScore, SuiteScore, compute_test_score, compute_suite_score

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
    missed_methods:    List[str] = field(default_factory=list)
    partial_methods:   List[str] = field(default_factory=list)

    bug_revealing: Optional[bool] = None

    redundancy_score: Optional[float] = None
    most_similar_to:  Optional[str]   = None

    # 标记诊断数据是否可信（路径问题时数据为默认值，不可信）
    diag_data_valid: bool = False

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class RefineResult:
    """
    Refine Agent 的完整输出，供 Generator 根据 per-Test 指令精修。
    """
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

    # 内部：agent.run() 写了几个文件（供 askGPT_refine 做 step 计数）
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
# 工具函数
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
    """org.pkg.Token_1_1Test → Token_1_1Test"""
    return full_name.rsplit(".", 1)[-1]


def _find_latest_tests_dir(project_dir: str) -> Optional[str]:
    """在 project_dir 下找最新的 tests%YYYYMMDDHHMMSS/ 目录。"""
    candidates = [
        os.path.join(project_dir, d)
        for d in os.listdir(project_dir)
        if d.startswith("tests%") and os.path.isdir(os.path.join(project_dir, d))
    ]
    return max(candidates, key=os.path.getmtime) if candidates else None


# ════════════════════════════════════════════════════════════════════
# Tool 1+2
# ════════════════════════════════════════════════════════════════════

def tool_compile_run_and_coverage(
    focal_method_result_dir: str,
    project_dir: str,
    test_names: List[str],
) -> Tuple[Dict[str, TestDiag], Optional[str]]:
    """
    调用 tool_runner_adapter，执行 TestRunner 并读取 suite_diagnosis.json。
    同时填充 Tool 1（compile/exec）和 Tool 2（coverage）的数据。
    返回 (diags, tests_output_dir)。
    """
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
        logger.warning("[Tool 1+2] suite_diagnosis.json empty — diag data invalid")
        # ★ 标记数据不可信
        for d in diags.values():
            d.diag_data_valid = False
        return diags, tests_output_dir

    # 填充 TestDiag 对象
    for tc_name, raw in diag_map.items():
        if tc_name not in diags:
            continue
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
        lr = raw.get("focal_line_rate")
        br = raw.get("focal_branch_rate")
        d.focal_line_rate   = float(lr) if lr is not None else None
        d.focal_branch_rate = float(br) if br is not None else None
        # ★ 有真实数据，标记为可信
        d.diag_data_valid = True

    valid_count = sum(1 for d in diags.values() if d.diag_data_valid)
    logger.info("[Tool 1+2] loaded %d/%d tests from suite_diagnosis.json",
                valid_count, len(diags))
    return diags, tests_output_dir


# ── 保留 tool_compile_run 作为向后兼容别名 ────────────────────────
def tool_compile_run(focal_method_result_dir, project_dir, test_names):
    return tool_compile_run_and_coverage(focal_method_result_dir, project_dir, test_names)


# ════════════════════════════════════════════════════════════════════
# Tool 2: 覆盖率（每个 Test 文件对 focal method 的覆盖率）
# ════════════════════════════════════════════════════════════════════

def tool_coverage(
    tests_output_dir: str,
    target_class_simple: str,
    focal_method: str,
    diags: Dict[str, TestDiag],
):
    """
    覆盖率数据已在 tool_compile_run_and_coverage() 中通过 suite_diagnosis.json 填充。
    此函数保留接口兼容性，实际上是空操作。
    如需额外的 JaCoCo XML 回退解析，可在此扩展。
    """
    pass


# ════════════════════════════════════════════════════════════════════
# Tool 3: Bug Revealing
# ════════════════════════════════════════════════════════════════════

def tool_bug_revealing(
    focal_method_result_dir: str,
    buggy_dir: str,
    fixed_dir: str,
    diags: Dict[str, TestDiag],
):
    """
    调用 scripts/bug_revealing.py，对 Suite 中每个 Test 文件判断是否 bug-revealing。
    结果写入 focal_method_result_dir/bugrevealing.csv。
    """
    script = os.path.join(HERE, "scripts", "bug_revealing.py")
    if not os.path.exists(script):
        logger.warning("[Tool 3] bug_revealing.py not found: %s", script)
        return

    out_csv = os.path.join(focal_method_result_dir, "bugrevealing.csv")
    cmd = [sys.executable, script,
           "--buggy", buggy_dir,
           "--fixed", fixed_dir,
           "--tests", focal_method_result_dir,   # 含 test_cases/ 子目录
           "--out",   out_csv]
    rc, _, err = _run(cmd, timeout=300)
    if rc != 0:
        logger.warning("[Tool 3] bug_revealing rc=%d: %s", rc, err[:300])

    if not os.path.exists(out_csv):
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
# Tool 4: 相似度
#
# Bug Fix (Issue 3):
#   传给 code_to_ast 和 measure_similarity 的路径改为
#   focal_method_result_dir/test_cases
#   → process_tests_dir() 走 'test_cases' 分支：
#     top_tests_dir = focal_method_result_dir  ✓
#     test_cases_dir = focal_method_result_dir/test_cases/  ✓
#     AST/ 和 Similarity/ 都写在 focal_method_result_dir 下  ✓
# ════════════════════════════════════════════════════════════════════

def tool_similarity(
    focal_method_result_dir: str,
    diags: Dict[str, TestDiag],
) -> List[Tuple[str, str, float]]:
    scripts_dir = os.path.join(HERE, "scripts")

    # ★ 修复：传 test_cases 子目录路径，让脚本走正确的分支
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

    # Similarity CSV 写在 focal_method_result_dir/Similarity/ 下
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
                diags[tc].redundancy_score = round(score, 4)
                diags[tc].most_similar_to  = partner

        logger.info("[Tool 4] %d pairs loaded from %s", len(all_pairs), bsim_files[-1])

    except Exception as e:
        logger.warning("[Tool 4] bigSims parse: %s", e)

    return all_pairs


# ════════════════════════════════════════════════════════════════════
# Refiner Prompt 构建
# ════════════════════════════════════════════════════════════════════

def _build_refiner_messages(
    focal_method: str,
    class_name: str,
    focal_method_code: str,
    test_file_codes: Dict[str, str],
    diags: Dict[str, TestDiag],
    test_scores: Dict[str, TestScore],
    suite_score: SuiteScore,
    iteration: int,
    template_dir: str,
) -> List[Dict]:
    """
    构建 Refiner LLM 的 messages。
    - 传入每个有问题的 Test 文件的源码（供 Refiner 分析具体代码）
    - 传入 SuiteScore（整体视图）
    - 传入每个 Test 的 TestScore + TestDiag（per-Test 详细诊断）
    """
    # 合并 diag + score，只保留有问题的 Test
    problematic_data = []
    for tname in diags:
        score = test_scores.get(tname, TestScore(tname))
        if not score.issues:
            continue
        entry = diags[tname].to_dict()
        entry["scores"] = score.to_dict()
        entry["source_code"] = test_file_codes.get(tname, "// [source not available]")

        # ★ 修复：如果诊断数据不可信，注明警告，防止 Refiner 给出基于错误诊断的指令
        if not diags[tname].diag_data_valid:
            entry["_WARNING"] = (
                "诊断数据缺失（工具链路径问题），compile_errors/exec_errors 均为空。"
                "请勿基于 COMPILE_FAIL 标签给出具体编译错误修复指令。"
                "仅根据 source_code 判断代码质量并给出改进建议。"
            )

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
        user = _fallback_prompt(
            focal_method, class_name, focal_method_code,
            problematic_data, suite_score, iteration
        )

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
    try:
        from jinja2 import Environment, FileSystemLoader
        tenv = Environment(loader=FileSystemLoader(template_dir))
        return tenv.get_template("fallback_refine_agent.jinja2").render(
            focal_method=focal_method,
            class_name=class_name,
            focal_method_code=focal_method_code,
            suite_json=suite_json,
            tests_json=tests_json,
            iteration=iteration,
        )
    except Exception as e:
        logger.warning("Fallback template render failed (%s), using hardcoded", e)
        return f"""You are a Java test quality analyst (Refine Agent).

## Context
Focal method: `{focal_method}` in `{class_name}` | Iteration {iteration}

## Focal Method Source
```java
{focal_method_code}
```

## Suite-Level Scores
```json
{suite_json}
```

## Problematic Test Files
```json
{tests_json}
```

## Your Task
Output ONLY a JSON object:
{{
  "suite_summary": "<2-4 sentences>",
  "test_instructions": {{
    "<test_name>": ["<instruction1>", "<instruction2>"]
  }},
  "delete_tests": ["<test_name>"]
}}

Rules:
- If _WARNING is present for a test, do NOT give compile-error fix instructions;
  instead focus on coverage improvement and assertion quality.
- test_name keys must match exactly
- Only include tests with issues
- delete_tests: only similarity > 0.95
- Max 4 instructions per test, must be concrete
"""


# ════════════════════════════════════════════════════════════════════
# Refine Agent
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

        # ── Tool 1+2: 编译 + 执行 + 覆盖率（通过 tool_runner_adapter）──
        # suite_diagnosis.json 统一输出，包含 compile/exec/coverage 全部数据
        t0 = time.time()
        diags, tests_output_dir = tool_compile_run_and_coverage(
            focal_method_result_dir, project_dir, test_names
        )
        valid_count = sum(1 for d in diags.values() if d.diag_data_valid)
        logger.info(
            "[RefineAgent] [Tool 1+2] %.1fs  valid_diags=%d/%d  "
            "compile_ok=%d/%d  exec_ok=%d/%d",
            time.time() - t0, valid_count, len(diags),
            sum(1 for d in diags.values() if d.compile_ok), len(diags),
            sum(1 for d in diags.values() if d.exec_ok),    len(diags),
        )

        # ★ 打印诊断数据有效性警告
        if valid_count == 0:
            logger.warning(
                "[RefineAgent] ⚠️  ALL diag data invalid (suite_diagnosis.json empty). "
                "Refiner will work with source code only, without real compile/exec status. "
                "Check tool_runner_adapter logs for TestRunner path issues."
            )

        # Tool 3
        if not self.skip_bug_revealing and self.buggy_dir and self.fixed_dir:
            t0 = time.time()
            tool_bug_revealing(
                focal_method_result_dir, self.buggy_dir, self.fixed_dir, diags
            )
            logger.info("[RefineAgent] [Tool 3] %.1fs", time.time() - t0)

        # Tool 4 (★ 路径修复已在 tool_similarity 内部实现)
        pairwise_sims: List[Tuple[str, str, float]] = []
        if not self.skip_similarity and len(test_names) > 1:
            t0 = time.time()
            pairwise_sims = tool_similarity(focal_method_result_dir, diags)
            logger.info("[RefineAgent] [Tool 4] %.1fs  %d pairs",
                        time.time() - t0, len(pairwise_sims))

        # ── ★ 脚本计算 Test 级得分（每个 Test 文件）────────────
        test_scores: Dict[str, TestScore] = {
            name: compute_test_score(diag) for name, diag in diags.items()
        }

        # ── ★ 脚本计算 Suite 级统计（N 个 Test 文件整体）────────
        suite_score: SuiteScore = compute_suite_score(test_scores, pairwise_sims)

        logger.info(
            "[RefineAgent] SuiteScore: tests=%d compile=%d/%d exec=%d/%d "
            "line_cov_avg=%s bug_reveal=%d/%d max_pair_sim=%s",
            suite_score.n_tests,
            suite_score.compile_pass_count, suite_score.n_tests,
            suite_score.exec_pass_count,    suite_score.n_tests,
            f"{suite_score.coverage_line_avg:.2f}" if suite_score.coverage_line_avg is not None else "N/A",
            suite_score.bug_reveal_count,   suite_score.bug_reveal_checked,
            f"{suite_score.max_pairwise_similarity:.3f}" if suite_score.max_pairwise_similarity is not None else "N/A",
        )
        if suite_score.problem_tests:
            logger.info("[RefineAgent] Problems: %s", suite_score.problem_tests)

        # 保存诊断
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
                "diag_data_valid_count": valid_count,
            }, f, indent=2, ensure_ascii=False)
        step += 1; files_written += 1

        # 检查是否有问题
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

        # Refiner LLM
        filtered_diags  = {n: diags[n]       for n in problematic}
        filtered_scores = {n: test_scores[n] for n in problematic}
        filtered_codes  = {n: test_file_codes.get(n, "") for n in problematic}

        messages = _build_refiner_messages(
            focal_method=focal_method, class_name=class_name,
            focal_method_code=focal_method_code,
            test_file_codes=filtered_codes,
            diags=filtered_diags, test_scores=filtered_scores,
            suite_score=suite_score,
            iteration=iteration, template_dir=self.template_dir,
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

        instructions = {
            t: instr for t, instr in parsed.get("test_instructions", {}).items()
            if t in diags and isinstance(instr, list) and instr
        }
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