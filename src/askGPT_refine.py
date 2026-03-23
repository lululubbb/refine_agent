"""
askGPT_refine.py  (v4 — LLMStatsTracker 对齐 HITS baseline)
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
from typing import Dict, List, Optional

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
from llm_stats_tracker import LLMStatsTracker          # ★ 新增
from refine_agent import RefineAgent, RefineResult
from suite_io import extract_test_methods, rebuild_suite
from tools import (
    get_dataset_path, parse_file_name, get_messages_tokens,
    repair_imports, repair_package, change_class_name, extract_code,
    canonical_package_decl,
)
from jinja2 import Environment, FileSystemLoader

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
        # 去掉注释
        s = re.sub(r'//[^\n]*', '', s)
        s = re.sub(r'/\*.*?\*/', '', s, flags=re.DOTALL)
        # 压缩空白
        return re.sub(r'\s+', ' ', s).strip()
    import re
    return normalize(old) != normalize(new)


def _print_suite_score(suite_score, tag=""):
    ss = suite_score
    print(flush=True)
    _divider("·", color=Fore.YELLOW)
    print(Fore.YELLOW + f"  📊 Suite Score{' ' + tag if tag else ''}" + Style.RESET_ALL, flush=True)
    _divider("·", color=Fore.YELLOW)

    cr = ss.compile_pass_rate
    cr_c = Fore.GREEN if cr >= 0.8 else (Fore.YELLOW if cr >= 0.5 else Fore.RED)
    print(f"  {'编译通过率':<16}: {cr_c}{ss.compile_pass_count}/{ss.n_tests} ({cr*100:.0f}%){Style.RESET_ALL}", flush=True)

    er = ss.exec_pass_rate
    er_c = Fore.GREEN if er >= 0.8 else (Fore.YELLOW if er >= 0.5 else Fore.RED)
    print(f"  {'执行通过率':<16}: {er_c}{ss.exec_pass_count}/{ss.n_tests} ({er*100:.0f}%){Style.RESET_ALL}", flush=True)

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
        # ★ 修复问题3：区分不同的"未检测"原因
        skip_reason = getattr(ss, '_bug_reveal_skip_reason', None)
        if skip_reason == "fixed_dir not provided":
            reason_str = f"未检测 {Fore.RED}(fixed project 目录不存在，请确认 _f 版本路径){Style.RESET_ALL}"
        elif skip_reason == "skip_bug_revealing=True":
            reason_str = f"未检测 {Fore.YELLOW}(skip_bug_revealing=True){Style.RESET_ALL}"
        elif ss.exec_pass_count == 0:
            reason_str = f"未检测 {Fore.YELLOW}(所有测试编译/执行失败，无法检测){Style.RESET_ALL}"
        else:
            reason_str = f"{Fore.WHITE}未检测{Style.RESET_ALL}"
        print(f"  {'Bug揭示率':<16}: {reason_str}", flush=True)

    if ss.max_pairwise_similarity is not None:
        sim = ss.max_pairwise_similarity
        sim_c = Fore.RED if 1-sim > 0.9 else (Fore.YELLOW if 1-sim > 0.7 else Fore.GREEN)
        print(f"  {'最大用例相似度':<16}: {sim_c}{1-sim:.3f}{Style.RESET_ALL}", flush=True)
    else:
        print(f"  {'最大用例相似度':<16}: {Fore.RED}N/A (相似度计算失败，检查 Tool 4 日志){Style.RESET_ALL}", flush=True)

    if ss.problem_tests:
        print(f"\n  ⚠️  问题分布：", flush=True)
        issue_order = ["COMPILE_FAIL", "UNEXPECTED_EXEC_FAIL", "EXEC_TIMEOUT",
                       "LOW_LINE_COV", "LOW_BRANCH_COV", "NOT_BUG_REVEALING", "HIGH_REDUNDANCY"]
        issue_colors = {
            "COMPILE_FAIL":       Fore.RED,
            "EXPECTED_EXEC_FAIL": Fore.GREEN,  # good fail
            "UNEXPECTED_EXEC_FAIL": Fore.RED,  # bad fail
            "EXEC_TIMEOUT":       Fore.RED,
            "LOW_LINE_COV":       Fore.YELLOW,
            "LOW_BRANCH_COV":     Fore.YELLOW,
            "NOT_BUG_REVEALING":  Fore.MAGENTA,
            "HIGH_REDUNDANCY":    Fore.CYAN,
        }
        for iss in issue_order:
            if iss in ss.problem_tests:
                c = issue_colors.get(iss, Fore.WHITE)
                print(f"    {c}[{iss}]{Style.RESET_ALL} → {', '.join(ss.problem_tests[iss])}", flush=True)
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
    """打印单个 Test 文件的详细诊断，用于 refine 前的问题定位。"""
    issues = score.issues if score else []
    if not issues:
        return

    issue_colors = {
        "COMPILE_FAIL": Fore.RED, "EXPECTED_EXEC_FAIL": Fore.GREEN, "UNEXPECTED_EXEC_FAIL": Fore.RED, "EXEC_TIMEOUT": Fore.RED,
        "LOW_LINE_COV": Fore.YELLOW, "LOW_BRANCH_COV": Fore.YELLOW,
        "NOT_BUG_REVEALING": Fore.MAGENTA, "HIGH_REDUNDANCY": Fore.CYAN,
    }

    # ★ 提示诊断数据是否可信
    data_valid = getattr(diag, 'diag_data_valid', True)
    validity_hint = "" if data_valid else f" {Fore.RED}[⚠️ 诊断数据无效]{Style.RESET_ALL}"

    print(f"\n  🔍 {Fore.WHITE}{tc_name}{Style.RESET_ALL}{validity_hint}  问题: "
          + "  ".join([f"{issue_colors.get(i, Fore.WHITE)}[{i}]{Style.RESET_ALL}" for i in issues]),
          flush=True)

    if not data_valid:
        print(f"    {Fore.RED}⚠️  工具链诊断数据缺失（suite_diagnosis.json 为空）。"
              f"上报的 COMPILE_FAIL 可能是假阳性。{Style.RESET_ALL}", flush=True)
        return

    if "COMPILE_FAIL" in issues and diag.compile_errors:
        print(f"    {Fore.RED}编译错误 (前5条):{Style.RESET_ALL}", flush=True)
        for e in diag.compile_errors[:5]:
            print(f"      • {e}", flush=True)

    # 执行错误
    if ("EXPECTED_EXEC_FAIL" in issues or "UNEXPECTED_EXEC_FAIL" in issues or "EXEC_TIMEOUT" in issues) and diag.exec_errors:
        print(f"    {Fore.RED}运行错误 (前5条):{Style.RESET_ALL}", flush=True)
        for e in diag.exec_errors[:5]:
            print(f"      • {e}", flush=True)

    # 覆盖率
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


def remain_prompt_tokens(messages: List[Dict]) -> int:
    return MAX_PROMPT_TOKENS - get_messages_tokens(messages)


# ════════════════════════════════════════════════════════════════════
# Generator LLM 调用
# ════════════════════════════════════════════════════════════════════

def call_generator(gen_client: LLMClient, messages: List[Dict],
                   save_path: str) -> tuple[bool, LLMCallResult]:
    """调用 Generator LLM，保存原始响应，返回 (ok, LLMCallResult)。"""
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
) -> Optional[tuple]:
    save_dir = os.path.join(gen_log_dir, str(seq))
    os.makedirs(save_dir, exist_ok=True)

    pkg_decl = canonical_package_decl(package)
    tc_name  = f"{class_name}_{method_id}_{seq}Test"
    print(f"\n  ⚙️  [{_ts()}] {progress_tag} 生成 Test #{seq}: {tc_name} ...", flush=True)

    def _s(s): return _strip_pkg(s, imports, package)

    # 选模板
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
# Fix 单个 Test
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
) -> List[Dict]:
    # ★ 从 diag 提取详细信息
    compile_ok      = getattr(diag, 'compile_ok',      True)  if diag else True
    exec_ok         = getattr(diag, 'exec_ok',         True)  if diag else True
    compile_errors  = getattr(diag, 'compile_errors',  [])    if diag else []
    exec_errors     = getattr(diag, 'exec_errors',     [])    if diag else []
    missed_methods  = getattr(diag, 'missed_methods',  [])    if diag else []
    partial_methods = getattr(diag, 'partial_methods', [])    if diag else []

    instructions_summary = "\n".join(
        f"  {i+1}. {instr}" for i, instr in enumerate(instructions)
    )

    unchanged_warning = ""
    if prev_unchanged:
        unchanged_warning = (
            "\n\n⚠️ CRITICAL: Your previous output was IDENTICAL to the input. "
            "You MUST make substantial changes this time. "
            "The output MUST differ meaningfully from the current_suite below."
        )

    context = {
        "class_name":           class_name,
        "focal_method":         focal_method,
        "test_name":            test_name,
        "current_suite":        current_code,
        "suite_summary":        suite_summary,
        "instructions_json":    json.dumps(instructions, indent=2, ensure_ascii=False),
        "delete_tests_json":    "[]",
        "method_code":          ctx_d1.get("information", ctx_d3.get("full_fm", "")),
        "imports":              imports,
        "instructions_summary": instructions_summary,
        "unchanged_warning":    unchanged_warning,
        "compile_ok":      compile_ok,
        "exec_ok":         exec_ok,
        "compile_errors":  compile_errors[:10],
        "exec_errors":     exec_errors[:10],
        "missed_methods":  missed_methods[:20],
        "partial_methods": partial_methods[:10],
    }
    msgs = generate_messages(TEMPLATE_FIX, context)
    if remain_prompt_tokens(msgs) < 0:
        context["method_code"] = ctx_d3.get("full_fm", "")
        msgs = generate_messages(TEMPLATE_FIX, context)

    # ★ 在 user message 末尾追加强制要求（无论模板是否支持 unchanged_warning 变量）
    if msgs and msgs[-1]["role"] == "user":
        suffix = (
            f"\n\n## Repair Instructions Summary\n{instructions_summary}"
            f"\n\n## MANDATORY REQUIREMENT\n"
            f"Your output MUST be substantially different from the current test file. "
            f"Apply ALL instructions above. Do NOT output the same code as the input."
        )
        if prev_unchanged:
            suffix += (
                "\n\n⚠️ WARNING: The previous attempt produced output identical to the input. "
                "This time you MUST make concrete, visible changes to the code."
            )
        msgs[-1]["content"] += suffix
        if not compile_ok and compile_errors:
            suffix += (
                f"\n\n## COMPILE ERRORS REMINDER (MUST FIX FIRST)\n"
                + "\n".join(f"  {e}" for e in compile_errors[:5])
            )
        if not exec_ok and exec_errors:
            suffix += (
                f"\n\n## EXECUTION ERRORS REMINDER\n"
                + "\n".join(f"  {e}" for e in exec_errors[:5])
            )

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
    """
    针对一个 focal method 的完整 pipeline：
    1. 生成 test_number 个 Test 文件（Phase 1）
    2. max_rounds 轮 Refine Agent + per-Test 精修（Phase 2）
    """
    process_start = time.time()
    progress_tag  = f"[{submits}/{total}]"

    method_id, proj_name, class_name, method_name = parse_file_name(base_name)

    # ── 目录 ─────────────────────────────────────────────────────
    tc_dir      = os.path.join(base_dir, "test_cases")
    gen_log_dir = os.path.join(base_dir, "gen_logs")
    ref_log_dir = os.path.join(base_dir, "refine_logs")
    for d in [tc_dir, gen_log_dir, ref_log_dir]:
        os.makedirs(d, exist_ok=True)

    # ── 打印 focal method 处理头 ──────────────────────────────────
    print(flush=True)
    _section(f"{progress_tag} {proj_name}.{class_name}.{method_name}  (id={method_id})", Fore.CYAN)
    print(f"  {Fore.CYAN}目录: {base_dir}{Style.RESET_ALL}", flush=True)
    print(f"  {Fore.CYAN}计划: 生成 {test_number} 个 Test 文件，最多 {max_rounds} 轮 Refine{Style.RESET_ALL}", flush=True)

    # ── ★ 统一 Token / Time 统计（与 HITS LLMStatsTracker 对齐）──
    tracker    = LLMStatsTracker()
    time_stats = {
        "wall_clock":  {"start": process_start, "end": 0, "total_seconds": 0},
        "tool_chain":  {"total_seconds": 0},   # TestRunner + 相似度等非 LLM 耗时
        "rounds":      {},                      # per-phase wall-clock
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

    proj_base     = os.path.dirname(os.path.abspath(project_dir))
    current_dir   = os.path.abspath(project_dir)
    current_name  = os.path.basename(current_dir)
 
    # ── Determine fixed_dir (for test generation) and buggy_dir (for bug_revealing) ──
    # Support both _f-first (new default) and _b-first (legacy) workflows.
    if current_name.endswith("_f") or current_name.endswith("_F"):
        # New workflow: project_dir points to the fixed version.
        # Tests are generated and evaluated on the fixed version.
        # Bug revealing is tested on the buggy (_b) sibling.
        fixed_dir = current_dir
        _proj_base_name = re.sub(r'_f$', '', current_name, flags=re.IGNORECASE)
        buggy_dir = None
        for cand in [
            os.path.join(proj_base, current_name.replace("_f", "_b").replace("_F", "_B")),
            os.path.join(proj_base, f"{_proj_base_name}_b"),
        ]:
            if os.path.isdir(cand):
                buggy_dir = cand
                print(f"  {Fore.GREEN}✅ found buggy_dir (for bug_revealing): {cand}{Style.RESET_ALL}", flush=True)
                break
        if buggy_dir is None:
            print(f"  {Fore.RED}⚠ buggy_dir (_b) not found, bug_revealing will be skipped.{Style.RESET_ALL}", flush=True)
        # The TestRunner compiles/runs tests on the fixed project
        test_project_dir = fixed_dir
    else:
        # Legacy workflow: project_dir points to the buggy version (original behaviour).
        buggy_dir = current_dir
        _proj_base_name = re.sub(r'_b$', '', current_name, flags=re.IGNORECASE)
        fixed_dir = None
        for cand in [
            os.path.join(proj_base, current_name.replace("_b", "_f").replace("_B", "_F")),
            os.path.join(proj_base, f"{_proj_base_name}_f"),
        ]:
            if os.path.isdir(cand):
                fixed_dir = cand
                print(f"  {Fore.GREEN}✅ found fixed_dir: {cand}{Style.RESET_ALL}", flush=True)
                break
        if fixed_dir is None:
            print(f"  {Fore.RED}⚠ fixed_dir not found, bug_revealing will be skipped.{Style.RESET_ALL}", flush=True)
        # The TestRunner compiles/runs tests on the buggy project (legacy)
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
    gen_failures = []

    for seq in range(1, test_number + 1):
        tc_name = f"{class_name}_{method_id}_{seq}Test"
        result = generate_one_test(
            seq         = seq,
            gen_client  = gen_client,
            ctx_d1      = ctx_d1,
            ctx_d3      = ctx_d3,
            imports     = imports,
            package     = package,
            class_name  = class_name,
            method_id   = method_id,
            tc_dir      = tc_dir,
            gen_log_dir = gen_log_dir,
            progress_tag= progress_tag,
        )
        if result is None:
            gen_failures.append(seq)
            logger.warning("%s test_%d generation failed", progress_tag, seq)
            continue
        code, gen_result = result
        # ★ 按 HITS 口径记录：role="generator", phase="phase1", 纯 LLM 调用时间
        tracker.record("generator", "phase1", gen_result)
        print(f"  📊 [TokenLog] Recorded generator phase1: {gen_result.prompt_tokens}+{gen_result.completion_tokens} tokens", flush=True)
        if code is None:
            gen_failures.append(seq)
            continue
        current_codes[tc_name] = code

    phase1_elapsed = time.time() - phase1_start
    time_stats["rounds"]["phase1"] = round(phase1_elapsed, 2)

    success_n, fail_n = len(current_codes), len(gen_failures)
    sc = Fore.GREEN if fail_n == 0 else (Fore.YELLOW if success_n > 0 else Fore.RED)
    print(sc + f"\n  ✔ Phase 1 完成 {_progress_bar(success_n, test_number)}  "
          f"失败: {fail_n}  耗时: {phase1_elapsed:.1f}s" + Style.RESET_ALL, flush=True)

    if not current_codes:
        print(f"  {Fore.RED}❌ 全部 Test 生成失败{Style.RESET_ALL}", flush=True)
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
        print(Fore.MAGENTA +
              f"  ▶ Phase 2 Round {r}/{max_rounds}: Refine Agent ({len(current_codes)} Tests)"
              + Style.RESET_ALL, flush=True)
        _divider("═", color=Fore.MAGENTA)

        # ── Refine Agent（包含工具链 + Refiner LLM）─────────────────
        print(f"  [{_ts()}] 运行工具链 (编译/执行/覆盖率/相似度) ...", flush=True)
        t0_agent = time.time()
        refine_result: RefineResult = agent.run(
            focal_method_result_dir = base_dir,
            project_dir             = test_project_dir,
            focal_method            = method_name,
            class_name              = class_name,
            target_class_fqn        = (
                f"{pkg_decl.replace('package ','').replace(';','')}.{class_name}"
                if pkg_decl else class_name),
            focal_method_code       = focal_method_code,
            test_file_codes         = current_codes,
            iteration               = r,
            save_dir                = round_log_dir,
            step_counter_start      = 1,
        )
        agent_elapsed = time.time() - t0_agent
        # 工具链耗时 = agent 总耗时 - refiner LLM 调用时间
        tool_elapsed = agent_elapsed - refine_result.refiner_elapsed_seconds
        time_stats["tool_chain"]["total_seconds"] += max(0.0, tool_elapsed)
        print(f"  [{_ts()}] 工具链完成  耗时: {agent_elapsed:.1f}s "
              f"(LLM: {refine_result.refiner_elapsed_seconds:.1f}s, "
              f"工具链: {max(0.0, tool_elapsed):.1f}s)", flush=True)

        # ★ 记录 Refiner LLM token（仅在真正调用了 LLM 时记录）
        if refine_result.refiner_prompt_tokens > 0 or refine_result.refiner_completion_tokens > 0:
            # 构造一个临时 LLMCallResult 供 tracker 使用
            from llm_client import LLMCallResult as _LLMCallResult
            _ref_result = _LLMCallResult(
                content           = "",
                prompt_tokens     = refine_result.refiner_prompt_tokens,
                completion_tokens = refine_result.refiner_completion_tokens,
                elapsed_seconds   = refine_result.refiner_elapsed_seconds,
            )
            tracker.record("refiner", round_key, _ref_result)
            print(f"  📊 [TokenLog] Recorded refiner {round_key}: {_ref_result.prompt_tokens}+{_ref_result.completion_tokens} tokens", flush=True)

        if refine_result.suite_score:
            _print_suite_score(refine_result.suite_score, tag=f"Round {r}")

        # 打印诊断
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

        # 删除高冗余 Test
        for del_tc in refine_result.delete_tests:
            current_codes.pop(del_tc, None)
            unchanged_counts.pop(del_tc, None)
            tc_path = os.path.join(tc_dir, f"{del_tc}.java")
            if os.path.exists(tc_path):
                os.remove(tc_path)
                print(f"  🗑  已删除冗余 Test: {del_tc}", flush=True)

        # ── Fix 循环 ─────────────────────────────────────────────
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

            tc_diag = refine_result.test_diags.get(tc_name)
            fix_msgs = build_fix_messages(
                test_name      = tc_name,
                current_code   = current_codes[tc_name],
                instructions   = instructions,
                focal_method   = method_name,
                class_name     = class_name,
                ctx_d1         = ctx_d1,
                ctx_d3         = ctx_d3,
                imports        = imports,
                suite_summary  = refine_result.suite_summary,
                prev_unchanged = prev_unchanged,
                diag=tc_diag, 
            )

            fix_gen_path = os.path.join(fix_dir, "fix_gen.json")
            t0_fix = time.time()
            ok, fix_result = call_generator(gen_client, fix_msgs, fix_gen_path)
            t_fix = time.time() - t0_fix

            # ★ 记录 fix 的 Generator token
            tracker.record("generator", round_key, fix_result)
            print(f"  📊 [TokenLog] Recorded generator {round_key} fix: {fix_result.prompt_tokens}+{fix_result.completion_tokens} tokens", flush=True)

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

                    # diff 检测
                    changed = _code_changed(current_codes[tc_name], new_code)
                    if not changed:
                        unchanged_counts[tc_name] = unchanged_counts.get(tc_name, 0) + 1
                        fix_results["unchanged"].append(tc_name)
                        print(f"    ⚠️  {Fore.YELLOW}{tc_name} 输出与原始完全相同 "
                              f"(连续相同: {unchanged_counts[tc_name]} 次){Style.RESET_ALL}", flush=True)
                        with open(new_java_path, "w", encoding="utf-8") as f:
                            f.write(f"// [UNCHANGED] Output identical to input "
                                    f"(attempt {unchanged_counts[tc_name]})\n")
                            f.write(new_code)
                    else:
                        unchanged_counts[tc_name] = 0
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
                        f.write(f"// [EXTRACT_FAILED] LLM returned no valid Java code\n")
                    print(f"    ⚠️  {tc_name} 未提取到有效代码 ({t_fix:.1f}s)", flush=True)
            else:
                fix_results["fail"].append(tc_name)
                with open(new_java_path, "w", encoding="utf-8") as f:
                    f.write(f"// [LLM_ERROR] Generator call failed for {tc_name}\n")
                print(f"    ❌ {tc_name} LLM 调用失败 ({t_fix:.1f}s)", flush=True)

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

        # 若当前轮所有 fix 都未改变，说明 Refiner/Generator 处于僵局，记录并继续
        if fix_results["unchanged"] and not fix_results["ok"]:
            print(Fore.YELLOW +
                  f"  ⚠️  本轮所有精修输出均未发生变化，可能原因：\n"
                  f"     1. 诊断数据缺失（suite_diagnosis.json 为空）→ 检查 TestRunner 路径\n"
                  f"     2. Refiner 给出的指令过于模糊\n"
                  f"     3. Generator 模型能力限制\n"
                  f"  下一轮将加入 'prev_unchanged' 强化提示。" + Style.RESET_ALL, flush=True)

    # ── 保存统计 ──────────────────────────────────────────────────
    _save_stats(base_dir, tracker, time_stats, process_start)
    return tracker.to_dict()


def _save_stats(base_dir: str, tracker: LLMStatsTracker,
                time_stats: dict, process_start: float):
    """保存 token_stats.json 和 time_stats.json（与 HITS 字段对齐）。"""
    end_time = time.time()
    time_stats["wall_clock"]["end"]           = end_time
    time_stats["wall_clock"]["total_seconds"] = round(end_time - process_start, 2)

    # ★ token_stats.json：由 LLMStatsTracker 生成，字段与 HITS 完全一致
    token_stats = tracker.to_dict()

    # 额外追加一个 legacy-compatible 节点，方便旧脚本读取
    # （prompt/completion 字段名与 v3 相同，避免下游分析脚本报错）
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

    total_tok = token_stats["all_total"]["total_tokens"]
    llm_time  = token_stats["all_total"]["llm_elapsed_seconds"]
    wall_time = time_stats["wall_clock"]["total_seconds"]
    print(flush=True)
    _divider("═", color=Fore.BLUE)
    print(Fore.BLUE +
          f"  🏁 全部完成\n"
          f"     Wall-clock: {wall_time}s  |  "
          f"LLM time (纯API): {llm_time}s  |  "
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
    """将单个 focal method 的 token_stats 汇总到全局统计。"""
    for role in ("generator", "refiner"):
        for k in ("prompt_tokens", "completion_tokens", "total_tokens"):
            g.setdefault(role, {}).setdefault(k, 0)
            g[role][k] += s.get(role, {}).get(k, 0)
        g[role].setdefault("llm_elapsed_seconds", 0.0)
        g[role]["llm_elapsed_seconds"] += s.get(role, {}).get("llm_elapsed_seconds", 0.0)

    g.setdefault("all_total", {
        "prompt_tokens": 0, "completion_tokens": 0,
        "total_tokens": 0, "llm_elapsed_seconds": 0.0,
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


# ════════════════════════════════════════════════════════════════════
# 批量入口
# ════════════════════════════════════════════════════════════════════

def start_whole_process(
    source_dir: str,
    result_path: str,
    method_ids: Optional[List[str]] = None,
    multiprocess: bool = False,
):
    """
    扫描 source_dir（direction_1/）下所有 .json，
    对每个 focal method 调用 focal_method_pipeline。
    """
    global_start = time.time()
    global_stats: dict = {
        "generator": {"prompt_tokens": 0, "completion_tokens": 0,
                      "total_tokens": 0, "llm_elapsed_seconds": 0.0},
        "refiner":   {"prompt_tokens": 0, "completion_tokens": 0,
                      "total_tokens": 0, "llm_elapsed_seconds": 0.0},
        "all_total": {"prompt_tokens": 0, "completion_tokens": 0,
                      "total_tokens": 0, "llm_elapsed_seconds": 0.0},
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

    # ── 打印全局摘要 ──────────────────────────────────────────────
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
    print(f"ALL total_tokens  : {gt['total_tokens']}")
    print(f"ALL LLM time      : {gt['llm_elapsed_seconds']:.1f}s  (纯 API 调用，不含工具链)")
    print(f"avg tokens/task   : {round(gt['total_tokens']/total, 1) if total else 0}")
    print(f"Generator per task: {round(global_stats['generator']['total_tokens']/total, 1) if total else 0}")
    print(f"Refiner per task  : {round(global_stats['refiner']['total_tokens']/total, 1) if total else 0}")
    print("=======================" + Style.RESET_ALL)

    return global_stats