"""
askGPT_refine.py  (v5 — 删除版本信息注入，增强语法验证集成)
======================================

正确的 Pipeline 流程（与用户需求完全对齐）：

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

目录结构（与 ChatUniTest 完全兼容）：
  results_batch/Csv_1_b/scope_test%T%/
    1%Csv_1_b%Token%reset%d3/          ← base_dir (focal method)
      test_cases/                       ← ★ TestRunner 读取此处
        Token_1_1Test.java              ← test_num=1 的 Test 文件
        Token_1_2Test.java              ← test_num=2 的 Test 文件
        ...
        Token_1_5Test.java              ← test_num=5 的 Test 文件
      gen_logs/                         ← 初始生成记录（每个 Test 一个子目录）
        1/   1_GEN.json  2_JAVA.java
        2/   1_GEN.json  2_JAVA.java
        ...
      refine_logs/                      ← Refine 迭代记录（每轮一个子目录）
        round_1/
          tool_diag.json                ← 工具诊断 + 两级得分
          REFINE.json                   ← Refiner LLM 输出
          fix_1/  fix_gen.json  new.java  ← 对 Test_1 的精修
          fix_2/  fix_gen.json  new.java
          ...
        round_2/
          ...
      time_stats.json
      token_stats.json

  增加清晰的进度打印，包括：
  - 每个 focal method 的处理进度（进度条 + 时间估算）
  - Phase 1 每个 Test 文件的生成状态
  - Phase 2 每轮 Refine 的详细诊断输出：
      · Suite 整体评分（编译率/执行率/覆盖率/Bug 揭示率/冗余度）
      · 每个问题 Test 的具体问题标签 + 错误摘要
      · Refiner LLM 输出的修复指令预览
      · 每次 fix 后的状态变化
  - 彩色 ANSI 输出，按严重程度染色
  - 生成 refine_quality.jsonl 日志，方便后期离线分析覆盖率提升瓶颈

修复内容：
  Bug 1:  token_stats["rounds"] 始终为空 {}
          → 新增 _acc_round_tokens()，在 phase1 结束和每轮 round 结束时
            通过"快照基线 → 结束时相减"得到增量，写入 stats["rounds"]
  Bug 1b: 缺少 all_total 字段
          → _acc_gen / _acc_ref 每次累加后同步更新 token_stats["all_total"]
  Bug 3:  fix_gen.json 和 new.java 未生成
          → fix_gen.json 由 call_generator() 明确写出；
            new.java 在所有路径（成功/提取失败/LLM失败）都明确写出，
            失败时写注释占位，便于调试
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
from contract_integration import (
    extract_contract_for_focal_method,
    save_contract,
    enrich_ctx_with_contract,
    get_contract_text,
)
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
from contract_integration import (
    extract_contract_for_focal_method, save_contract,
    enrich_ctx_with_contract, get_contract_text,
)

init()
logger = logging.getLogger(__name__)

_PROMPT_DIR = os.path.join(os.path.dirname(HERE), "prompt")
env = Environment(loader=FileSystemLoader(_PROMPT_DIR))


# ════════════════════════════════════════════════════════════════════
# 进度打印工具
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
    """判断两段 Java 代码是否有实质区别（忽略空白和注释差异）。"""
    def normalize(s):
        s = re.sub(r'//[^\n]*', '', s)
        s = re.sub(r'/\*.*?\*/', '', s, flags=re.DOTALL)
        return re.sub(r'\s+', ' ', s).strip()
    return normalize(old) != normalize(new)


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
        print(f"  {'分支覆盖率(avg)':<16}: {bc_c}{bc*100:.1f}%  "
              f"(min={ss.coverage_branch_min*100:.1f}%  max={ss.coverage_branch_max*100:.1f}%){Style.RESET_ALL}"
              if hasattr(ss, 'coverage_branch_min') and ss.coverage_branch_min is not None
              else f"  {'分支覆盖率(avg)':<16}: {bc_c}{bc*100:.1f}%{Style.RESET_ALL}",
              flush=True)
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
    else:
        print(f"  {'最大用例相似度':<16}: {Fore.RED}N/A{Style.RESET_ALL}", flush=True)

    if ss.problem_tests and ss.n_tests > 0:
        print(f"\n  ⚠️  问题分布：", flush=True)
        issue_order = ["COMPILE_FAIL", "UNEXPECTED_EXEC_FAIL", "EXEC_TIMEOUT",
                       "LOW_LINE_COV", "LOW_BRANCH_COV", "NOT_BUG_REVEALING", "HIGH_REDUNDANCY"]
        issue_colors = {
            "COMPILE_FAIL":         Fore.RED,
            "UNEXPECTED_EXEC_FAIL": Fore.RED,
            "EXEC_TIMEOUT":         Fore.RED,
            "LOW_LINE_COV":         Fore.YELLOW,
            "LOW_BRANCH_COV":       Fore.YELLOW,
            "NOT_BUG_REVEALING":    Fore.MAGENTA,
            "HIGH_REDUNDANCY":      Fore.CYAN,
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
        "COMPILE_FAIL": Fore.RED, "EXEC_FAIL": Fore.RED, "EXEC_TIMEOUT": Fore.RED,
        "LOW_LINE_COV": Fore.YELLOW, "LOW_BRANCH_COV": Fore.YELLOW,
        "NOT_BUG_REVEALING": Fore.MAGENTA, "HIGH_REDUNDANCY": Fore.CYAN,
    }

    data_valid = getattr(diag, 'diag_data_valid', True)
    validity_hint = "" if data_valid else f" {Fore.RED}[⚠️ 诊断数据无效]{Style.RESET_ALL}"

    print(f"\n  🔍 {Fore.WHITE}{tc_name}{Style.RESET_ALL}{validity_hint}  问题: "
          + "  ".join([f"{issue_colors.get(i, Fore.WHITE)}[{i}]{Style.RESET_ALL}" for i in issues]),
          flush=True)

    if not data_valid:
        return

    if "COMPILE_FAIL" in issues and diag.compile_errors:
        print(f"    {Fore.RED}编译错误 (前5条):{Style.RESET_ALL}", flush=True)
        for e in diag.compile_errors[:5]:
            print(f"      • {e}", flush=True)

    if "EXEC_FAIL" in issues and diag.exec_errors:
        print(f"    {Fore.RED}运行错误 (前5条):{Style.RESET_ALL}", flush=True)
        for e in diag.exec_errors[:5]:
            print(f"      • {e}", flush=True)

    if score.focal_line_coverage is not None:
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
        print(f"    {Fore.MAGENTA}未揭示 Bug：建议针对边界条件和异常路径增加断言{Style.RESET_ALL}", flush=True)

    # 高冗余
    if "HIGH_REDUNDANCY" in issues and score.most_similar_to:
        rs = score.max_similarity or 0
        print(f"    {Fore.CYAN}冗余度 {rs:.3f}，与 {score.most_similar_to} 高度相似{Style.RESET_ALL}", flush=True)


def _print_refine_instructions(instructions: Dict[str, List[str]], delete_tests: List[str]):
    """打印 Refiner LLM 输出的修复指令预览。"""
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
# Prompt 工具
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
# Generator LLM 调用
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
# 语法验证工具（集中管理）
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
# 初始生成单个 Test 文件
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
) -> Optional[tuple]:
    save_dir = os.path.join(gen_log_dir, str(seq))
    os.makedirs(save_dir, exist_ok=True)

    pkg_decl = canonical_package_decl(package)
    tc_name  = f"{class_name}_{method_id}_{seq}Test"
    print(f"\n  ⚙️  [{_ts()}] {progress_tag} 生成 Test #{seq}: {tc_name} ...", flush=True)

    def _s(s): return _strip_pkg(s, imports, package)

    # 不再注入 version_constraints
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

    # ★ 语法验证：在生成后立即执行，将问题缓存供下一轮 fix 使用
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

    print(f"    ✅ 生成成功{'⚠️(语法修复)' if has_err else ''} | "
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
# ★ 渐进式修复策略：优先级判断
# ════════════════════════════════════════════════════════════════════

def _get_fix_priority(issues: List[str]) -> str:
    """
    返回当前 Test 最需要修复的问题类型。
    优先级: COMPILE_FAIL > EXEC_FAIL/TIMEOUT > LOW_COV > BUG_REVEALING > REDUNDANCY
    """
    if "COMPILE_FAIL" in issues:
        return "compile"
    if "EXEC_FAIL" in issues or "EXEC_TIMEOUT" in issues:
        return "exec"
    if "LOW_LINE_COV" in issues or "LOW_BRANCH_COV" in issues:
        return "coverage"
    if "NOT_BUG_REVEALING" in issues:
        return "bug_revealing"
    if "HIGH_REDUNDANCY" in issues:
        return "redundancy"
    return "none"


# ════════════════════════════════════════════════════════════════════
# Fix 单个 Test
# ════════════════════════════════════════════════════════════════════
def _select_key_compile_errors(compile_errors: List[str], max_items: int = 10) -> List[str]:
    """
    从完整编译错误列表中选取最有价值的错误行。
    优先 ': error:' 行，其次上下文行，跳过 'Note:' 等噪声。
    """
    error_lines = []
    context_lines = []
    for line in compile_errors:
        if ": error:" in line or line.strip().startswith("error:"):
            error_lines.append(line)
        elif line.strip() and not line.strip().startswith("Note:"):
            context_lines.append(line)
    selected = error_lines[:max_items]
    if len(selected) < max_items:
        selected += context_lines[:max_items - len(selected)]
    return selected if selected else compile_errors[:max_items]

def build_fix_messages(
    test_name, current_code, instructions, focal_method,
    class_name, ctx_d1, ctx_d3, imports, suite_summary,
    prev_unchanged=False, diag=None, contract_text="",
    validation_issues: dict = None, cfg=None,
    issues: List[str] = None,
):
    """
    构建 fix 阶段的 LLM 消息列表。
 
    修改要点：
    1. 消融模式开关（use_compile_exec / use_coverage / use_bug_revealing / use_redundancy）
       作为 Jinja2 模板变量传入，由模板决定显示哪些区块（问题5）。
    2. 完整的 compile_errors / exec_errors 从 diag 读取，
       tool_runner_adapter 已从 compiler_output/*.txt 和 test_output/*.txt 填充（问题1）。
    3. issues 列表传入模板，控制 BUG_REVEALING / HIGH_REDUNDANCY 区块（问题4/5）。
    4. 删除 error_summary（问题3：冗余，错误本身已足够清晰）。
    5. 修复指令不再按 priority 过度过滤，保留全部（问题2）。
    """
    from scoring_ablation import AblationConfig, global_ablation_config
    if cfg is None:
        cfg = global_ablation_config()
    if issues is None:
        issues = []
 
    # ── 消融模式开关 ──────────────────────────────────────────────
    use_compile_exec  = bool(cfg.use_compile_exec)
    use_coverage      = bool(cfg.use_coverage)
    use_bug_revealing = bool(cfg.use_bug_revealing)
    use_redundancy    = bool(cfg.use_redundancy)
 
    # ── 从 diag 读取完整错误信息 ──────────────────────────────────
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
 
    if use_coverage and diag:
        missed_methods  = list(getattr(diag, 'missed_methods', []))
        partial_methods = list(getattr(diag, 'partial_methods', []))
    else:
        missed_methods  = []
        partial_methods = []
 
    # ── 消融模式下过滤 issues ────────────────────────────────────
    filtered_issues = []
    for issue in issues:
        if issue in ("COMPILE_FAIL", "EXEC_FAIL", "EXEC_TIMEOUT") and not use_compile_exec:
            continue
        if issue in ("LOW_LINE_COV", "LOW_BRANCH_COV") and not use_coverage:
            continue
        if issue == "NOT_BUG_REVEALING" and not use_bug_revealing:
            continue
        if issue == "HIGH_REDUNDANCY" and not use_redundancy:
            continue
        filtered_issues.append(issue)
 
    priority = _get_fix_priority(filtered_issues) if filtered_issues else "none"

    # ── 新增：指令过滤逻辑 ────────────────────────────────────────────────────
    filtered_instructions = []
    for instr in instructions:
        instr_lower = instr.lower()
        
        # 1. 如果优先级是编译，只保留编译/语法指令
        if priority == "compile":
            if "compile" in instr_lower or "syntax" in instr_lower:
                filtered_instructions.append(instr)
        
        # 2. 如果优先级是执行，只保留执行/运行时/异常指令
        elif priority == "exec":
            if any(kw in instr_lower for kw in ["exec", "runtime", "exception", "timeout"]):
                filtered_instructions.append(instr)
        
        # 3. 如果优先级是覆盖率，只保留覆盖率/分支/行指令
        elif priority == "coverage":
            if any(kw in instr_lower for kw in ["coverage", "branch", "line"]):
                filtered_instructions.append(instr)
        
        # 4. 如果优先级是找 Bug，只保留 Bug 触发指令
        elif priority == "bug_revealing":
            if "bug" in instr_lower or "revealing" in instr_lower:
                filtered_instructions.append(instr)
        
        # 5. 如果优先级是去冗余
        elif priority == "redundancy":
            if "redundancy" in instr_lower or "similar" in instr_lower:
                filtered_instructions.append(instr)
        
        # 6. 无明确优先级或 none 时，保留所有指令（或根据需求自定义）
        else:
            filtered_instructions.append(instr)

    # 如果过滤后一条指令都没剩下（极端情况），回退到原始指令，防止模型丢失上下文
    if not filtered_instructions and instructions:
        filtered_instructions = list(instructions)

    merged_instructions = filtered_instructions
 
    unchanged_warning = (
        "\\n\\n⚠️ CRITICAL: Your previous output was IDENTICAL to the input. "
        "You MUST make substantial changes this time. "
        "Rewrite the failing test methods completely with different logic."
        if prev_unchanged else ""
    )
 
    method_code = ctx_d1.get("information", ctx_d3.get("full_fm", ""))
 
    context = {
        # 基础信息
        "class_name":           class_name,
        "focal_method":         focal_method,
        "test_name":            test_name,
        "current_suite":        current_code,
        "suite_summary":        suite_summary,
        "method_code":          method_code,
        "imports":              imports,
        "contract_text":        contract_text,
        "unchanged_warning":    unchanged_warning,
        # 修复指令
        "instructions_json":    json.dumps(merged_instructions[:5], indent=2, ensure_ascii=False),
        "delete_tests_json":    "[]",
        "instructions_summary": "\\n".join(
            f"  {i+1}. {instr}" for i, instr in enumerate(merged_instructions[:5])
        ),
        # ★ 消融模式开关（传入模板）
        "use_compile_exec":  use_compile_exec,
        "use_coverage":      use_coverage,
        "use_bug_revealing": use_bug_revealing,
        "use_redundancy":    use_redundancy,
        # 编译/运行状态和完整错误
        "compile_ok":     compile_ok,
        "exec_ok":        exec_ok,
        "compile_errors": compile_errors[:30],
        "exec_errors":    exec_errors[:30],
        # 覆盖率信息
        "missed_methods":  missed_methods[:20],
        "partial_methods": partial_methods[:10],
        # ★ issues 列表（控制 BUG_REVEALING / HIGH_REDUNDANCY 区块）
        "issues": filtered_issues,
        # 兼容性字段（保留但为空）
        "auto_fix_hints": [],
        "error_summary":  "",
    }
 
    msgs = generate_messages(TEMPLATE_FIX, context)
    if remain_prompt_tokens(msgs) < 0:
        context["method_code"] = ctx_d3.get("full_fm", "")[:2000]
        msgs = generate_messages(TEMPLATE_FIX, context)
 
    # ── 末尾追加关键提示 ─────────────────────────────────────────
    if msgs and msgs[-1]["role"] == "user":
        suffix_parts = []
 
        # 修复指令摘要（始终追加）
        suffix_parts.append(
            f"\\n\\n## 📋 Repair Instructions Summary\\n{context['instructions_summary']}"
        )
 
        # 编译错误关键行强化
        if use_compile_exec and not compile_ok and compile_errors:
            key_errors = _select_key_compile_errors(compile_errors, max_items=10)
            suffix_parts.append(
                "\\n\\n## ⚠️ KEY COMPILE ERRORS TO FIX:\\n"
                + "\\n".join(f"  {e}" for e in key_errors)
            )
 
        # 运行错误强化
        if use_compile_exec and compile_ok and not exec_ok and exec_errors:
            suffix_parts.append(
                "\\n\\n## ⚠️ KEY RUNTIME ERRORS TO FIX:\\n"
                + "\\n".join(f"  {e}" for e in exec_errors[:8])
            )
 
        # 未改变警告
        if prev_unchanged:
            suffix_parts.append(
                "\\n\\nMUST MAKE SUBSTANTIAL CHANGES: "
                "Previous output was identical to input. "
                "Rewrite the problematic test methods completely."
            )
 
        # 语法验证问题注入
        if validation_issues and test_name in validation_issues:
            _vdata = validation_issues[test_name]
            if _vdata.get("has_errors") and _vdata.get("prompt_text"):
                suffix_parts.append(
                    f"\\n\\n## Static Pre-validation Issues (fix these too):\\n"
                    f"{_vdata['prompt_text']}"
                )
 
        msgs[-1]["content"] += "".join(suffix_parts)
 
    return msgs

# ════════════════════════════════════════════════════════════════════
# 主流程 — focal_method_pipeline
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

    # ★ 删除版本信息提取
    # version_text 完全移除

    # 合约提取（保留，对有防御性检查的方法有价值）
    contract = extract_contract_for_focal_method(raw_data, ctx_d1)
    if contract and not contract.is_empty():
        save_contract(contract, base_dir)
        print(f"  {Fore.BLUE}📋 Program contract extracted: "
              f"{len(contract.preconditions)} preconditions, "
              f"{len(contract.exception_contracts)} exception contracts{Style.RESET_ALL}", flush=True)
    else:
        contract = None

    gen_client = make_generator_client()
    ref_client = make_refiner_client()

    proj_base    = os.path.dirname(os.path.abspath(project_dir))
    current_dir  = os.path.abspath(project_dir)
    current_name = os.path.basename(current_dir)

    if current_name.endswith("_f") or current_name.endswith("_F"):
        fixed_dir = current_dir
        buggy_name = re.sub(r'_f$', '_b', current_name, flags=re.IGNORECASE)
        buggy_dir = None
        cand = os.path.join(proj_base, buggy_name)
        if os.path.isdir(cand):
            buggy_dir = cand
        test_project_dir = fixed_dir
    else:
        buggy_dir = current_dir
        fixed_name = re.sub(r'_b$', '_f', current_name, flags=re.IGNORECASE)
        fixed_dir = None
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

    # ════════════════════════════════════════════════════════════════
    # Phase 1: 初始生成
    # ════════════════════════════════════════════════════════════════
    phase1_start = time.time()
    _divider("═", color=Fore.GREEN)
    print(Fore.GREEN + f"  ▶ Phase 1: 初始生成 {test_number} 个 Test 文件" + Style.RESET_ALL, flush=True)
    _divider("═", color=Fore.GREEN)

    current_codes: Dict[str, str] = {}
    validation_issues_cache: dict = {}

    # focal class 上下文（用于语法验证的动态规则）
    focal_class_ctx = ctx_d1.get("information", "") or ctx_d3.get("full_fm", "")

    for seq in range(1, test_number + 1):
        tc_name = f"{class_name}_{method_id}_{seq}Test"
        result = generate_one_test(
            seq=seq, gen_client=gen_client,
            ctx_d1=enrich_ctx_with_contract(ctx_d1, contract),
            ctx_d3=enrich_ctx_with_contract(ctx_d3, contract),
            imports=imports, package=package,
            class_name=class_name, method_id=method_id,
            tc_dir=tc_dir, gen_log_dir=gen_log_dir,
            progress_tag=progress_tag,
            validation_issues_cache=validation_issues_cache,
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

    # ════════════════════════════════════════════════════════════════
    # Phase 2: 迭代 Refine
    # ════════════════════════════════════════════════════════════════
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

        # ★ 注释：取消删除高冗余 Test 操作，只进行提升
        # # 删除高冗余 Test
        # for del_tc in refine_result.delete_tests:
        #     current_codes.pop(del_tc, None)
        #     unchanged_counts.pop(del_tc, None)
        #     tc_path = os.path.join(tc_dir, f"{del_tc}.java")
        #     if os.path.exists(tc_path):
        #         os.remove(tc_path)
        #         print(f"  🗑  已删除冗余 Test: {del_tc}", flush=True)

        # Fix 循环
        fix_results = {"ok": [], "unchanged": [], "no_code": [], "fail": []}
        print(f"\n  🔧 开始精修 {len(refine_result.instructions)} 个 Test ...", flush=True)

        for tc_name, instructions in refine_result.instructions.items():
            if tc_name not in current_codes:
                continue

            fix_dir = os.path.join(round_log_dir, f"fix_{tc_name}")
            os.makedirs(fix_dir, exist_ok=True)

            prev_unchanged = unchanged_counts.get(tc_name, 0) > 0
            print(f"\n    [{_ts()}] 精修 {Fore.WHITE}{tc_name}{Style.RESET_ALL} "
                  f"({len(instructions)} 条指令)"
                  + (f" {Fore.YELLOW}[上轮未改变，加强提示]{Style.RESET_ALL}" if prev_unchanged else ""),
                  flush=True)

            tc_diag  = refine_result.test_diags.get(tc_name)
            tc_score = refine_result.test_scores.get(tc_name)
            original_code = current_codes[tc_name]

            fix_msgs = build_fix_messages(
                test_name=tc_name, current_code=original_code,
                instructions=instructions, focal_method=method_name,
                class_name=class_name, ctx_d1=ctx_d1, ctx_d3=ctx_d3,
                imports=imports, suite_summary=refine_result.suite_summary,
                prev_unchanged=prev_unchanged, diag=tc_diag,
                contract_text=get_contract_text(contract),
                # ★ 不再传入 version_text
                validation_issues=validation_issues_cache,
                issues=tc_score.issues if tc_score else [],
            )

            try:
                prompt_json_path = os.path.join(fix_dir, "fix_prompt.json")
                with open(prompt_json_path, "w", encoding="utf-8") as pf:
                    json.dump(fix_msgs, pf, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"    ⚠ 无法保存 fix prompt: {e}", flush=True)

            fix_gen_path = os.path.join(fix_dir, "fix_gen.json")
            t0_fix = time.time()
            ok, fix_result = call_generator(gen_client, fix_msgs, fix_gen_path)
            t_fix = time.time() - t0_fix

            tracker.record("generator", round_key, fix_result)

            new_java_path = os.path.join(fix_dir, "new.java")

            if ok:
                has_code, new_code, _ = extract_code(fix_result.content)
                if has_code and new_code.strip():
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
                        print(f"    ⚠️  {Fore.YELLOW}{tc_name} 输出与原始完全相同 "
                              f"(连续相同: {unchanged_counts[tc_name]} 次){Style.RESET_ALL}", flush=True)
                        with open(new_java_path, "w", encoding="utf-8") as f:
                            f.write(f"// [UNCHANGED]\n")
                            f.write(new_code)
                    else:
                        unchanged_counts[tc_name] = 0

                        # ★ fix 后立即进行语法验证，更新缓存供下一轮使用
                        has_val_errors, val_text = _run_syntax_validation(
                            new_code, tc_name, focal_class_context=focal_class_ctx
                        )
                        if val_text:
                            validation_issues_cache[tc_name] = {
                                "has_errors": has_val_errors,
                                "prompt_text": val_text,
                            }
                            if has_val_errors:
                                print(f"    ⚠️  [Validator] fix 后仍有静态问题，"
                                      f"将在下轮注入提示", flush=True)
                        else:
                            # 修复成功，清除旧的验证缓存
                            validation_issues_cache.pop(tc_name, None)

                        current_codes[tc_name] = new_code
                        tc_path = os.path.join(tc_dir, f"{tc_name}.java")
                        with open(tc_path, "w", encoding="utf-8") as f:
                            f.write(new_code)
                        with open(new_java_path, "w", encoding="utf-8") as f:
                            f.write(new_code)
                        fix_results["ok"].append(tc_name)
                        print(f"    ✅ {tc_name} 精修成功 | "
                              f"prompt={fix_result.prompt_tokens} "
                              f"completion={fix_result.completion_tokens} | "
                              f"llm_time={fix_result.elapsed_seconds:.1f}s", flush=True)
                else:
                    fix_results["no_code"].append(tc_name)
                    with open(new_java_path, "w", encoding="utf-8") as f:
                        f.write("// [EXTRACT_FAILED]\n")
            else:
                fix_results["fail"].append(tc_name)
                with open(new_java_path, "w", encoding="utf-8") as f:
                    f.write(f"// [LLM_ERROR]\n")

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
# 全局汇总辅助
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


# ════════════════════════════════════════════════════════════════════
# 批量入口
# ════════════════════════════════════════════════════════════════════

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
    global_stats["wall_clock_seconds"]    = elapsed
    global_stats["total_focal_methods"]   = total

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