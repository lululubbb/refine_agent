"""
askGPT_refine.py  (v7 — simplified, ChatUniTest-style fix logic)

Key changes vs v6:
  1. Removed assert_fixer integration entirely
  2. Removed scoring_improvements / branch_hint_extractor integration
  3. Removed StableTestGuard (stable test protection)
  4. Simplified fix loop: suite-level priority logic
     - Phase 2 round logic:
       * If NOT all tests compile → fix only compile-failing tests (compile errors)
       * If all tests compile but some have exec errors → fix exec-failing tests
       * If all compile AND all exec pass → fix remaining issues (coverage, bug-revealing, redundancy)
       per-test: fix based on that test's highest-priority issue
  5. Removed contract_integration, project_version_extractor usage
  6. Removed _enforce_test_method_limit (over-engineering)
  7. Kept _run_syntax_validation as a lightweight pre-check
"""
from __future__ import annotations

import concurrent.futures
import copy
import json
import logging
import os
import re
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional

from colorama import Fore, Style, init

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from config import (
    TEMPLATE_NO_DEPS, TEMPLATE_WITH_DEPS, TEMPLATE_FIX,
    MAX_PROMPT_TOKENS, MIN_ERROR_TOKENS,
    max_rounds, test_number, process_number,
    dataset_dir, result_dir, project_dir,
)
from llm_client import LLMClient, LLMCallResult, make_generator_client, make_refiner_client
from llm_stats_tracker import LLMStatsTracker
from refine_agent import RefineAgent, RefineResult
from tools import (
    get_dataset_path, parse_file_name, get_messages_tokens,
    repair_imports, repair_package, change_class_name, extract_code,
    canonical_package_decl,
)
from jinja2 import Environment, FileSystemLoader
from compile_error_analyzer import enrich_diag_with_fix_hints, get_error_summary
from scoring import sort_issues_by_priority, issues_at_priority_level
from scoring_ablation import (
    compute_test_score_ablation as compute_test_score,
    compute_suite_score_ablation as compute_suite_score,
    global_ablation_config,
)

init()
logger = logging.getLogger(__name__)

_PROMPT_DIR = os.path.join(os.path.dirname(HERE), "prompt")
env = Environment(loader=FileSystemLoader(_PROMPT_DIR))


# ════════════════════════════════════════════════════════════════════
# Progress printing helpers
# ════════════════════════════════════════════════════════════════════

def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _divider(char="─", width=72, color=Fore.WHITE):
    print(color + char * width + Style.RESET_ALL, flush=True)


