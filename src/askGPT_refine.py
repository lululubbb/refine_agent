"""
askGPT_refine.py  (v6 — 断言修复 + @Test数量强制控制 + 平衡策略)

  针对一个 focal method：

  Phase 1 — 初始生成（一次性生成所有 test_number 个 Test 文件）
  ┌─────────────────────────────────────────────────────────┐
  │ for seq in 1..test_number:                              │
  │   Generator LLM → Token_1_{seq}Test.java                │
  │   写入 test_cases/ 目录                                  │
  └─────────────────────────────────────────────────────────┘

  Phase 2 — 迭代 Refine（固定 max_rounds 轮）
  ┌─────────────────────────────────────────────────────────┐
  │ for round in 1..max_rounds:                             │
  │   Refine Agent 对整个 Suite（N 个 Test 文件）评估：       │
  │     Tool 1: TestRunner 编译/执行所有 Test 文件            │
  │     Tool 2: 每个 Test 的 focal method 覆盖率              │
  │     Tool 3: 每个 Test 的 bug_revealing                   │
  │     Tool 4: Suite 内 Test 文件间 pairwise 相似度          │
  │   → TestScore × N（每个 Test 文件的各维度得分）           │
  │   → SuiteScore（N 个 Test 文件的整体统计）                │
  │   → Refiner LLM 生成 per-Test 指令                      │
  │                                                         │
  │   for each test in instructions:                        │
  │     Generator LLM 精修该 Test 文件（只改有指令的 Test）   │
  │     更新 test_cases/{test}.java                          │
  └─────────────────────────────────────────────────────────┘
  
核心改动（相对 v5）：
1. 新增 _enforce_test_method_limit()：代码层面强制截断多余@Test方法
2. 新增 _run_assert_fixer()：集成 MutAP 风格断言修复
3. generate_one_test() 生成后立即调用断言修复和数量控制
4. fix 循环中也调用断言修复
5. build_fix_messages() 中严格隔离：编译/执行失败时绝不混入覆盖率/bugrevealing指令
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
from typing import Dict, List, Optional, Set

from colorama import Fore, Style, init, Back

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
from suite_io import extract_test_methods, rebuild_suite
from tools import (
    get_dataset_path, parse_file_name, get_messages_tokens,
    repair_imports, repair_package, change_class_name, extract_code,
    canonical_package_decl,
)
from jinja2 import Environment, FileSystemLoader
from compile_error_analyzer import enrich_diag_with_fix_hints, get_error_summary
from scoring import sort_issues_by_priority, issues_at_priority_level
from stable_test_guard import StableTestGuard
import assert_fixer as _af_module

init()
logger = logging.getLogger(__name__)

_PROMPT_DIR = os.path.join(os.path.dirname(HERE), "prompt")
env = Environment(loader=FileSystemLoader(_PROMPT_DIR))

# ── @Test 数量硬性上限 ──────────────────────────────────────────────
_MAX_TEST_METHODS_DEFAULT = 15   # 绝对上限（降低以避免编译错误堆积）
_TEST_METHOD_HEADROOM     = 3   # fix时最多允许新增数量


# ════════════════════════════════════════════════════════════════════
# 新增：强制截断多余 @Test 方法（代码层面，不依赖 prompt）
# ════════════════════════════════════════════════════════════════════

def _enforce_test_method_limit(java_source: str, max_tests: int) -> str:
    """
    强制将测试文件中的 @Test 方法数量限制在 max_tests 以内。
    超出部分直接删除（保留前 max_tests 个）。

    这是代码层面的硬性控制，不依赖 LLM 遵守 prompt 中的数量限制。
    """
    current_count = len(re.findall(r'@Test\b', java_source))
    if current_count <= max_tests:
        return java_source

    lines = java_source.splitlines(keepends=True)
    test_count = 0
    cut_line = None

    for i, line in enumerate(lines):
        if re.search(r'@Test\b', line):
            test_count += 1
            if test_count > max_tests:
                cut_line = i
                break

    if cut_line is None:
        return java_source

    kept_lines = lines[:cut_line]
    source_so_far = ''.join(kept_lines)
    open_braces = source_so_far.count('{')
    close_braces = source_so_far.count('}')
    missing = open_braces - close_braces
    if missing > 0:
        source_so_far = source_so_far.rstrip()
        source_so_far += '\n' + '}\n' * missing

    logger.info("[TestLimit] Truncated from %d to %d @Test methods", current_count, max_tests)
    return source_so_far


# ════════════════════════════════════════════════════════════════════
# 新增：从被测类源码提取私有字段名
# ════════════════════════════════════════════════════════════════════

def _extract_private_fields_from_source(source_code: str) -> list:
    """从被测类源码中提取私有字段名"""
    pattern = re.compile(
        r'\bprivate\b[^;{(]*?\b([a-z]\w*)\s*(?:=\s*[^;]+)?;',
        re.MULTILINE
    )
    excluded = {'this', 'super', 'void', 'null', 'true', 'false',
                'int', 'long', 'double', 'float', 'boolean',
                'byte', 'char', 'short', 'final', 'static', 'new'}
    fields = []
    for m in pattern.finditer(source_code):
        name = m.group(1).strip()
        if name and name not in excluded and not name[0].isupper():
            fields.append(name)
    return fields


# ════════════════════════════════════════════════════════════════════
# 新增：集成 MutAP 断言修复
# ════════════════════════════════════════════════════════════════════

def _run_assert_fixer(
    java_source: str,
    class_name: str,
    method_id: str,
    seq,
    package: str,
    test_project_dir: str,
    focal_source_code: str = "",
) -> str:
    """
    对 LLM 生成的测试代码运行 MutAP 风格的断言修复。
    在写入 test_cases/ 之前调用。

    修复内容：
    1. 移除直接访问私有字段的断言（避免编译错误）
    2. 修复 assertEquals 中错误的预期值（用真实运行结果替换）
    """
    private_fields = _extract_private_fields_from_source(focal_source_code)

    try:
        from config import JUNIT_JAR, MOCKITO_JAR, LOG4J_JAR
        from assert_fixer import fix_assertions

        pkg_clean = re.sub(r'^package\s+', '', package or '').rstrip(';').strip()
        tc_class_name = f"{class_name}_{method_id}_{seq}Test"

        fixed = fix_assertions(
            java_source=java_source,
            class_name=tc_class_name,
            package=pkg_clean,
            project_dir=test_project_dir,
            junit_jar=JUNIT_JAR,
            private_fields=private_fields,
        )
        return fixed
    except Exception as e:
        logger.debug("[AssertFixer] skipped for %s_%s_%sTest: %s", class_name, method_id, seq, e)
        return java_source


# ════════════════════════════════════════════════════════════════════
# Progress printing helpers  (unchanged)
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


def _progress_bar(current: int, total: int, width: int = 20) -> str:
    filled = int(width * current / total) if total > 0 else 0
    return f"[{'█' * filled}{'░' * (width - filled)}] {current}/{total}"


def _code_changed(old: str, new: str) -> bool:
    def normalize(s):
        s = re.sub(r'//[^\n]*', '', s)
        s = re.sub(r'/\*.*?\*/', '', s, flags=re.DOTALL)
        return re.sub(r'\s+', ' ', s).strip()
    return normalize(old) != normalize(new)


def _count_test_methods(java_source: str) -> int:
    """Count @Test annotated methods in a Java source string."""
    return len(re.findall(r'@Test\b', java_source))


def _print_suite_score(suite_score, tag=""):
    ss = suite_score
    print(flush=True)
    _divider("·", color=Fore.YELLOW)
    print(Fore.YELLOW + f"  📊 Suite Score{' ' + tag if tag else ''}" + Style.RESET_ALL, flush=True)
    _divider("·", color=Fore.YELLOW)

    # 编译通过率（可能在消融模式下为 None）
    if ss.compile_pass_rate is not None:
        cr = ss.compile_pass_rate
        cr_c = Fore.GREEN if cr >= 0.8 else (Fore.YELLOW if cr >= 0.5 else Fore.RED)
        print(f"  {'编译通过率':<16}: {cr_c}{ss.compile_pass_count}/{ss.n_tests} ({cr*100:.0f}%){Style.RESET_ALL}", flush=True)
    else:
        print(f"  {'编译通过率':<16}: {Fore.WHITE}N/A (消融模式已禁用){Style.RESET_ALL}", flush=True)

    # 执行通过率（可能在消融模式下为 None）
    if ss.exec_pass_rate is not None:
        er = ss.exec_pass_rate
        er_c = Fore.GREEN if er >= 0.8 else (Fore.YELLOW if er >= 0.5 else Fore.RED)
        print(f"  {'执行通过率':<16}: {er_c}{ss.exec_pass_count}/{ss.n_tests} ({er*100:.0f}%){Style.RESET_ALL}", flush=True)
    else:
        print(f"  {'执行通过率':<16}: {Fore.WHITE}N/A (消融模式已禁用){Style.RESET_ALL}", flush=True)

    if ss.coverage_line_avg is not None:
        lc = ss.coverage_line_avg
        lc_c = Fore.GREEN if lc >= 0.8 else (Fore.YELLOW if lc >= 0.7 else Fore.RED)
        print(f"  {'行覆盖率(avg)':<16}: {lc_c}{lc*100:.1f}%  "
              f"(min={ss.coverage_line_min*100:.1f}%  max={ss.coverage_line_max*100:.1f}%){Style.RESET_ALL}", flush=True)
    else:
        print(f"  {'行覆盖率(avg)':<16}: {Fore.WHITE}N/A{Style.RESET_ALL}", flush=True)

    if ss.coverage_branch_avg is not None:
        bc = ss.coverage_branch_avg
        bc_c = Fore.GREEN if bc >= 0.8 else (Fore.YELLOW if bc >= 0.7 else Fore.RED)
        print(f"  {'分支覆盖率(avg)':<16}: {bc_c}{bc*100:.1f}%{Style.RESET_ALL}", flush=True)
    else:
        print(f"  {'分支覆盖率(avg)':<16}: {Fore.WHITE}N/A{Style.RESET_ALL}", flush=True)

    if ss.bug_reveal_checked > 0:
        br = ss.bug_reveal_rate
        br_c = Fore.GREEN if br >= 0.5 else (Fore.YELLOW if br > 0 else Fore.RED)
        print(f"  {'Bug揭示率':<16}: {br_c}{ss.bug_reveal_count}/{ss.bug_reveal_checked} ({br*100:.0f}%){Style.RESET_ALL}", flush=True)
    else:
        skip_reason = getattr(ss, '_bug_reveal_skip_reason', None)
        if skip_reason == "fixed_dir not provided":
            reason_str = f"未检测 {Fore.RED}(fixed project 目录不存在){Style.RESET_ALL}"
        elif skip_reason == "skip_bug_revealing=True":
            reason_str = f"未检测 {Fore.YELLOW}(skip_bug_revealing=True){Style.RESET_ALL}"
        elif ss.exec_pass_count == 0:
            reason_str = f"未检测 {Fore.YELLOW}(所有测试编译/执行失败){Style.RESET_ALL}"
        else:
            reason_str = f"{Fore.WHITE}未检测{Style.RESET_ALL}"
        print(f"  {'Bug揭示率':<16}: {reason_str}", flush=True)

    if ss.max_pairwise_similarity is not None:
        sim = ss.max_pairwise_similarity
        sim_c = Fore.RED if 1-sim > 0.9 else (Fore.YELLOW if 1-sim > 0.7 else Fore.GREEN)
        print(f"  {'最大用例相似度':<16}: {sim_c}{1-sim:.3f}{Style.RESET_ALL}", flush=True)

    if ss.problem_tests and ss.n_tests > 0:
        print(f"\n  ⚠️  问题分布（按优先级）：", flush=True)
        # Issue 5: show issues in priority order
        issue_order = ["COMPILE_FAIL", "EXEC_FAIL", "EXEC_TIMEOUT",
                       "NOT_BUG_REVEALING",
                       "LOW_LINE_COV", "LOW_BRANCH_COV",
                       "HIGH_REDUNDANCY"]
        issue_colors = {
            "COMPILE_FAIL":      Fore.RED,
            "EXEC_FAIL":         Fore.RED,
            "EXEC_TIMEOUT":      Fore.RED,
            "NOT_BUG_REVEALING": Fore.MAGENTA,
            "LOW_LINE_COV":      Fore.YELLOW,
            "LOW_BRANCH_COV":    Fore.YELLOW,
            "HIGH_REDUNDANCY":   Fore.CYAN,
        }
        for iss in issue_order:
            if iss in ss.problem_tests:
                c = issue_colors.get(iss, Fore.WHITE)
                print(f"    {c}[{iss}]{Style.RESET_ALL} → {', '.join(ss.problem_tests[iss])}", flush=True)
    elif ss.n_tests == 0:
        print(f"\n  ⚠️  无测试用例，无法进行质量检查。", flush=True)
    else:
        print(f"\\n  ✅ 无问题！Suite 全部通过质量检查。", flush=True)
        # ★ 修复问题5：说明质量检查标准，避免歧义
        print(f"  {Fore.WHITE}  质量标准: 编译通过 + 执行无异常 + 行覆盖率≥70%"
              f" + 分支覆盖率≥70% + 冗余度(≤70%){Style.RESET_ALL}", flush=True)
        # 如果 bug_revealing 未检测，单独说明
        if ss.bug_reveal_checked == 0:
            skip_reason = getattr(ss, '_bug_reveal_skip_reason', None)
            if skip_reason == "fixed_dir not provided":
                print(f"  {Fore.RED}  ⚠ Bug揭示率未检测：_f 版本项目不存在{Style.RESET_ALL}", flush=True)
            elif ss.exec_pass_count == 0:
                print(f"  {Fore.YELLOW}  ⚠ Bug揭示率未检测：所有测试执行失败{Style.RESET_ALL}", flush=True)

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
        "LOW_LINE_COV":      Fore.YELLOW,
        "LOW_BRANCH_COV":    Fore.YELLOW,
        "HIGH_REDUNDANCY":   Fore.CYAN,
    }

    data_valid = getattr(diag, 'diag_data_valid', True)
    validity_hint = "" if data_valid else f" {Fore.RED}[⚠️ 诊断数据无效]{Style.RESET_ALL}"

    print(f"\n  🔍 {Fore.WHITE}{tc_name}{Style.RESET_ALL}{validity_hint}  问题（优先级顺序）: "
          + "  ".join([f"{issue_colors.get(i, Fore.WHITE)}[{i}]{Style.RESET_ALL}" for i in issues]),
          flush=True)

    if not data_valid:
        return

    if "COMPILE_FAIL" in issues and diag.compile_errors:
        print(f"    {Fore.RED}编译错误 (前5条):{Style.RESET_ALL}", flush=True)
        for e in diag.compile_errors[:5]:
            print(f"      • {e}", flush=True)

    if ("EXEC_FAIL" in issues or "EXEC_TIMEOUT" in issues) and diag.exec_errors:
        print(f"    {Fore.RED}运行错误 (前5条):{Style.RESET_ALL}", flush=True)
        for e in diag.exec_errors[:5]:
            print(f"      • {e}", flush=True)

    # Issue 3: show focal line counts
    if score.focal_line_covered is not None and score.focal_line_total is not None and score.focal_line_total > 0:
        lc_pct = score.focal_line_covered / score.focal_line_total * 100
        lc_color = Fore.GREEN if lc_pct >= 70 else (Fore.YELLOW if lc_pct >= 40 else Fore.RED)
        print(f"    focal method行覆盖: {lc_color}{score.focal_line_covered}/{score.focal_line_total} ({lc_pct:.1f}%){Style.RESET_ALL}", flush=True)
    elif score.focal_line_coverage is not None:
        lc = score.focal_line_coverage
        lc_color = Fore.GREEN if lc >= 0.7 else (Fore.YELLOW if lc >= 0.4 else Fore.RED)
        print(f"    行覆盖率: {lc_color}{lc*100:.1f}%{Style.RESET_ALL}", flush=True)
    if score.focal_branch_coverage is not None:
        bc = score.focal_branch_coverage
        bc_color = Fore.GREEN if bc >= 0.7 else (Fore.YELLOW if bc >= 0.4 else Fore.RED)
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
# Prompt helpers (unchanged)
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
# Generator LLM call (unchanged)
# ════════════════════════════════════════════════════════════════════

def call_generator(gen_client: LLMClient, messages: List[Dict],
                   save_path: str) -> tuple[bool, LLMCallResult]:
    result = gen_client.chat(messages)
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump({
            "choices": [{"message": {"role": "assistant", "content": result.content}}],
            "usage":   result.to_usage_dict(),
        }, f, indent=2, ensure_ascii=False)
    return (not result.content.startswith("[LLM_ERROR]")), result


def _strip_pkg(s: str, imports: str, package: str) -> str:
    return s.replace(imports, "").replace(package, "").strip()


# ════════════════════════════════════════════════════════════════════
# Syntax validation (unchanged)
# ════════════════════════════════════════════════════════════════════

def _run_syntax_validation(
    java_code: str,
    tc_name: str,
    focal_class_context: str = "",
) -> tuple[bool, str]:
    """
    对 Java 代码执行语法验证。
    返回 (has_errors: bool, prompt_text: str)
    
    ★ 这是语法验证的统一入口，在以下时机调用：
      1. 初始生成后（generate_one_test）
      2. 每轮 fix 后（focal_method_pipeline 的 fix 循环）
    """
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
# Initial generation — 修改：调用断言修复 + 数量控制
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
    validation_issues_cache: dict = None,
    test_project_dir: str = "",
    focal_source_code: str = "",
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

    # ── 新增 Step A: 强制截断多余 @Test 方法 ──────────────────────
    final_code = _enforce_test_method_limit(final_code, _MAX_TEST_METHODS_DEFAULT)

    # ── 新增 Step B: MutAP 断言修复 ──────────────────────────────
    if test_project_dir:
        final_code = _run_assert_fixer(
            java_source=final_code,
            class_name=class_name,
            method_id=method_id,
            seq=seq,
            package=package,
            test_project_dir=test_project_dir,
            focal_source_code=focal_source_code,
        )

    tc_fname = f"{class_name}_{method_id}_{seq}Test.java"
    tc_path  = os.path.join(tc_dir, tc_fname)
    with open(tc_path, "w", encoding="utf-8") as f:
        f.write(final_code)
    with open(os.path.join(save_dir, "2_JAVA.java"), "w", encoding="utf-8") as f:
        f.write(final_code)

    _focal_ctx = ctx_d1.get("information", "") or ctx_d3.get("full_fm", "")
    has_errors, val_text = _run_syntax_validation(
        final_code, tc_name, focal_class_context=_focal_ctx
    )
    if val_text and validation_issues_cache is not None:
        validation_issues_cache[tc_name] = {
            "has_errors": has_errors,
            "prompt_text": val_text,
        }
        if has_errors:
            print(
                f"    ⚠️  [Validator] {tc_name} 发现静态问题，"
                f"将在 fix 阶段注入修复提示", flush=True
            )

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
# Issue 5: Fix priority ordering helper
# ════════════════════════════════════════════════════════════════════

def _get_fix_priority_for_test(issues: List[str]) -> str:
    """
    Return the top-priority issue category for a single test's issue list.
    Priority: compile > exec > bug_revealing > coverage > redundancy
    """
    top = issues_at_priority_level(issues)
    if not top:
        return "none"
    first = top[0]
    if first == "COMPILE_FAIL":
        return "compile"
    if first in ("EXEC_FAIL", "EXEC_TIMEOUT"):
        return "exec"
    if first == "NOT_BUG_REVEALING":
        return "bug_revealing"
    if first in ("LOW_LINE_COV", "LOW_BRANCH_COV"):
        return "coverage"
    if first == "HIGH_REDUNDANCY":
        return "redundancy"
    return "none"


# ════════════════════════════════════════════════════════════════════
# build_fix_messages  — per-test priority (Issue 3)
# ════════════════════════════════════════════════════════════════════

def build_fix_messages(
    test_name,
    current_code,
    instructions,
    focal_method,
    class_name,
    ctx_d1,
    ctx_d3,
    imports,
    suite_summary,
    prev_unchanged=False,
    diag=None,
    contract_text="",
    validation_issues: dict = None,
    cfg=None,
    issues: List[str] = None,
):
    """
    Build fix-phase LLM messages.

    Issue 2: coverage context only populated when LOW_COV issue is present.
    Issue 3: focal_line_covered / focal_line_total passed from diag.
    Issue 4: max_test_methods computed and passed to template.
    Issue 5: instructions filtered to top-priority issue group.
    """
    from scoring_ablation import AblationConfig, global_ablation_config
    if cfg is None:
        cfg = global_ablation_config()
    if issues is None:
        issues = []

    use_compile_exec  = bool(cfg.use_compile_exec)
    use_coverage      = bool(cfg.use_coverage)
    use_bug_revealing = bool(cfg.use_bug_revealing)
    use_redundancy    = bool(cfg.use_redundancy)

    # ── Per-test top priority ─────────────────────────────────────
    # Issue 3: use the THIS test's issues, not any suite-global filter
    top_issues = issues_at_priority_level(issues) if issues else []
    priority   = _get_fix_priority_for_test(issues)

    # Ablation filter
    filtered_issues = []
    for issue in top_issues:
        if issue in ("COMPILE_FAIL","EXEC_FAIL","EXEC_TIMEOUT") and not use_compile_exec: continue
        if issue in ("LOW_LINE_COV","LOW_BRANCH_COV") and not use_coverage: continue
        if issue == "NOT_BUG_REVEALING" and not use_bug_revealing: continue
        if issue == "HIGH_REDUNDANCY" and not use_redundancy: continue
        filtered_issues.append(issue)

    # Error info
    if use_compile_exec and diag:
        compile_ok     = getattr(diag, 'compile_ok', True)
        exec_ok        = getattr(diag, 'exec_ok', True)
        compile_errors = list(getattr(diag, 'compile_errors', []))
        exec_errors    = list(getattr(diag, 'exec_errors', []))
    else:
        compile_ok     = True
        exec_ok        = True
        compile_errors = []
        exec_errors    = []

    # Coverage info — only when LOW_COV is THIS test's issue
    has_coverage_issue = "LOW_LINE_COV" in filtered_issues or "LOW_BRANCH_COV" in filtered_issues
    if use_coverage and has_coverage_issue and diag:
        focal_line_rate    = getattr(diag, 'focal_line_rate',    None)
        focal_branch_rate  = getattr(diag, 'focal_branch_rate',  None)
        focal_line_covered = getattr(diag, 'focal_line_covered', None)
        focal_line_total   = getattr(diag, 'focal_line_total',   None)
    else:
        # Issue 2: do NOT pass coverage context if not a coverage issue
        focal_line_rate    = None
        focal_branch_rate  = None
        focal_line_covered = None
        focal_line_total   = None

    # ── @Test 数量限制：fix时只允许 current + headroom ──────────
    current_test_count = _count_test_methods(current_code)
    # 编译/执行失败时不允许增加新@Test，只修复现有
    if priority in ("compile", "exec"):
        max_test_methods = current_test_count  # 不允许新增
    else:
        max_test_methods = min(
            current_test_count + _TEST_METHOD_HEADROOM,
            _MAX_TEST_METHODS_DEFAULT,
        )
    max_test_methods = max(max_test_methods, 1)

    # ── 过滤指令到最高优先级 ─────────────────────────────────────
     # ── Filter instructions to per-test top priority ──────────────
    filtered_instructions = []
    for instr in instructions:
        il = instr.lower()
        if priority == "compile":
            if any(k in il for k in ["compile","syntax","error:","cannot find","private access",
                                      "incompatible","unreported","ambiguous","constructor",
                                      "does not override","abstract","implement"]):
                filtered_instructions.append(instr)
        elif priority == "exec":
            if any(k in il for k in ["exec","runtime","exception","timeout","assert","expected",
                                      "but was","thrown","null","reflection","field"]):
                filtered_instructions.append(instr)
        elif priority == "bug_revealing":
            if any(k in il for k in ["bug","revealing","assert","assertEquals","boundary",
                                      "precise","strengthen","exact"]):
                filtered_instructions.append(instr)
        elif priority == "coverage":
            if any(k in il for k in ["coverage","branch","line","path","case","boundary","test"]):
                filtered_instructions.append(instr)
        elif priority == "redundancy":
            if any(k in il for k in ["redundan","similar","structur","different"]):
                filtered_instructions.append(instr)
        else:
            filtered_instructions.append(instr)

    if not filtered_instructions and instructions:
        filtered_instructions = list(instructions)

    unchanged_warning = (
        "\n\n⚠️ CRITICAL: Your previous output was IDENTICAL to the input. "
        "You MUST make substantial changes this time."
        if prev_unchanged else "")

    method_code = ctx_d1.get("information", ctx_d3.get("full_fm",""))

    context = {
        "class_name":           class_name,
        "focal_method":         focal_method,
        "test_name":            test_name,
        "current_suite":        current_code,
        "suite_summary":        suite_summary,
        "method_code":          method_code,
        "imports":              imports,
        "contract_text":        contract_text,
        "unchanged_warning":    unchanged_warning,
        "instructions_json":    json.dumps(filtered_instructions[:4], indent=2, ensure_ascii=False),
        "delete_tests_json":    "[]",
        "instructions_summary": "\n".join(
            f"  {i+1}. {instr}" for i, instr in enumerate(filtered_instructions[:4])
        ),
        "use_compile_exec":  use_compile_exec,
        "use_coverage":      use_coverage,
        "use_bug_revealing": use_bug_revealing,
        "use_redundancy":    use_redundancy,
        "compile_ok":     compile_ok,
        "exec_ok":        exec_ok,
        "compile_errors": compile_errors[:30],
        "exec_errors":    exec_errors[:30],
        # Issue 2+3: coverage vars (None when not a coverage issue)
        "focal_line_rate":    focal_line_rate,
        "focal_branch_rate":  focal_branch_rate,
        "focal_line_covered": focal_line_covered,
        "focal_line_total":   focal_line_total,
        "issues": filtered_issues,
        "max_test_methods": max_test_methods,
        "missed_methods":  [],
        "partial_methods": [],
        "auto_fix_hints":  [],
        "error_summary":   "",
    }

    msgs = generate_messages(TEMPLATE_FIX, context)
    if remain_prompt_tokens(msgs) < 0:
        context["method_code"] = ctx_d3.get("full_fm", "")[:2000]
        msgs = generate_messages(TEMPLATE_FIX, context)

    if msgs and msgs[-1]["role"] == "user":
        suffix_parts = []

        suffix_parts.append(
            f"\n\n## 📋 Repair Instructions Summary\n{context['instructions_summary']}"
        )

        if prev_unchanged:
            suffix_parts.append(
                "\n\nMUST MAKE SUBSTANTIAL CHANGES: "
                "Previous output was identical to input. "
                "Rewrite the problematic test methods completely."
            )

        if validation_issues and test_name in validation_issues:
            _vdata = validation_issues[test_name]
            if _vdata.get("has_errors") and _vdata.get("prompt_text"):
                suffix_parts.append(
                    f"\n\n## Static Pre-validation Issues (fix these too):\n"
                    f"{_vdata['prompt_text']}"
                )

        # @Test 数量限制说明（简短）
        if priority in ("compile", "exec"):
            suffix_parts.append(
                f"\n\n⚠️ DO NOT add new @Test methods. Focus ONLY on fixing the "
                f"{'compile' if priority == 'compile' else 'runtime'} errors shown above. "
                f"Keep exactly the same test methods, just fix the error."
            )
        else:
            suffix_parts.append(
                f"\n\n⚠️ Keep total @Test methods ≤ {max_test_methods} "
                f"(currently {current_test_count})."
            )

        msgs[-1]["content"] += "".join(suffix_parts)

    return msgs


# ════════════════════════════════════════════════════════════════════
# focal_method_pipeline — 修改：传入 test_project_dir 给 generate_one_test
#                          + fix 循环中调用断言修复 + @Test 截断
# ════════════════════════════════════════════════════════════════════

def focal_method_pipeline(
    base_name: str,
    base_dir: str,
    submits: int,
    total: int,
) -> dict:
    process_start = time.time()
    progress_tag  = f"[{submits}/{total}]"

    method_id, proj_name, class_name, method_name = parse_file_name(base_name)

    tc_dir      = os.path.join(base_dir, "test_cases")
    gen_log_dir = os.path.join(base_dir, "gen_logs")
    ref_log_dir = os.path.join(base_dir, "refine_logs")
    for d in [tc_dir, gen_log_dir, ref_log_dir]:
        os.makedirs(d, exist_ok=True)

    print(flush=True)
    _section(f"{progress_tag} {proj_name}.{class_name}.{method_name}  (id={method_id})", Fore.CYAN)
    print(f"  {Fore.CYAN}目录: {base_dir}{Style.RESET_ALL}", flush=True)
    print(f"  {Fore.CYAN}计划: 生成 {test_number} 个 Test 文件（上限{_MAX_TEST_METHODS_DEFAULT}个@Test），最多 {max_rounds} 轮 Refine{Style.RESET_ALL}", flush=True)

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
    focal_source_code = raw_data.get("source_code", "")
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
    validation_issues_cache: dict = {}
    guard = StableTestGuard()
    # 设置 assert_fixer 日志到 base_dir
    _af_log = os.path.join(base_dir, "assert_fixer.log")
    try:
        import assert_fixer as _af_module
        if hasattr(_af_module, 'set_log_file'):
            _af_module.set_log_file(_af_log)
    except Exception:
        pass

    focal_class_ctx = ctx_d1.get("information", "") or ctx_d3.get("full_fm", "")

    for seq in range(1, test_number + 1):
        tc_name = f"{class_name}_{method_id}_{seq}Test"
        result = generate_one_test(
            seq=seq, gen_client=gen_client,
            ctx_d1=ctx_d1, ctx_d3=ctx_d3,
            imports=imports, package=package,
            class_name=class_name, method_id=method_id,
            tc_dir=tc_dir, gen_log_dir=gen_log_dir,
            progress_tag=progress_tag,
            validation_issues_cache=validation_issues_cache,
            test_project_dir=test_project_dir,       # ← 新增
            focal_source_code=focal_source_code,     # ← 新增
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
        # 更新稳定性追踪
        guard.update_after_round(r, refine_result.test_diags, current_codes)
        logger.info("[StableGuard] Round %d: %s", r, guard.summary())
        
        stable_tests = guard.get_stable_tests()
        unstable_tests = guard.get_unstable_tests()
        if stable_tests:
            print(f"  🛡 Stable (protected): {sorted(stable_tests)}", flush=True)
        if unstable_tests:
            print(f"  🔧 Unstable (needs fix): {sorted(unstable_tests)}", flush=True)

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

        if not refine_result.has_actionable_instructions():
            print(Fore.GREEN + f"\n  🎉 Round {r}: 无修复指令，提前结束" + Style.RESET_ALL, flush=True)
            time_stats["rounds"][round_key] = round(time.time() - round_start, 2)
            _log_refine_quality(round_log_dir, f"{class_name}.{method_name}", r,
                                refine_result.suite_score, refine_result.test_scores,
                                refine_result.instructions, refine_result.suite_summary)
            break

        _print_refine_instructions(refine_result.instructions, refine_result.delete_tests)

    # ── Fix loop ──────────────────────────────────────────────
    def _build_fix_messages_for_unstable(
        tc_name: str,
        current_code: str,
        instructions: List[str],
        focal_method: str,
        class_name: str,
        ctx_d1: dict,
        ctx_d3: dict,
        imports: str,
        diag,
        issues: List[str],
        prev_unchanged: bool,
        validation_issues: dict,
    ) -> List[Dict]:
        """
        为"不稳定"的test（有compile/exec错误）构建fix消息。
        原则：极简，只给错误信息，绝对禁止新增@Test。
        """
        compile_ok     = getattr(diag, 'compile_ok', True) if diag else True
        exec_ok        = getattr(diag, 'exec_ok', True) if diag else True
        compile_errors = list(getattr(diag, 'compile_errors', []))[:5] if diag else []
        exec_errors    = list(getattr(diag, 'exec_errors', []))[:3] if diag else []
    
        current_test_count = _count_test_methods(current_code)
        method_code = ctx_d1.get("information", ctx_d3.get("full_fm", ""))[:3000]
    
        # 只提取与当前错误类型直接相关的指令
        has_compile_fail = "COMPILE_FAIL" in issues
        has_exec_fail    = "EXEC_FAIL" in issues or "EXEC_TIMEOUT" in issues
    
        if has_compile_fail:
            relevant = [i for i in instructions if any(
                kw in i.lower() for kw in [
                    'compile', 'error', 'cannot find', 'private', 'abstract',
                    'incompatible', 'unreported', 'ambiguous', 'constructor',
                ]
            )] or instructions[:2]
        elif has_exec_fail:
            relevant = [i for i in instructions if any(
                kw in i.lower() for kw in [
                    'runtime', 'exception', 'assert', 'expected', 'but was',
                    'null', 'timeout', 'thrown',
                ]
            )] or instructions[:2]
        else:
            relevant = instructions[:2]
    
        relevant = relevant[:2]  # 最多2条，减少干扰
    
        context = {
            "class_name":        class_name,
            "focal_method":      focal_method,
            "test_name":         tc_name,
            "current_suite":     current_code,
            "suite_summary":     "",
            "method_code":       method_code,
            "imports":           imports,
            "contract_text":     "",
            "unchanged_warning": "",
            "instructions_json": json.dumps(relevant, indent=2, ensure_ascii=False),
            "delete_tests_json": "[]",
            "instructions_summary": "\n".join(f"  {i+1}. {inst}" for i, inst in enumerate(relevant)),
            "use_compile_exec":  True,
            "use_coverage":      False,
            "use_bug_revealing": False,
            "use_redundancy":    False,
            "compile_ok":        compile_ok,
            "exec_ok":           exec_ok,
            "compile_errors":    compile_errors,
            "exec_errors":       exec_errors,
            "focal_line_rate":   None,
            "focal_branch_rate": None,
            "focal_line_covered":None,
            "focal_line_total":  None,
            "issues":            issues,
            "max_test_methods":  current_test_count,  # 不允许新增
            "missed_methods":    [],
            "partial_methods":   [],
            "auto_fix_hints":    [],
            "error_summary":     "",
        }
    
        msgs = generate_messages(TEMPLATE_FIX, context)
        if remain_prompt_tokens(msgs) < 0:
            context["method_code"] = method_code[:1000]
            msgs = generate_messages(TEMPLATE_FIX, context)
    
        # 追加简洁约束（不堆叠）
        if msgs and msgs[-1]["role"] == "user":
            suffix = f"\n\nCRITICAL: Keep exactly {current_test_count} @Test methods. Fix ONLY the error above."
            if prev_unchanged:
                suffix += "\nPrevious output was identical. Make concrete changes to fix the error."
            # 只在compile失败时追加静态验证问题
            if has_compile_fail and validation_issues and tc_name in validation_issues:
                vdata = validation_issues[tc_name]
                if vdata.get("has_errors"):
                    suffix += f"\n\n{vdata.get('prompt_text', '')}"
            msgs[-1]["content"] += suffix
    
        return msgs
    
    
    def _build_fix_messages_for_stable(
        tc_name: str,
        current_code: str,
        instructions: List[str],
        focal_method: str,
        class_name: str,
        ctx_d1: dict,
        ctx_d3: dict,
        imports: str,
        diag,
        issues: List[str],
        prev_unchanged: bool,
    ) -> List[Dict]:
        """
        为"稳定"的test（compile+exec pass，但有覆盖率/bugrevealing问题）构建fix消息。
        原则：只允许修改方法体内的断言，不重写方法签名，不新增@Test（除非EXPAND）。
        """
        current_test_count = _count_test_methods(current_code)
        method_code = ctx_d1.get("information", ctx_d3.get("full_fm", ""))[:3000]
    
        has_bug_issue = "NOT_BUG_REVEALING" in issues
        has_cov_issue = "LOW_LINE_COV" in issues or "LOW_BRANCH_COV" in issues
    
        # 覆盖率问题：允许新增最多1个@Test
        if has_cov_issue and not has_bug_issue:
            max_tests = current_test_count + 3
        elif has_bug_issue:
            max_tests = current_test_count + 1
        else:
            max_tests = current_test_count 
            
        focal_line_rate    = getattr(diag, 'focal_line_rate',    None) if diag and has_cov_issue else None
        focal_branch_rate  = getattr(diag, 'focal_branch_rate',  None) if diag and has_cov_issue else None
        focal_line_covered = getattr(diag, 'focal_line_covered', None) if diag and has_cov_issue else None
        focal_line_total   = getattr(diag, 'focal_line_total',   None) if diag and has_cov_issue else None
    
        relevant = instructions[:3]
    
        context = {
            "class_name":        class_name,
            "focal_method":      focal_method,
            "test_name":         tc_name,
            "current_suite":     current_code,
            "suite_summary":     "",
            "method_code":       method_code,
            "imports":           imports,
            "contract_text":     "",
            "unchanged_warning": "",
            "instructions_json": json.dumps(relevant, indent=2, ensure_ascii=False),
            "delete_tests_json": "[]",
            "instructions_summary": "\n".join(f"  {i+1}. {inst}" for i, inst in enumerate(relevant)),
            "use_compile_exec":  False,
            "use_coverage":      has_cov_issue,
            "use_bug_revealing": has_bug_issue,
            "use_redundancy":    False,
            "compile_ok":        True,
            "exec_ok":           True,
            "compile_errors":    [],
            "exec_errors":       [],
            "focal_line_rate":   focal_line_rate,
            "focal_branch_rate": focal_branch_rate,
            "focal_line_covered":focal_line_covered,
            "focal_line_total":  focal_line_total,
            "issues":            issues,
            "max_test_methods":  max_tests,
            "missed_methods":    getattr(diag, 'missed_methods', [])[:5] if diag else [],
            "partial_methods":   getattr(diag, 'partial_methods', [])[:5] if diag else [],
            "auto_fix_hints":    [],
            "error_summary":     "",
        }
    
        msgs = generate_messages(TEMPLATE_FIX, context)
        if remain_prompt_tokens(msgs) < 0:
            context["method_code"] = method_code[:1000]
            msgs = generate_messages(TEMPLATE_FIX, context)
    
        if msgs and msgs[-1]["role"] == "user":
            if has_bug_issue:
                suffix = (
                    f"\n\nThis test compiles and runs. Strengthen existing assertions first."
                    f"You may add at most 1 new @Test method only if it can reveal the bug "
                    f"When possible, use assertEquals(expected, actual) for exact checks; "
                    f"without removing or weakening any existing @Test methods."
                )
            else:
                suffix = (
                    f"\n\nThis test compiles and runs. "
                    f"You may add at most 3 new @Test method for an uncovered branch. "
                    f"Do NOT modify existing @Test methods that already pass."
                )
            if prev_unchanged:
                suffix += " Previous output was identical—make a concrete change."
            msgs[-1]["content"] += suffix
    
        return msgs
    
    
    def _tiered_fix_loop(
        refine_result,
        guard,  # StableTestGuard instance
        current_codes: dict,
        tc_dir: str,
        round_log_dir: str,
        round_key: str,
        gen_client,
        tracker,
        ctx_d1: dict,
        ctx_d3: dict,
        imports: str,
        package: str,
        pkg_decl: str,
        class_name: str,
        method_id: str,
        method_name: str,
        focal_class_ctx: str,
        test_project_dir: str,
        focal_source_code: str,
        unchanged_counts: dict,
        validation_issues_cache: dict,
    ) -> dict:
        """
        核心fix循环：物理分离稳定测试和不稳定测试的修复策略。
    
        关键设计：
        1. 不稳定test（compile/exec fail）→ _build_fix_messages_for_unstable
        - 极简prompt，只看错误信息
        - 严格禁止新增@Test
        - fix后检查方法数量，如果变少则回滚（guard.guard_after_fix）
    
        2. 稳定test（pass但需增强）→ _build_fix_messages_for_stable
        - 不给编译/执行错误信息（避免LLM乱改）
        - 只给覆盖率/bugrevealing诊断
        - 仅允许方法体内修改或最多新增1个@Test
        - fix后如果原有@Test方法消失则回滚
    
        3. 既稳定又没问题的test → 根本不传给LLM（不在instructions里）
        """
        fix_results = {
            "ok": [], "unchanged": [], "no_code": [],
            "fail": [], "rollback": []
        }
    
        print(f"\n  🔧 Tiered fix loop: {len(refine_result.instructions)} tests", flush=True)
    
        for tc_name, instructions in refine_result.instructions.items():
            if tc_name not in current_codes:
                continue
    
            tc_score = refine_result.test_scores.get(tc_name)
            tc_diag  = refine_result.test_diags.get(tc_name)
            issues   = tc_score.issues if tc_score else []
            if not issues:
                continue  # 没问题，跳过
    
            stability = guard.get_stability(tc_name)
            is_stable = stability and stability.is_stable
    
            original_code = current_codes[tc_name]
            prev_unchanged = unchanged_counts.get(tc_name, 0) > 0
    
            fix_dir = os.path.join(round_log_dir, f"fix_{tc_name}")
            os.makedirs(fix_dir, exist_ok=True)
    
            # 选择对应的message构建策略
            if is_stable:
                tier_label = "🟡STABLE-ENHANCE"
                fix_msgs = _build_fix_messages_for_stable(
                    tc_name=tc_name,
                    current_code=original_code,
                    instructions=instructions,
                    focal_method=method_name,
                    class_name=class_name,
                    ctx_d1=ctx_d1,
                    ctx_d3=ctx_d3,
                    imports=imports,
                    diag=tc_diag,
                    issues=issues,
                    prev_unchanged=prev_unchanged,
                )
            else:
                tier_label = "🔴UNSTABLE-FIX"
                fix_msgs = _build_fix_messages_for_unstable(
                    tc_name=tc_name,
                    current_code=original_code,
                    instructions=instructions,
                    focal_method=method_name,
                    class_name=class_name,
                    ctx_d1=ctx_d1,
                    ctx_d3=ctx_d3,
                    imports=imports,
                    diag=tc_diag,
                    issues=issues,
                    prev_unchanged=prev_unchanged,
                    validation_issues=validation_issues_cache,
                )
    
            print(
                f"\n    [{_ts()}] {tier_label} {tc_name} | issues={issues}",
                flush=True
            )
    
            # 调用LLM
            fix_gen_path = os.path.join(fix_dir, "fix_gen.json")
            ok, fix_result = call_generator(gen_client, fix_msgs, fix_gen_path)
            tracker.record("generator", round_key, fix_result)
    
            if not ok:
                fix_results["fail"].append(tc_name)
                continue
    
            has_code, new_code, _ = extract_code(fix_result.content)
            if not has_code or not new_code.strip():
                fix_results["no_code"].append(tc_name)
                continue
    
            # 代码后处理（package/import修复）
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
    
            # @Test数量强制截断
            if is_stable:
                # 稳定test：最多允许+1
                max_allowed = _count_test_methods(original_code) + 1
            else:
                # 不稳定test：严格禁止新增
                max_allowed = _count_test_methods(original_code)
            new_code = _enforce_test_method_limit(new_code, max_allowed)
    
            # assert_fixer（只做安全清理，不替换值）
            if test_project_dir and focal_source_code:
                from assert_fixer import fix_assertions
                pf = _extract_private_fields_from_source(focal_source_code)
                pkg_clean = re.sub(r'^package\s+', '', package or '').rstrip(';').strip()
                new_code = fix_assertions(
                    java_source=new_code,
                    class_name=f"{class_name}_{method_id}_{seq_num}Test",
                    package=pkg_clean,
                    project_dir=test_project_dir,
                    private_fields=pf,
                )
    
            # 检查是否改变
            changed = _code_changed(original_code, new_code)
    
            if not changed:
                unchanged_counts[tc_name] = unchanged_counts.get(tc_name, 0) + 1
                fix_results["unchanged"].append(tc_name)
                print(
                    f"    ⚠️  {tc_name} UNCHANGED (streak={unchanged_counts[tc_name]})",
                    flush=True
                )
                continue
    
            # 稳定测试：代码层面保护（guard回滚）
            new_code, rolled_back = guard.guard_after_fix(tc_name, new_code, tc_dir)
            if rolled_back:
                fix_results["rollback"].append(tc_name)
                print(
                    f"    🔄 {tc_name} ROLLED BACK (stable test lost @Test methods)",
                    flush=True
                )
                continue
    
            # 语法验证（快速）
            unchanged_counts[tc_name] = 0
            has_val_errors, val_text = _run_syntax_validation(
                new_code, tc_name, focal_class_context=focal_class_ctx
            )
            if val_text:
                validation_issues_cache[tc_name] = {
                    "has_errors": has_val_errors,
                    "prompt_text": val_text,
                }
            else:
                validation_issues_cache.pop(tc_name, None)
    
            # 写入文件
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
                f"    ✅ {tc_name} FIXED | {tier_label} | "
                f"@Test: {orig_cnt}→{new_cnt} | "
                f"tokens={fix_result.prompt_tokens}+{fix_result.completion_tokens}",
                flush=True
            )
    
        return fix_results

        print(flush=True)
        print(Fore.MAGENTA +
              f"  ✔ Round {r} 完成 | 耗时 {round_elapsed:.1f}s | "
              f"成功: {len(fix_results['ok'])}  "
              f"未改变: {len(fix_results['unchanged'])}  "
              f"无代码: {len(fix_results['no_code'])}  "
              f"失败: {len(fix_results['fail'])}" + Style.RESET_ALL, flush=True)

        if fix_results["unchanged"] and not fix_results["ok"]:
            print(Fore.YELLOW +
                  f"  ⚠️  本轮所有精修输出均未发生变化\n"
                  f"  下一轮将加入 'prev_unchanged' 强化提示。" + Style.RESET_ALL, flush=True)

    _save_stats(base_dir, tracker, time_stats, process_start)
    return tracker.to_dict()


def _save_stats(base_dir: str, tracker: LLMStatsTracker,
                time_stats: dict, process_start: float):
    end_time = time.time()
    time_stats["wall_clock"]["end"]           = end_time
    time_stats["wall_clock"]["total_seconds"] = round(end_time - process_start, 2)

    token_stats = tracker.to_dict()
    token_stats["_legacy"] = {
        "generator": {
            "prompt":     token_stats["generator"]["prompt_tokens"],
            "completion": token_stats["generator"]["completion_tokens"],
            "total":      token_stats["generator"]["total_tokens"],
        },
        "refiner": {
            "prompt":     token_stats["refiner"]["prompt_tokens"],
            "completion": token_stats["refiner"]["completion_tokens"],
            "total":      token_stats["refiner"]["total_tokens"],
        },
        "all_total": token_stats["all_total"]["total_tokens"],
    }

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
# Global accumulator + batch entry (unchanged)
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