def _section(title: str, color=Fore.CYAN):
    w = 72
    inner = f"  {title}  "
    pad_l = max(0, (w - 2 - len(inner)) // 2)
    pad_r = max(0, w - 2 - len(inner) - pad_l)
    print(color + "┌" + "─" * (w - 2) + "┐" + Style.RESET_ALL, flush=True)
    print(color + "│" + " " * pad_l + inner + " " * pad_r + "│" + Style.RESET_ALL, flush=True)
    print(color + "└" + "─" * (w - 2) + "┘" + Style.RESET_ALL, flush=True)


def _code_changed(old: str, new: str) -> bool:
    def normalize(s):
        s = re.sub(r'//[^\n]*', '', s)
        s = re.sub(r'/\*.*?\*/', '', s, flags=re.DOTALL)
        return re.sub(r'\s+', ' ', s).strip()
    return normalize(old) != normalize(new)


def _count_test_methods(java_source: str) -> int:
    return len(re.findall(r'@Test\b', java_source))


def _print_suite_score(suite_score, tag=""):
    ss = suite_score
    print(flush=True)
    _divider("·", color=Fore.YELLOW)
    print(Fore.YELLOW + f"  📊 Suite Score{' ' + tag if tag else ''}" + Style.RESET_ALL, flush=True)
    _divider("·", color=Fore.YELLOW)

    if ss.compile_pass_rate is not None:
        cr = ss.compile_pass_rate
        cr_c = Fore.GREEN if cr >= 0.8 else (Fore.YELLOW if cr >= 0.5 else Fore.RED)
        all_tag = " ✅ALL" if ss.all_compile_pass else ""
        print(f"  {'编译通过率':<16}: {cr_c}{ss.compile_pass_count}/{ss.n_tests} ({cr*100:.0f}%){all_tag}{Style.RESET_ALL}", flush=True)

    if ss.exec_pass_rate is not None:
        er = ss.exec_pass_rate
        er_c = Fore.GREEN if er >= 0.8 else (Fore.YELLOW if er >= 0.5 else Fore.RED)
        print(f"  {'执行通过率':<16}: {er_c}{ss.exec_pass_count}/{ss.n_tests} ({er*100:.0f}%){Style.RESET_ALL}", flush=True)

    if ss.coverage_line_avg is not None:
        lc = ss.coverage_line_avg
        lc_c = Fore.GREEN if lc >= 0.8 else (Fore.YELLOW if lc >= 0.7 else Fore.RED)
        print(f"  {'行覆盖率(avg)':<16}: {lc_c}{lc*100:.1f}%  "
              f"(min={ss.coverage_line_min*100:.1f}%  max={ss.coverage_line_max*100:.1f}%){Style.RESET_ALL}", flush=True)

    if ss.coverage_branch_avg is not None:
        bc = ss.coverage_branch_avg
        bc_c = Fore.GREEN if bc >= 0.8 else (Fore.YELLOW if bc >= 0.7 else Fore.RED)
        print(f"  {'分支覆盖率(avg)':<16}: {bc_c}{bc*100:.1f}%{Style.RESET_ALL}", flush=True)

    if ss.bug_reveal_checked > 0:
        br = ss.bug_reveal_rate
        br_c = Fore.GREEN if br >= 0.5 else (Fore.YELLOW if br > 0 else Fore.RED)
        print(f"  {'Bug揭示率':<16}: {br_c}{ss.bug_reveal_count}/{ss.bug_reveal_checked} ({br*100:.0f}%){Style.RESET_ALL}", flush=True)

    if ss.max_pairwise_similarity is not None:
        sim = ss.max_pairwise_similarity
        sim_c = Fore.RED if 1-sim > 0.9 else (Fore.YELLOW if 1-sim > 0.7 else Fore.GREEN)
        print(f"  {'最大用例相似度':<16}: {sim_c}{1-sim:.3f}{Style.RESET_ALL}", flush=True)

    if ss.problem_tests and ss.n_tests > 0:
        print(f"\n  ⚠️  问题分布（按优先级）：", flush=True)
        issue_order = ["COMPILE_FAIL", "EXEC_FAIL", "EXEC_TIMEOUT",
                       "NOT_BUG_REVEALING", "LOW_COVERAGE",
                       "LOW_LINE_COV", "LOW_BRANCH_COV", "HIGH_REDUNDANCY"]
        issue_colors = {
            "COMPILE_FAIL":      Fore.RED,
            "EXEC_FAIL":         Fore.RED,
            "EXEC_TIMEOUT":      Fore.RED,
            "NOT_BUG_REVEALING": Fore.MAGENTA,
            "LOW_COVERAGE":      Fore.YELLOW,
            "LOW_LINE_COV":      Fore.YELLOW,
            "LOW_BRANCH_COV":    Fore.YELLOW,
            "HIGH_REDUNDANCY":   Fore.CYAN,
        }
        for iss in issue_order:
            if iss in ss.problem_tests:
                c = issue_colors.get(iss, Fore.WHITE)
                print(f"    {c}[{iss}]{Style.RESET_ALL} → {', '.join(ss.problem_tests[iss])}", flush=True)
    elif ss.n_tests > 0:
        print(f"\n  ✅ 无问题！Suite 全部通过质量检查。", flush=True)

    _divider("·", color=Fore.YELLOW)
    print(flush=True)


def _print_test_diag(tc_name: str, diag, score):
    issues = score.issues if score else []
    if not issues:
        return

    issue_colors = {
        "COMPILE_FAIL":      Fore.RED,
        "EXEC_FAIL":         Fore.RED,
        "EXEC_TIMEOUT":      Fore.RED,
        "NOT_BUG_REVEALING": Fore.MAGENTA,
        "LOW_COVERAGE":      Fore.YELLOW,
        "LOW_LINE_COV":      Fore.YELLOW,
        "LOW_BRANCH_COV":    Fore.YELLOW,
        "HIGH_REDUNDANCY":   Fore.CYAN,
    }

    print(f"\n  🔍 {Fore.WHITE}{tc_name}{Style.RESET_ALL}  问题: "
          + "  ".join([f"{issue_colors.get(i, Fore.WHITE)}[{i}]{Style.RESET_ALL}" for i in issues]),
          flush=True)

    if "COMPILE_FAIL" in issues and diag.compile_errors:
        print(f"    {Fore.RED}编译错误 (前5条):{Style.RESET_ALL}", flush=True)
        for e in diag.compile_errors[:5]:
            print(f"      • {e}", flush=True)

    if ("EXEC_FAIL" in issues or "EXEC_TIMEOUT" in issues) and diag.exec_errors:
        print(f"    {Fore.RED}运行错误 (前5条):{Style.RESET_ALL}", flush=True)
        for e in diag.exec_errors[:5]:
            print(f"      • {e}", flush=True)

    if score.focal_line_covered is not None and score.focal_line_total is not None and score.focal_line_total > 0:
        lc_pct = score.focal_line_covered / score.focal_line_total * 100
        lc_color = Fore.GREEN if lc_pct >= 80 else (Fore.YELLOW if lc_pct >= 50 else Fore.RED)
        print(f"    focal method行覆盖: {lc_color}{score.focal_line_covered}/{score.focal_line_total} ({lc_pct:.1f}%){Style.RESET_ALL}", flush=True)
    elif score.focal_line_coverage is not None:
        lc = score.focal_line_coverage
        lc_color = Fore.GREEN if lc >= 0.8 else (Fore.YELLOW if lc >= 0.5 else Fore.RED)
        print(f"    行覆盖率: {lc_color}{lc*100:.1f}%{Style.RESET_ALL}", flush=True)
    if score.focal_branch_coverage is not None:
        bc = score.focal_branch_coverage
        bc_color = Fore.GREEN if bc >= 0.8 else (Fore.YELLOW if bc >= 0.5 else Fore.RED)
        print(f"    分支覆盖率: {bc_color}{bc*100:.1f}%{Style.RESET_ALL}", flush=True)

    # 未覆盖方法
    if diag.missed_methods:
        print(f"    {Fore.YELLOW}未覆盖方法 (前5个):{Style.RESET_ALL}", flush=True)
        for m in diag.missed_methods[:5]:
            print(f"      • {m}", flush=True)

    # Bug revealing
    if "NOT_BUG_REVEALING" in issues:
        print(f"    {Fore.MAGENTA}未揭示 Bug：建议强化断言（使用精确 assertEquals）{Style.RESET_ALL}", flush=True)

    # 高冗余
    if "HIGH_REDUNDANCY" in issues and score.most_similar_to:
        rs = score.max_similarity or 0
        print(f"    {Fore.CYAN}冗余度 {rs:.3f}，与 {score.most_similar_to} 高度相似{Style.RESET_ALL}", flush=True)


def _print_refine_instructions(instructions: Dict[str, List[str]], delete_tests: List[str]):
    if not instructions and not delete_tests:
        print(f"\n  ℹ️  {Fore.GREEN}Refiner 无修复指令（Suite 质量良好）{Style.RESET_ALL}", flush=True)
        return

    print(f"\n  📝 Refiner 修复指令预览：", flush=True)
    for tc, instr_list in instructions.items():
        print(f"\n    {Fore.WHITE}▶ {tc}{Style.RESET_ALL}", flush=True)
        for idx, instr in enumerate(instr_list, 1):
            # 截断超长指令
            preview = instr[:200] + ("..." if len(instr) > 200 else "")
            print(f"      {idx}. {preview}", flush=True)

    if delete_tests:
        print(f"\n    {Fore.CYAN}🗑  建议删除（高冗余）: {', '.join(delete_tests)}{Style.RESET_ALL}", flush=True)


def _log_refine_quality(save_dir: str, focal_method: str, round_num: int,
                        suite_score, test_scores: dict, instructions: dict,
                        suite_summary: str, fix_results: dict = None):
    log_path = os.path.normpath(os.path.join(save_dir, "..", "refine_quality.jsonl"))
    entry = {
        "ts": _ts(), "focal_method": focal_method, "round": round_num,
        "suite_summary": suite_summary,
        "suite_score": suite_score.to_dict() if suite_score else {},
        "test_issues": {name: s.issues for name, s in test_scores.items()},
        "instructions_count": len(instructions),
        "tests_with_instructions": list(instructions.keys()),
        "fix_results": fix_results or {},
    }
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.debug("refine_quality.jsonl write error: %s", e)


# ════════════════════════════════════════════════════════════════════
# Prompt helpers
# ════════════════════════════════════════════════════════════════════

def generate_prompt(template_name: str, context: dict) -> str:
    return env.get_template(template_name).render(context)


def generate_messages(template_name: str, context: dict) -> List[Dict]:
    messages = []
    sys_name = f"{template_name.split('.')[0]}_system.jinja2"
    if os.path.exists(os.path.join(_PROMPT_DIR, sys_name)):
        messages.append({"role": "system", "content": generate_prompt(sys_name, {})})
    messages.append({"role": "user", "content": generate_prompt(template_name, context)})
    return messages


def remain_prompt_tokens(messages):
    return MAX_PROMPT_TOKENS - get_messages_tokens(messages)


# ════════════════════════════════════════════════════════════════════
# Generator LLM call
# ════════════════════════════════════════════════════════════════════

def call_generator(gen_client: LLMClient, messages: List[Dict],
                   save_path: str) -> tuple:
    try:
        result = gen_client.chat(messages)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump({
                "choices": [{"message": {"role": "assistant", "content": result.content}}],
                "usage":   result.to_usage_dict(),
            }, f, indent=2, ensure_ascii=False)
        return (not result.content.startswith("[LLM_ERROR]")), result
    except Exception as e:
        error_msg = f"[LLM_ERROR] Exception: {type(e).__name__}: {str(e)}"
        error_result = LLMCallResult(content=error_msg, prompt_tokens=0,
                                     completion_tokens=0, elapsed_seconds=0.0)
        try:
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump({"error": str(e), "choices": [{"message": {"role": "assistant", "content": error_msg}}]},
                          f, indent=2, ensure_ascii=False)
        except Exception:
            pass
        return False, error_result


def _strip_pkg(s: str, imports: str, package: str) -> str:
    return s.replace(imports, "").replace(package, "").strip()


# ════════════════════════════════════════════════════════════════════
# Syntax validation (lightweight, no assert_fixer)
# ════════════════════════════════════════════════════════════════════

def _run_syntax_validation(
    java_code: str,
    tc_name: str,
    focal_class_context: str = "",
) -> tuple:
    try:
        from java_syntax_validator import validate_java
        result = validate_java(java_code, focal_class_context=focal_class_context)
        if result.is_valid:
            return False, ""
        prompt_text = result.to_prompt_text(max_issues=4)
        return result.error_count > 0, prompt_text
    except Exception as e:
        logger.debug("syntax validation failed for %s: %s", tc_name, e)
        return False, ""


# ════════════════════════════════════════════════════════════════════
# Initial generation
# ════════════════════════════════════════════════════════════════════

def generate_one_test(
    seq: int,
    gen_client: LLMClient,
    ctx_d1: dict,
    ctx_d3: dict,
    imports: str,
    package: str,
    class_name: str,
    method_id: str,
    tc_dir: str,
    gen_log_dir: str,
    progress_tag: str = "",
) -> Optional[tuple]:
    save_dir = os.path.join(gen_log_dir, str(seq))
    os.makedirs(save_dir, exist_ok=True)

    pkg_decl = canonical_package_decl(package)
    tc_name  = f"{class_name}_{method_id}_{seq}Test"
    print(f"\n  ⚙️  [{_ts()}] {progress_tag} 生成 Test #{seq}: {tc_name} ...", flush=True)

    def _s(s): return _strip_pkg(s, imports, package)

    if not ctx_d3.get("c_deps") and not ctx_d3.get("m_deps"):
        ctx  = copy.deepcopy(ctx_d1)
        msgs = generate_messages(TEMPLATE_NO_DEPS, ctx)
        if remain_prompt_tokens(msgs) < 0:
            ctx["information"] = _s(ctx["information"])
            msgs = generate_messages(TEMPLATE_NO_DEPS, ctx)
    else:
        ctx  = copy.deepcopy(ctx_d3)
        msgs = generate_messages(TEMPLATE_WITH_DEPS, ctx)
        if remain_prompt_tokens(msgs) < 0:
            ctx["full_fm"] = _s(ctx.get("full_fm", ""))
            msgs = generate_messages(TEMPLATE_WITH_DEPS, ctx)

    if not msgs:
        print(f"    ❌ 无法构建 prompt", flush=True)
        return None

    gen_path = os.path.join(save_dir, "1_GEN.json")
    t0 = time.time()
    ok, gen_result = call_generator(gen_client, msgs, gen_path)
    elapsed = time.time() - t0

    if not ok:
        print(f"    ❌ LLM 调用失败 ({elapsed:.1f}s)", flush=True)
        return None, gen_result

    has_code, code, has_err = extract_code(gen_result.content)
    if not has_code or not code.strip():
        print(f"    ❌ 未提取到有效 Java 代码 ({elapsed:.1f}s)", flush=True)
        return None, gen_result

    if pkg_decl:
        code = repair_package(code, pkg_decl)
    code = repair_imports(code, imports)
    if pkg_decl:
        code = _ensure_package_first(code, pkg_decl)

    final_code = change_class_name(code, class_name, method_id, seq)
    if pkg_decl:
        final_code = repair_package(final_code, pkg_decl)
        final_code = _ensure_package_first(final_code, pkg_decl)

    tc_fname = f"{class_name}_{method_id}_{seq}Test.java"
    tc_path  = os.path.join(tc_dir, tc_fname)
    with open(tc_path, "w", encoding="utf-8") as f:
        f.write(final_code)
    with open(os.path.join(save_dir, "2_JAVA.java"), "w", encoding="utf-8") as f:
        f.write(final_code)

    test_cnt = _count_test_methods(final_code)
    print(f"    ✅ 生成成功{'⚠️(语法修复)' if has_err else ''} | "
          f"@Test数={test_cnt} | "
          f"tokens={gen_result.prompt_tokens}+{gen_result.completion_tokens} | "
          f"llm_time={gen_result.elapsed_seconds:.1f}s | {tc_fname}", flush=True)
    return final_code, gen_result


def _ensure_package_first(code: str, pkg_decl: str) -> str:
    lines = code.splitlines()
    pkg_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith("package "):
            pkg_idx = i
            break
    if pkg_idx is None or pkg_idx == 0:
        return code
    has_non_empty_before = any(
        l.strip() and not l.strip().startswith("//") and not l.strip().startswith("/*")
        for l in lines[:pkg_idx]
    )
    if not has_non_empty_before:
        return code
    pkg_line = lines.pop(pkg_idx)
    while lines and not lines[0].strip():
        lines.pop(0)
    lines.insert(0, "")
    lines.insert(0, pkg_line)
    return "\n".join(lines)


# ════════════════════════════════════════════════════════════════════
# Suite-level fix priority logic
# ════════════════════════════════════════════════════════════════════

def _get_suite_fix_mode(suite_score) -> str:
    """
    Determine the suite-level fix mode based on current state.

    Returns:
      "compile"   — at least one test has COMPILE_FAIL → fix compile errors first
      "exec"      — all compile, but at least one has exec error → fix exec errors
      "quality"   — all compile AND all exec pass → fix coverage/bugrevealing/redundancy
      "done"      — no issues
    """
    if not suite_score.all_compile_pass:
        return "compile"
    if suite_score.exec_pass_count < suite_score.n_tests:
        return "exec"
    if suite_score.problem_tests:
        return "quality"
    return "done"


def _should_fix_test(tc_name: str, issues: List[str], suite_fix_mode: str) -> bool:
    """
    Decide whether to fix this test given the current suite mode.

    compile mode: only fix tests with COMPILE_FAIL
    exec mode:    only fix tests with EXEC_FAIL or EXEC_TIMEOUT
    quality mode: fix tests with any issue (coverage, bug-revealing, redundancy)
    """
    if not issues:
        return False
    if suite_fix_mode == "compile":
        return "COMPILE_FAIL" in issues
    if suite_fix_mode == "exec":
        return "EXEC_FAIL" in issues or "EXEC_TIMEOUT" in issues
    if suite_fix_mode == "quality":
        return True
    return False


# ════════════════════════════════════════════════════════════════════
# build_fix_messages — simplified ChatUniTest style
# ════════════════════════════════════════════════════════════════════

def build_fix_messages(
    test_name: str,
    current_code: str,
    instructions: List[str],
    focal_method: str,
    class_name: str,
    ctx_d1: dict,
    ctx_d3: dict,
    imports: str,
    suite_summary: str,
    prev_unchanged: bool = False,
    diag=None,
    suite_fix_mode: str = "compile",
    cfg=None,
    issues: List[str] = None,
) -> List[Dict]:
    """
    Build fix messages for a single test file.

    The context injected depends on the suite_fix_mode:
    - compile: inject compile errors only
    - exec:    inject exec errors only
    - quality: inject coverage/bug-revealing info + Refiner instructions
    """
    if cfg is None:
        cfg = global_ablation_config()
    if issues is None:
        issues = []

    method_code = ctx_d1.get("information", ctx_d3.get("full_fm", ""))

    # Compile errors
    compile_ok     = getattr(diag, 'compile_ok', True) if diag else True
    exec_ok        = getattr(diag, 'exec_ok', True)    if diag else True
    compile_errors = list(getattr(diag, 'compile_errors', []))[:30] if diag else []
    exec_errors    = list(getattr(diag, 'exec_errors', []))[:30]    if diag else []

    # Coverage info — only in quality mode
    focal_line_rate    = None
    focal_branch_rate  = None
    focal_line_covered = None
    focal_line_total   = None
    missed_methods     = []
    partial_methods    = []
    if suite_fix_mode == "quality" and diag:
        focal_line_rate    = getattr(diag, 'focal_line_rate',    None)
        focal_branch_rate  = getattr(diag, 'focal_branch_rate',  None)
        focal_line_covered = getattr(diag, 'focal_line_covered', None)
        focal_line_total   = getattr(diag, 'focal_line_total',   None)
        missed_methods     = getattr(diag, 'missed_methods',     [])[:10]
        partial_methods    = getattr(diag, 'partial_methods',    [])[:10]

    unchanged_warning = (
        "\n\n⚠️ CRITICAL: Your previous output was IDENTICAL to the input. "
        "You MUST make substantial changes this time."
        if prev_unchanged else "")

    use_compile = suite_fix_mode in ("compile", "exec")
    use_cov     = suite_fix_mode == "quality" and cfg.use_coverage
    use_bug     = suite_fix_mode == "quality" and cfg.use_bug_revealing
    use_redun   = suite_fix_mode == "quality" and cfg.use_redundancy

    context = {
        "class_name":           class_name,
        "focal_method":         focal_method,
        "test_name":            test_name,
        "current_suite":        current_code,
        "suite_summary":        suite_summary,
        "method_code":          method_code,
        "imports":              imports,
        "contract_text":        "",
        "unchanged_warning":    unchanged_warning,
        "instructions_json":    json.dumps(instructions[:4], indent=2, ensure_ascii=False),
        "delete_tests_json":    "[]",
        "instructions_summary": "\n".join(
            f"  {i+1}. {instr}" for i, instr in enumerate(instructions[:4])
        ),
        "use_compile_exec":  use_compile,
        "use_coverage":      use_cov,
        "use_bug_revealing": use_bug,
        "use_redundancy":    use_redun,
        "compile_ok":     compile_ok,
        "exec_ok":        exec_ok,
        "compile_errors": compile_errors,
        "exec_errors":    exec_errors,
        "focal_line_rate":    focal_line_rate,
        "focal_branch_rate":  focal_branch_rate,
        "focal_line_covered": focal_line_covered,
        "focal_line_total":   focal_line_total,
        "issues":             issues,
        "max_test_methods":   _count_test_methods(current_code) + 2,
        "missed_methods":     missed_methods,
        "partial_methods":    partial_methods,
        "auto_fix_hints":     [],
        "error_summary":      "",
        # Simplified mode hint for the template
        "suite_fix_mode":     suite_fix_mode,
        "branch_hint_text":   "",
        "count_rationale":    "",
        "strategy_rationale": "",
    }

    msgs = generate_messages(TEMPLATE_FIX, context)
    if remain_prompt_tokens(msgs) < 0:
        context["method_code"] = method_code[:2000]
        msgs = generate_messages(TEMPLATE_FIX, context)

    if msgs and msgs[-1]["role"] == "user":
        suffix_parts = []

        if instructions:
            suffix_parts.append(
                f"\n\n## 📋 Repair Instructions\n{context['instructions_summary']}"
            )

        if prev_unchanged:
            suffix_parts.append(
                "\n\nMUST MAKE SUBSTANTIAL CHANGES: "
                "Previous output was identical. Rewrite the problematic sections completely."
            )

        if suite_fix_mode == "compile":
            suffix_parts.append(
                "\n\n⚠️ COMPILE FIX MODE: Fix ONLY the compile errors shown above. "
                "Do NOT change test logic or add new @Test methods."
            )
        elif suite_fix_mode == "exec":
            suffix_parts.append(
                "\n\n⚠️ EXEC FIX MODE: Fix ONLY the runtime errors shown above. "
                "Keep the same test structure, just correct the failing assertions/setup."
            )

        msgs[-1]["content"] += "".join(suffix_parts)

    return msgs


# ════════════════════════════════════════════════════════════════════
# focal_method_pipeline
# ════════════════════════════════════════════════════════════════════

def focal_method_pipeline(
    base_name: str,
    base_dir: str,
    submits: int,
    total: int,
) -> dict:
    process_start = time.time()
    progress_tag  = f"[{submits}/{total}]"
    _cfg = global_ablation_config()

    method_id, proj_name, class_name, method_name = parse_file_name(base_name)

    tc_dir      = os.path.join(base_dir, "test_cases")
    gen_log_dir = os.path.join(base_dir, "gen_logs")
    ref_log_dir = os.path.join(base_dir, "refine_logs")
    for d in [tc_dir, gen_log_dir, ref_log_dir]:
        os.makedirs(d, exist_ok=True)

    print(flush=True)
    _section(f"{progress_tag} {proj_name}.{class_name}.{method_name}  (id={method_id})", Fore.CYAN)
    print(f"  {Fore.CYAN}目录: {base_dir}{Style.RESET_ALL}", flush=True)
    print(f"  {Fore.CYAN}计划: 生成 {test_number} 个 Test 文件，最多 {max_rounds} 轮 Refine{Style.RESET_ALL}", flush=True)

    tracker    = LLMStatsTracker()
    time_stats = {
        "wall_clock":  {"start": process_start, "end": 0, "total_seconds": 0},
        "tool_chain":  {"total_seconds": 0},
        "rounds":      {},
    }

    try:
        with open(get_dataset_path(method_id, proj_name, class_name, method_name, "raw")) as f:
            raw_data = json.load(f)
        with open(get_dataset_path(method_id, proj_name, class_name, method_name, "1")) as f:
            ctx_d1 = json.load(f)
        with open(get_dataset_path(method_id, proj_name, class_name, method_name, "3")) as f:
            ctx_d3 = json.load(f)
    except FileNotFoundError as e:
        print(f"  {Fore.RED}❌ 数据集文件不存在: {e}{Style.RESET_ALL}", flush=True)
        return tracker.to_dict()

    package           = raw_data.get("package", "")
    imports           = raw_data.get("imports", "")
    focal_method_code = raw_data.get("source_code", ctx_d1.get("information", ""))
    pkg_decl          = canonical_package_decl(package)

    gen_client = make_generator_client()
    ref_client = make_refiner_client()

    proj_base    = os.path.dirname(os.path.abspath(project_dir))
    current_dir  = os.path.abspath(project_dir)
    current_name = os.path.basename(current_dir)

    if current_name.endswith("_f") or current_name.endswith("_F"):
        fixed_dir  = current_dir
        buggy_name = re.sub(r'_f$', '_b', current_name, flags=re.IGNORECASE)
        buggy_dir  = None
        cand = os.path.join(proj_base, buggy_name)
        if os.path.isdir(cand):
            buggy_dir = cand
        test_project_dir = fixed_dir
    else:
        buggy_dir  = current_dir
        fixed_name = re.sub(r'_b$', '_f', current_name, flags=re.IGNORECASE)
        fixed_dir  = None
        cand = os.path.join(proj_base, fixed_name)
        if os.path.isdir(cand):
            fixed_dir = cand
        test_project_dir = buggy_dir

    agent = RefineAgent(
        refiner_client     = ref_client,
        template_dir       = _PROMPT_DIR,
        buggy_dir          = buggy_dir,
        fixed_dir          = fixed_dir,
        skip_bug_revealing = (buggy_dir is None or fixed_dir is None),
    )

    # ── Phase 1: Initial generation ──────────────────────────────
    phase1_start = time.time()
    _divider("═", color=Fore.GREEN)
    print(Fore.GREEN + f"  ▶ Phase 1: 初始生成 {test_number} 个 Test 文件" + Style.RESET_ALL, flush=True)
    _divider("═", color=Fore.GREEN)

    current_codes: Dict[str, str] = {}

    for seq in range(1, test_number + 1):
        tc_name = f"{class_name}_{method_id}_{seq}Test"
        result = generate_one_test(
            seq=seq, gen_client=gen_client,
            ctx_d1=ctx_d1, ctx_d3=ctx_d3,
            imports=imports, package=package,
            class_name=class_name, method_id=method_id,
            tc_dir=tc_dir, gen_log_dir=gen_log_dir,
            progress_tag=progress_tag,
        )
        if result is None:
            continue
        code, gen_result = result
        tracker.record("generator", "phase1", gen_result)
        if code is None:
            continue
        current_codes[tc_name] = code

    phase1_elapsed = time.time() - phase1_start
    time_stats["rounds"]["phase1"] = round(phase1_elapsed, 2)
    print(f"\n  ✔ Phase 1 done: {len(current_codes)}/{test_number} OK  {phase1_elapsed:.1f}s", flush=True)

    if not current_codes:
        _save_stats(base_dir, tracker, time_stats, process_start)
        return tracker.to_dict()

    # ── Phase 2: Iterative Refine ─────────────────────────────────
    unchanged_counts: Dict[str, int] = {tc: 0 for tc in current_codes}

    for r in range(1, max_rounds + 1):
        round_start   = time.time()
        round_key     = f"round_{r}"
        round_log_dir = os.path.join(ref_log_dir, round_key)
        os.makedirs(round_log_dir, exist_ok=True)

        print(flush=True)
        _divider("═", color=Fore.MAGENTA)
        print(Fore.MAGENTA + f"  ▶ Round {r}/{max_rounds}: Refine ({len(current_codes)} Tests)" + Style.RESET_ALL)

        # ── Run RefineAgent (tools + Refiner LLM) ────────────────
        t0_agent = time.time()
        refine_result: RefineResult = agent.run(
            focal_method_result_dir=base_dir,
            project_dir=test_project_dir,
            focal_method=method_name,
            class_name=class_name,
            target_class_fqn=(
                f"{pkg_decl.replace('package ','').replace(';','')}.{class_name}"
                if pkg_decl else class_name),
            focal_method_code=focal_method_code,
            test_file_codes=current_codes,
            iteration=r,
            save_dir=round_log_dir,
            step_counter_start=1,
        )

        agent_elapsed = time.time() - t0_agent
        tool_elapsed  = agent_elapsed - refine_result.refiner_elapsed_seconds
        time_stats["tool_chain"]["total_seconds"] += max(0.0, tool_elapsed)

        if refine_result.refiner_prompt_tokens > 0 or refine_result.refiner_completion_tokens > 0:
            from llm_client import LLMCallResult as _LLMCallResult
            _ref_result = _LLMCallResult(
                content="", prompt_tokens=refine_result.refiner_prompt_tokens,
                completion_tokens=refine_result.refiner_completion_tokens,
                elapsed_seconds=refine_result.refiner_elapsed_seconds,
            )
            tracker.record("refiner", round_key, _ref_result)

        if refine_result.suite_score:
            _print_suite_score(refine_result.suite_score, tag=f"Round {r}")

        # Determine suite-level fix mode
        suite_score  = refine_result.suite_score
        suite_mode   = _get_suite_fix_mode(suite_score) if suite_score else "done"
        print(f"  🎯 Suite fix mode: {Fore.CYAN}{suite_mode}{Style.RESET_ALL}", flush=True)

        problematic = [n for n, s in refine_result.test_scores.items() if s.issues]
        if problematic:
            print(f"  📋 问题 Test 详细诊断 ({len(problematic)}/{len(current_codes)}):", flush=True)
            for tc_name in problematic:
                diag  = refine_result.test_diags.get(tc_name)
                score = refine_result.test_scores.get(tc_name)
                if diag and score:
                    _print_test_diag(tc_name, diag, score)
        else:
            print(f"  ✅ 所有 Test 通过质量检查", flush=True)

        if refine_result.suite_summary:
            print(f"\n  💬 Refiner 总体评价:", flush=True)
            for line in refine_result.suite_summary.splitlines():
                print(f"     {line}", flush=True)

        if suite_mode == "done":
            print(Fore.GREEN + f"\n  🎉 Round {r}: 无修复指令，提前结束" + Style.RESET_ALL, flush=True)
            time_stats["rounds"][round_key] = round(time.time() - round_start, 2)
            _log_refine_quality(round_log_dir, f"{class_name}.{method_name}", r,
                                refine_result.suite_score, refine_result.test_scores,
                                {}, refine_result.suite_summary)
            break

        # ── Fix loop: suite-level priority ───────────────────────
        fix_results = {"ok": [], "unchanged": [], "no_code": [], "fail": []}

        # Determine which tests to fix based on suite_mode
        tests_to_fix = {
            tc: refine_result.test_scores[tc].issues
            for tc in refine_result.instructions
            if tc in current_codes
               and _should_fix_test(tc, refine_result.test_scores.get(tc, type('', (), {'issues': []})()).issues, suite_mode)
        }

        # If Refiner gave no instructions for fixable tests, use rule-based hints
        for tc_name in list(current_codes.keys()):
            score = refine_result.test_scores.get(tc_name)
            if not score:
                continue
            if not _should_fix_test(tc_name, score.issues, suite_mode):
                continue
            if tc_name not in tests_to_fix:
                tests_to_fix[tc_name] = score.issues

        print(f"\n  🔧 Fix mode [{suite_mode}]: targeting {len(tests_to_fix)} tests", flush=True)

        for tc_name, issues in tests_to_fix.items():
            original_code = current_codes[tc_name]
            tc_diag       = refine_result.test_diags.get(tc_name)
            instructions  = refine_result.instructions.get(tc_name, [])

            # Fallback to rule-based hints if Refiner gave no instructions
            if not instructions:
                instructions = enrich_diag_with_fix_hints(tc_diag) if tc_diag else []

            prev_unchanged = unchanged_counts.get(tc_name, 0) > 0

            fix_dir = os.path.join(round_log_dir, f"fix_{tc_name}")
            os.makedirs(fix_dir, exist_ok=True)

            fix_msgs = build_fix_messages(
                test_name=tc_name,
                current_code=original_code,
                instructions=instructions,
                focal_method=method_name,
                class_name=class_name,
                ctx_d1=ctx_d1,
                ctx_d3=ctx_d3,
                imports=imports,
                suite_summary=refine_result.suite_summary,
                prev_unchanged=prev_unchanged,
                diag=tc_diag,
                suite_fix_mode=suite_mode,
                cfg=_cfg,
                issues=issues,
            )

            print(f"\n    [{_ts()}] Fix {tc_name} | mode={suite_mode} | issues={issues}", flush=True)
            try:
                prompt_json_path = os.path.join(fix_dir, "fix_prompt.json")
                with open(prompt_json_path, "w", encoding="utf-8") as pf:
                    json.dump(fix_msgs, pf, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"    ⚠ 无法保存 fix prompt: {e}", flush=True)
            try:
                fix_gen_path = os.path.join(fix_dir, "fix_gen.json")
                ok, fix_result = call_generator(gen_client, fix_msgs, fix_gen_path)
                tracker.record("generator", round_key, fix_result)

                if not ok:
                    fix_results["fail"].append(tc_name)
                    print(f"    ❌ {tc_name} FAILED | 生成器返回错误", flush=True)
                    continue

                has_code, new_code, _ = extract_code(fix_result.content)
                if not has_code or not new_code.strip():
                    fix_results["no_code"].append(tc_name)
                    print(f"    ❌ {tc_name} NO_CODE | 无法提取代码", flush=True)
                    continue

                if pkg_decl:
                    new_code = repair_package(new_code, pkg_decl)
                new_code = repair_imports(new_code, imports)
                if pkg_decl:
                    new_code = _ensure_package_first(new_code, pkg_decl)

                try:
                    seq_num = int(tc_name.split("_")[-1].replace("Test", ""))
                except ValueError:
                    seq_num = 1
                new_code = change_class_name(new_code, class_name, method_id, seq_num)
                if pkg_decl:
                    new_code = repair_package(new_code, pkg_decl)
                    new_code = _ensure_package_first(new_code, pkg_decl)

                changed = _code_changed(original_code, new_code)

                if not changed:
                    unchanged_counts[tc_name] = unchanged_counts.get(tc_name, 0) + 1
                    fix_results["unchanged"].append(tc_name)
                    print(f"    ⚠️  {tc_name} UNCHANGED (streak={unchanged_counts[tc_name]})", flush=True)
                    continue

                unchanged_counts[tc_name] = 0
                current_codes[tc_name] = new_code
                tc_path = os.path.join(tc_dir, f"{tc_name}.java")
                with open(tc_path, "w", encoding="utf-8") as f:
                    f.write(new_code)
                with open(os.path.join(fix_dir, "new.java"), "w", encoding="utf-8") as f:
                    f.write(new_code)

                fix_results["ok"].append(tc_name)
                orig_cnt = _count_test_methods(original_code)
                new_cnt  = _count_test_methods(new_code)
                print(
                    f"    ✅ {tc_name} FIXED | @Test: {orig_cnt}→{new_cnt} | "
                    f"tokens={fix_result.prompt_tokens}+{fix_result.completion_tokens}",
                    flush=True
                )

            except Exception as e:
                fix_results["fail"].append(tc_name)
                print(f"    ❌ {tc_name} EXCEPTION | {type(e).__name__}: {e}", flush=True)
                logger.exception("[FixLoop] Exception processing %s", tc_name)
                continue

        round_elapsed = time.time() - round_start
        time_stats["rounds"][round_key] = round(round_elapsed, 2)

        _log_refine_quality(
            round_log_dir, f"{class_name}.{method_name}", r,
            refine_result.suite_score, refine_result.test_scores,
            refine_result.instructions, refine_result.suite_summary,
            fix_results=fix_results,
        )

        print(flush=True)
        print(Fore.MAGENTA +
              f"  ✔ Round {r} [{suite_mode}] | 耗时 {round_elapsed:.1f}s | "
              f"成功: {len(fix_results['ok'])}  "
              f"未改变: {len(fix_results['unchanged'])}  "
              f"无代码: {len(fix_results['no_code'])}  "
              f"失败: {len(fix_results['fail'])}" + Style.RESET_ALL, flush=True)

    _save_stats(base_dir, tracker, time_stats, process_start)
    return tracker.to_dict()


def _save_stats(base_dir: str, tracker: LLMStatsTracker,
                time_stats: dict, process_start: float):
    end_time = time.time()
    time_stats["wall_clock"]["end"]           = end_time
    time_stats["wall_clock"]["total_seconds"] = round(end_time - process_start, 2)

    token_stats = tracker.to_dict()

    with open(os.path.join(base_dir, "token_stats.json"), "w", encoding="utf-8") as f:
        json.dump(token_stats, f, indent=2, ensure_ascii=False)
    with open(os.path.join(base_dir, "time_stats.json"), "w", encoding="utf-8") as f:
        json.dump(time_stats, f, indent=2, ensure_ascii=False)

    total_tok  = token_stats["all_total"].get("total_tokens", 0)
    llm_time   = token_stats["all_total"].get("llm_elapsed_seconds", 0.0)
    call_count = token_stats["all_total"].get("call_count", 0)
    wall_time  = time_stats["wall_clock"].get("total_seconds", 0.0)
    print(flush=True)
    _divider("═", color=Fore.BLUE)
    print(Fore.BLUE +
          f"  🏁 全部完成\n"
          f"     Wall-clock: {wall_time}s  |  "
          f"LLM time (纯API): {llm_time}s ({call_count} calls)  |  "
          f"Generator: {token_stats['generator']['total_tokens']}  |  "
          f"Refiner: {token_stats['refiner']['total_tokens']}  |  "
          f"all_total: {total_tok}\n"
          f"     Generator breakdown: prompt={token_stats['generator']['prompt_tokens']}, completion={token_stats['generator']['completion_tokens']}\n"
          f"     Refiner breakdown: prompt={token_stats['refiner']['prompt_tokens']}, completion={token_stats['refiner']['completion_tokens']}\n"
          f"     Rounds: {list(token_stats.get('rounds', {}).keys())}"
          + Style.RESET_ALL, flush=True)
    _divider("═", color=Fore.BLUE)


# ════════════════════════════════════════════════════════════════════
# Global accumulator + batch entry
# ════════════════════════════════════════════════════════════════════

def _acc_global(g: dict, s: dict):
    for role in ("generator", "refiner"):
        for k in ("prompt_tokens", "completion_tokens", "total_tokens"):
            g.setdefault(role, {}).setdefault(k, 0)
            g[role][k] += s.get(role, {}).get(k, 0)
        g[role].setdefault("llm_elapsed_seconds", 0.0)
        g[role]["llm_elapsed_seconds"] += s.get(role, {}).get("llm_elapsed_seconds", 0.0)
        g[role].setdefault("call_count", 0)
        g[role]["call_count"] += s.get(role, {}).get("call_count", 0)

    g.setdefault("all_total", {
        "prompt_tokens": 0, "completion_tokens": 0,
        "total_tokens": 0, "llm_elapsed_seconds": 0.0, "call_count": 0,
    })
    g["all_total"]["prompt_tokens"]       = (g["generator"].get("prompt_tokens", 0)
                                              + g["refiner"].get("prompt_tokens", 0))
    g["all_total"]["completion_tokens"]   = (g["generator"].get("completion_tokens", 0)
                                              + g["refiner"].get("completion_tokens", 0))
    g["all_total"]["total_tokens"]        = (g["generator"].get("total_tokens", 0)
                                              + g["refiner"].get("total_tokens", 0))
    g["all_total"]["llm_elapsed_seconds"] = round(
        g["generator"].get("llm_elapsed_seconds", 0.0)
        + g["refiner"].get("llm_elapsed_seconds", 0.0), 3)
    g["all_total"]["call_count"]          = (g["generator"].get("call_count", 0)
                                              + g["refiner"].get("call_count", 0))


def start_whole_process(
    source_dir: str,
    result_path: str,
    method_ids: Optional[List[str]] = None,
    multiprocess: bool = False,
):
    global_start = time.time()
    global_stats: dict = {
        "generator": {"prompt_tokens": 0, "completion_tokens": 0,
                      "total_tokens": 0, "llm_elapsed_seconds": 0.0, "call_count": 0},
        "refiner":   {"prompt_tokens": 0, "completion_tokens": 0,
                      "total_tokens": 0, "llm_elapsed_seconds": 0.0, "call_count": 0},
        "all_total": {"prompt_tokens": 0, "completion_tokens": 0,
                      "total_tokens": 0, "llm_elapsed_seconds": 0.0, "call_count": 0},
    }

    file_paths = []
    for root, _, files in os.walk(source_dir):
        for fn in sorted(files):
            if not fn.endswith(".json"):
                continue
            if method_ids:
                mid = fn.split("%")[0]
                if mid not in method_ids:
                    continue
            file_paths.append(os.path.join(root, fn))

    total = len(file_paths)
    tasks = []
    print(flush=True)
    _section(f"RefineTestGen  共 {total} 个 focal method", Fore.CYAN)
    if method_ids:
        print(f"  筛选 IDs: {method_ids}", flush=True)

    for i, fp in enumerate(file_paths, 1):
        _, base_name = os.path.split(fp)
        base_name_result = base_name.replace(".json", "").replace("%d1", "%d3")
        base_dir = os.path.join(result_path, base_name_result)
        os.makedirs(os.path.join(base_dir, "test_cases"), exist_ok=True)
        tasks.append((base_name, base_dir, i, total))

    if multiprocess:
        print(f"  🔀 多进程 (workers={process_number})", flush=True)
        with concurrent.futures.ProcessPoolExecutor(max_workers=process_number) as executor:
            futures = {executor.submit(focal_method_pipeline, *t): t for t in tasks}
            for fut in concurrent.futures.as_completed(futures):
                try:
                    _acc_global(global_stats, fut.result())
                except Exception as e:
                    logger.error("Worker error: %s", e)
    else:
        print("  📋 单进程顺序执行", flush=True)
        for t in tasks:
            _acc_global(global_stats, focal_method_pipeline(*t))

    elapsed = round(time.time() - global_start, 2)
    global_stats["wall_clock_seconds"]  = elapsed
    global_stats["total_focal_methods"] = total

    with open(os.path.join(result_path, "global_stats.json"), "w", encoding="utf-8") as f:
        json.dump(global_stats, f, indent=2, ensure_ascii=False)

    gt = global_stats["all_total"]
    print(Fore.MAGENTA + "\n===== 全局统计 =====" + Style.RESET_ALL)
    print(f"总任务数          : {total}")
    print(f"全局总耗时        : {elapsed}s")
    print(f"\n=== Token 统计===")
    print(f"Generator prompt  : {global_stats['generator']['prompt_tokens']}")
    print(f"Generator compl.  : {global_stats['generator']['completion_tokens']}")
    print(f"Generator total   : {global_stats['generator']['total_tokens']}")
    print(f"Generator LLM time: {global_stats['generator']['llm_elapsed_seconds']:.1f}s")
    print(f"Refiner prompt    : {global_stats['refiner']['prompt_tokens']}")
    print(f"Refiner compl.    : {global_stats['refiner']['completion_tokens']}")
    print(f"Refiner total     : {global_stats['refiner']['total_tokens']}")
    print(f"Refiner LLM time  : {global_stats['refiner']['llm_elapsed_seconds']:.1f}s")
    print(f"ALL total_tokens  : {gt.get('total_tokens', 0)}")
    print(f"ALL LLM time      : {gt.get('llm_elapsed_seconds', 0.0):.1f}s   ({gt.get('call_count', 0)} calls)")
    print(f"avg tokens/task   : {round(gt['total_tokens']/total, 1) if total else 0}")
    print(f"Generator per task: {round(global_stats['generator']['total_tokens']/total, 1) if total else 0}")
    print(f"Refiner per task  : {round(global_stats['refiner']['total_tokens']/total, 1) if total else 0}")
    print("=======================" + Style.RESET_ALL)

    return global_stats