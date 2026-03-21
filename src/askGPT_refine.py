"""
askGPT_refine.py  (v3 — 概念修正版 + 进度日志增强版)
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
        lc_c = Fore.GREEN if lc >= 0.7 else (Fore.YELLOW if lc >= 0.4 else Fore.RED)
        print(f"  {'行覆盖率(avg)':<16}: {lc_c}{lc*100:.1f}%  "
              f"(min={ss.coverage_line_min*100:.1f}%  max={ss.coverage_line_max*100:.1f}%){Style.RESET_ALL}", flush=True)
    else:
        print(f"  {'行覆盖率(avg)':<16}: {Fore.WHITE}N/A{Style.RESET_ALL}", flush=True)

    if ss.coverage_branch_avg is not None:
        bc = ss.coverage_branch_avg
        bc_c = Fore.GREEN if bc >= 0.7 else (Fore.YELLOW if bc >= 0.4 else Fore.RED)
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
        sim_c = Fore.RED if sim > 0.9 else (Fore.YELLOW if sim > 0.7 else Fore.GREEN)
        print(f"  {'最大用例相似度':<16}: {sim_c}{sim:.3f}{Style.RESET_ALL}", flush=True)
    else:
        print(f"  {'最大用例相似度':<16}: {Fore.RED}N/A (相似度计算失败，检查 Tool 4 日志){Style.RESET_ALL}", flush=True)

    if ss.problem_tests:
        print(f"\n  ⚠️  问题分布：", flush=True)
        issue_order = ["COMPILE_FAIL", "EXEC_FAIL", "EXEC_TIMEOUT",
                       "LOW_LINE_COV", "LOW_BRANCH_COV", "NOT_BUG_REVEALING", "HIGH_REDUNDANCY"]
        issue_colors = {
            "COMPILE_FAIL":       Fore.RED,
            "EXEC_FAIL":          Fore.RED,
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
        print(f"  {Fore.WHITE}  质量标准: 编译通过 + 执行无异常 + 行覆盖率≥50%"
              f" + 分支覆盖率≥50% + 无高冗余(≤70%){Style.RESET_ALL}", flush=True)
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
        "COMPILE_FAIL": Fore.RED, "EXEC_FAIL": Fore.RED, "EXEC_TIMEOUT": Fore.RED,
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
        print(f"    {Fore.RED}编译错误 (前3条):{Style.RESET_ALL}", flush=True)
        for e in diag.compile_errors[:3]:
            print(f"      • {e}", flush=True)

    # 执行错误
    if ("EXEC_FAIL" in issues or "EXEC_TIMEOUT" in issues) and diag.exec_errors:
        print(f"    {Fore.RED}运行错误 (前3条):{Style.RESET_ALL}", flush=True)
        for e in diag.exec_errors[:3]:
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
# ★ Bug 1 & Bug 1b 修复：Token 统计工具函数
# ════════════════════════════════════════════════════════════════════

def _make_token_stats() -> dict:
    """
    ★ Bug 1b 修复：创建包含 all_total 和 rounds 字段的初始统计字典。
    统一由此函数创建，避免遗漏字段。
    """
    return {
        "generator": {"prompt": 0, "completion": 0, "total": 0},
        "refiner":   {"prompt": 0, "completion": 0, "total": 0},
        "all_total": 0,   # ★ Bug 1b：generator.total + refiner.total 的合计
        "rounds":    {},  # ★ Bug 1：按 phase1 / round_1 / round_2 ... 分别记录增量
    }


def _acc_round_tokens(stats: dict, round_key: str,
                      gen_prompt: int, gen_completion: int,
                      ref_prompt: int, ref_completion: int):
    """
    ★ Bug 1 修复核心：将本阶段（phase1 / round_N）的 token 增量写入 stats["rounds"]。

    调用方式：
      1. 在 phase1 结束后，传入 phase1 期间所有 Generator 调用的累计增量。
      2. 在每个 round_N 结束后，传入该轮 Generator + Refiner 的累计增量。

    增量计算方法（调用方负责）：
      在阶段开始前快照当前累计值，阶段结束后相减，得到本阶段增量。
    """
    gen_total = gen_prompt + gen_completion
    ref_total = ref_prompt + ref_completion
    stats["rounds"][round_key] = {
        "generator": {
            "prompt":     gen_prompt,
            "completion": gen_completion,
            "total":      gen_total,
        },
        "refiner": {
            "prompt":     ref_prompt,
            "completion": ref_completion,
            "total":      ref_total,
        },
        "round_total": gen_total + ref_total,
    }


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

def call_generator(gen_client: LLMClient, messages: List[Dict], save_path: str) -> tuple[bool, LLMCallResult]:
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
        return None

    has_code, code, has_err = extract_code(gen_result.content)
    if not has_code or not code.strip():
        print(f"    ❌ 未提取到有效 Java 代码 ({elapsed:.1f}s)", flush=True)
        return None

    # ★ 用规范化后的 pkg_decl 修正 package 声明
    if pkg_decl:
        code = repair_package(code, pkg_decl)

    # 修正 imports（repair_imports 内部已过滤 package 行）
    code = repair_imports(code, imports)

    # 确保 package 仍在最前（repair_imports 可能把 import 插到 package 之前了）
    if pkg_decl:
        code = _ensure_package_first(code, pkg_decl)

    # 更换类名
    final_code = change_class_name(code, class_name, method_id, seq)
    if pkg_decl:
        final_code = repair_package(final_code, pkg_decl)
        final_code = _ensure_package_first(final_code, pkg_decl)

    # 写入 test_cases/
    tc_fname = f"{class_name}_{method_id}_{seq}Test.java"
    tc_path  = os.path.join(tc_dir, tc_fname)
    with open(tc_path, "w", encoding="utf-8") as f:
        f.write(final_code)
    with open(os.path.join(save_dir, "2_JAVA.java"), "w", encoding="utf-8") as f:
        f.write(final_code)

    print(f"    ✅ 生成成功{'⚠️(语法修复)' if has_err else ''} | "
          f"tokens={gen_result.prompt_tokens}+{gen_result.completion_tokens} | "
          f"{elapsed:.1f}s | {tc_fname}", flush=True)
    return final_code, gen_result


def _ensure_package_first(code: str, pkg_decl: str) -> str:
    """确保 package 声明是 Java 文件最前面的有效语句。"""
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
# Fix 单个 Test（含 diff 检测 + 强化 prompt）
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
) -> List[Dict]:
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

    return msgs


# ════════════════════════════════════════════════════════════════════
# 主流程
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

    # ── Token / 时间统计 ───────────────────────────────────────────
    # ★ Bug 1 & 1b 修复：使用工厂函数创建，包含 all_total 和 rounds 字段
    token_stats = _make_token_stats()
    time_stats  = {"start": process_start, "end": 0, "total": 0, "rounds": {}}

    try:
        with open(get_dataset_path(method_id, proj_name, class_name, method_name, "raw")) as f:
            raw_data = json.load(f)
        with open(get_dataset_path(method_id, proj_name, class_name, method_name, "1")) as f:
            ctx_d1 = json.load(f)
        with open(get_dataset_path(method_id, proj_name, class_name, method_name, "3")) as f:
            ctx_d3 = json.load(f)
    except FileNotFoundError as e:
        print(f"  {Fore.RED}❌ 数据集文件不存在: {e}{Style.RESET_ALL}", flush=True)
        logger.error("%s dataset not found: %s", progress_tag, e)
        return token_stats

    package           = raw_data.get("package", "")
    imports           = raw_data.get("imports", "")
    focal_method_code = raw_data.get("source_code", ctx_d1.get("information", ""))
    pkg_decl          = canonical_package_decl(package)

    print(f"  package raw: {repr(package[:60])}  →  pkg_decl: {repr(pkg_decl)}", flush=True)

    gen_client = make_generator_client()
    ref_client = make_refiner_client()

    proj_base = os.path.dirname(os.path.abspath(project_dir))
    buggy_dir = os.path.abspath(project_dir)
    
    # ★ 修复问题3：尝试多个候选路径找 fixed_dir
    # 候选1：同级目录，_b → _f
    fixed_dir_candidate1 = os.path.join(
        proj_base, proj_name.replace("_b", "_f").replace("_B", "_F")
    )
    # 候选2：proj_name 本身可能已经是 _f（不含 _b）
    fixed_dir_candidate2 = os.path.join(
        proj_base, os.path.basename(os.path.abspath(project_dir)).replace("_b", "_f")
    )
    # 候选3：在 project_dir 的父目录下找任何含 _f 的同名项目
    _proj_base_name = re.sub(r'_b$', '', proj_name, flags=re.IGNORECASE)
    fixed_dir_candidate3 = os.path.join(proj_base, f"{_proj_base_name}_f")
    
    fixed_dir = None
    for cand in [fixed_dir_candidate1, fixed_dir_candidate2, fixed_dir_candidate3]:
        if os.path.isdir(cand):
            fixed_dir = cand
            print(f"  {Fore.GREEN}✅ found fixed_dir: {cand}{Style.RESET_ALL}", flush=True)
            break
    
    if fixed_dir is None:
        print(f"  {Fore.RED}⚠ fixed_dir not found, bug_revealing will be skipped.\\n"
              f"    Tried: {fixed_dir_candidate1}\\n"
              f"    Tried: {fixed_dir_candidate2}\\n"
              f"    Tried: {fixed_dir_candidate3}{Style.RESET_ALL}", flush=True)

    agent = RefineAgent(
        refiner_client     = ref_client,
        template_dir       = _PROMPT_DIR,
        buggy_dir          = buggy_dir,
        fixed_dir          = fixed_dir,
        skip_bug_revealing = (fixed_dir is None),
    )

    # ════════════════════════════════════════════════════════════════
    # Phase 1: 批量生成所有 test_number 个 Test 文件
    # ════════════════════════════════════════════════════════════════
    phase1_start = time.time()
    _divider("═", color=Fore.GREEN)
    print(Fore.GREEN + f"  ▶ Phase 1: 初始生成 {test_number} 个 Test 文件" + Style.RESET_ALL, flush=True)
    _divider("═", color=Fore.GREEN)

    current_codes: Dict[str, str] = {}
    gen_failures = []

    # ★ Bug 1 修复：快照 phase1 开始前的 generator token 基线
    gen_snap_prompt_phase1     = token_stats["generator"]["prompt"]
    gen_snap_completion_phase1 = token_stats["generator"]["completion"]

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
        current_codes[tc_name] = code
        _acc_gen(token_stats, gen_result)

    phase1_elapsed = time.time() - phase1_start
    time_stats["rounds"]["phase1"] = round(phase1_elapsed, 2)

    # ★ Bug 1 修复：phase1 结束，写入本阶段 token 增量到 rounds["phase1"]
    _acc_round_tokens(
        token_stats, "phase1",
        token_stats["generator"]["prompt"]     - gen_snap_prompt_phase1,
        token_stats["generator"]["completion"] - gen_snap_completion_phase1,
        0, 0,  # phase1 无 refiner 调用
    )

    success_n, fail_n = len(current_codes), len(gen_failures)
    sc = Fore.GREEN if fail_n == 0 else (Fore.YELLOW if success_n > 0 else Fore.RED)
    print(sc + f"\n  ✔ Phase 1 完成 {_progress_bar(success_n, test_number)}  "
          f"失败: {fail_n}  耗时: {phase1_elapsed:.1f}s" + Style.RESET_ALL, flush=True)

    if not current_codes:
        print(f"  {Fore.RED}❌ 全部 Test 生成失败{Style.RESET_ALL}", flush=True)
        return token_stats

    # ════════════════════════════════════════════════════════════════
    # Phase 2: 迭代 Refine
    # ════════════════════════════════════════════════
    # 记录每个 tc 的 unchanged 次数（用于 prev_unchanged 提示）
    unchanged_counts: Dict[str, int] = {tc: 0 for tc in current_codes}

    for r in range(1, max_rounds + 1):
        round_start   = time.time()
        round_key     = f"round_{r}"
        round_log_dir = os.path.join(ref_log_dir, round_key)
        os.makedirs(round_log_dir, exist_ok=True)

        # ★ Bug 1 修复：快照本轮开始前的 token 值，用于计算本轮增量
        gen_snap_prompt     = token_stats["generator"]["prompt"]
        gen_snap_completion = token_stats["generator"]["completion"]
        ref_snap_prompt     = token_stats["refiner"]["prompt"]
        ref_snap_completion = token_stats["refiner"]["completion"]

        print(flush=True)
        _divider("═", color=Fore.MAGENTA)
        print(Fore.MAGENTA +
              f"  ▶ Phase 2 Round {r}/{max_rounds}: Refine Agent ({len(current_codes)} Tests)"
              + Style.RESET_ALL, flush=True)
        _divider("═", color=Fore.MAGENTA)

        # ── Refine Agent ──────────────────────────────────────────
        print(f"  [{_ts()}] 运行工具链 (编译/执行/覆盖率/相似度) ...", flush=True)
        t0_agent = time.time()
        refine_result: RefineResult = agent.run(
            focal_method_result_dir = base_dir,
            project_dir             = buggy_dir,
            focal_method            = method_name,
            class_name              = class_name,
            target_class_fqn        = f"{pkg_decl.replace('package ','').replace(';','')}.{class_name}" if pkg_decl else class_name,
            focal_method_code       = focal_method_code,
            test_file_codes         = current_codes,
            iteration               = r,
            save_dir                = round_log_dir,
            step_counter_start      = 1,
        )
        print(f"  [{_ts()}] 工具链完成  耗时: {time.time() - t0_agent:.1f}s", flush=True)

        _acc_ref(token_stats, refine_result)  # ★ Bug 1b：_acc_ref 内同步更新 all_total

        if refine_result.suite_score:
            _print_suite_score(refine_result.suite_score, tag=f"Round {r}")

        # ── 打印每个问题 Test 的详细诊断 ──────────────────────────
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

        # ── 打印 Suite Summary ────────────────────────────────────
        if refine_result.suite_summary:
            print(f"\n  💬 Refiner 总体评价:", flush=True)
            # 多行缩进打印
            for line in refine_result.suite_summary.splitlines():
                print(f"     {line}", flush=True)

        if not refine_result.has_actionable_instructions():
            print(Fore.GREEN + f"\n  🎉 Round {r}: 无修复指令，提前结束" + Style.RESET_ALL, flush=True)
            time_stats["rounds"][round_key] = round(time.time() - round_start, 2)
            # ★ Bug 1 修复：early stop 也记录本轮 token 增量（主要是 refiner）
            _acc_round_tokens(
                token_stats, round_key,
                token_stats["generator"]["prompt"]     - gen_snap_prompt,
                token_stats["generator"]["completion"] - gen_snap_completion,
                token_stats["refiner"]["prompt"]       - ref_snap_prompt,
                token_stats["refiner"]["completion"]   - ref_snap_completion,
            )
            _log_refine_quality(round_log_dir, f"{class_name}.{method_name}", r,
                                refine_result.suite_score, refine_result.test_scores,
                                refine_result.instructions, refine_result.suite_summary)
            break

        # ── 打印修复指令预览 ──────────────────────────────────────
        _print_refine_instructions(refine_result.instructions, refine_result.delete_tests)

        # ── 删除高冗余 Test ───────────────────────────────────────
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

            # ★ Bug 3 修复：fix 子目录结构与旧版保持一致
            fix_dir = os.path.join(round_log_dir, f"fix_{tc_name}")
            os.makedirs(fix_dir, exist_ok=True)

            prev_unchanged = unchanged_counts.get(tc_name, 0) > 0
            print(f"\n    [{_ts()}] 精修 {Fore.WHITE}{tc_name}{Style.RESET_ALL} "
                  f"({len(instructions)} 条指令)"
                  + (f" {Fore.YELLOW}[上轮未改变，加强提示]{Style.RESET_ALL}" if prev_unchanged else ""),
                  flush=True)

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
            )

            # ★ Bug 3 修复：明确路径 fix_dir/fix_gen.json，call_generator 写出
            fix_gen_path = os.path.join(fix_dir, "fix_gen.json")
            t0_fix = time.time()
            ok, fix_result = call_generator(gen_client, fix_msgs, fix_gen_path)
            t_fix = time.time() - t0_fix
            _acc_gen(token_stats, fix_result)  # ★ Bug 1b：同步更新 all_total

            # ★ Bug 3 修复：new.java 在所有路径都明确写出（成功/提取失败/LLM失败）
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
                        print(f"    ⚠️  {Fore.YELLOW}{tc_name} 输出与原始完全相同，未更新文件 "
                              f"(连续相同: {unchanged_counts[tc_name]} 次){Style.RESET_ALL}",
                              flush=True)
                        # ★ Bug 3 修复：未改变时仍写出 new.java（带注释说明）
                        with open(new_java_path, "w", encoding="utf-8") as f:
                            f.write(f"// [UNCHANGED] Output identical to input (attempt {unchanged_counts[tc_name]})\n")
                            f.write(new_code)
                    else:
                        unchanged_counts[tc_name] = 0
                        current_codes[tc_name] = new_code
                        tc_path = os.path.join(tc_dir, f"{tc_name}.java")
                        with open(tc_path, "w", encoding="utf-8") as f:
                            f.write(new_code)
                        # ★ Bug 3 修复：成功时写出 new.java
                        with open(new_java_path, "w", encoding="utf-8") as f:
                            f.write(new_code)
                        fix_results["ok"].append(tc_name)
                        print(f"    ✅ {tc_name} 精修成功 | "
                              f"tokens={fix_result.prompt_tokens}+{fix_result.completion_tokens} | "
                              f"{t_fix:.1f}s", flush=True)
                else:
                    fix_results["no_code"].append(tc_name)
                    # ★ Bug 3 修复：未提取到代码时写出占位 new.java
                    with open(new_java_path, "w", encoding="utf-8") as f:
                        f.write(f"// [EXTRACT_FAILED] LLM returned no valid Java code\n"
                                f"// raw content ({len(fix_result.content)} chars):\n"
                                f"// {fix_result.content[:300].replace(chr(10), ' ')}\n")
                    print(f"    ⚠️  {tc_name} 未提取到有效代码 ({t_fix:.1f}s)", flush=True)
            else:
                fix_results["fail"].append(tc_name)
                # ★ Bug 3 修复：LLM 调用失败时写出占位 new.java
                with open(new_java_path, "w", encoding="utf-8") as f:
                    f.write(f"// [LLM_ERROR] Generator call failed for {tc_name}\n")
                print(f"    ❌ {tc_name} LLM 调用失败 ({t_fix:.1f}s)", flush=True)

        round_elapsed = time.time() - round_start
        time_stats["rounds"][round_key] = round(round_elapsed, 2)

        # ★ Bug 1 修复：round_N 结束，写入本轮实际消耗的 token 增量
        _acc_round_tokens(
            token_stats, round_key,
            token_stats["generator"]["prompt"]     - gen_snap_prompt,
            token_stats["generator"]["completion"] - gen_snap_completion,
            token_stats["refiner"]["prompt"]       - ref_snap_prompt,
            token_stats["refiner"]["completion"]   - ref_snap_completion,
        )

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
    time_stats["end"]   = time.time()
    time_stats["total"] = round(time_stats["end"] - process_start, 2)

    # ★ Bug 1b 修复：最终确保 all_total 正确（防止浮点累加误差）
    token_stats["all_total"] = (
        token_stats["generator"]["total"] + token_stats["refiner"]["total"]
    )

    with open(os.path.join(base_dir, "time_stats.json"),  "w", encoding="utf-8") as f:
        json.dump(time_stats,  f, indent=2, ensure_ascii=False)
    with open(os.path.join(base_dir, "token_stats.json"), "w", encoding="utf-8") as f:
        json.dump(token_stats, f, indent=2, ensure_ascii=False)

    total_tok = token_stats["all_total"]
    print(flush=True)
    _divider("═", color=Fore.BLUE)
    print(Fore.BLUE +
          f"  🏁 {progress_tag} {class_name}.{method_name} 全部完成\n"
          f"     总耗时: {time_stats['total']}s  |  "
          f"Generator: {token_stats['generator']['total']}  |  "
          f"Refiner: {token_stats['refiner']['total']}  |  "
          f"合计(all_total): {total_tok}"
          + Style.RESET_ALL, flush=True)
    _divider("═", color=Fore.BLUE)
    return token_stats


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
    # ★ Bug 1b 修复：全局统计也含 all_total
    global_stats = _make_token_stats()

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
    global_stats["elapsed_seconds"]     = elapsed
    global_stats["total_focal_methods"] = total
    # ★ Bug 1b 修复：全局 all_total 最终值
    global_stats["all_total"] = (
        global_stats["generator"]["total"] + global_stats["refiner"]["total"]
    )

    with open(os.path.join(result_path, "global_stats.json"), "w", encoding="utf-8") as f:
        json.dump(global_stats, f, indent=2, ensure_ascii=False)

    print(flush=True)
    _section("全局统计", Fore.MAGENTA)
    print(Fore.MAGENTA + f"  focal methods : {total}  总耗时: {elapsed}s" + Style.RESET_ALL, flush=True)
    print(Fore.MAGENTA + f"  Generator     : {global_stats['generator']['total']} tokens" + Style.RESET_ALL, flush=True)
    print(Fore.MAGENTA + f"  Refiner       : {global_stats['refiner']['total']} tokens"   + Style.RESET_ALL, flush=True)
    print(Fore.MAGENTA + f"  All total     : {global_stats['all_total']} tokens"           + Style.RESET_ALL, flush=True)


# ════════════════════════════════════════════════════════════════════
# 辅助累加函数
# ════════════════════════════════════════════════════════════════════

def _acc_gen(stats: dict, r: LLMCallResult):
    """
    ★ Bug 1b 修复：累加 Generator token，并同步更新 all_total。
    """
    stats["generator"]["prompt"]     += r.prompt_tokens
    stats["generator"]["completion"] += r.completion_tokens
    stats["generator"]["total"]      += r.total_tokens
    stats["all_total"] = stats["generator"]["total"] + stats["refiner"]["total"]


def _acc_ref(stats: dict, r: RefineResult):
    """
    ★ Bug 1b 修复：累加 Refiner token，并同步更新 all_total。
    """
    stats["refiner"]["prompt"]     += r.refiner_prompt_tokens
    stats["refiner"]["completion"] += r.refiner_completion_tokens
    stats["refiner"]["total"]      += (r.refiner_prompt_tokens
                                       + r.refiner_completion_tokens)
    stats["all_total"] = stats["generator"]["total"] + stats["refiner"]["total"]


def _acc_global(g: dict, s: dict):
    for role in ("generator", "refiner"):
        for k in ("prompt", "completion", "total"):
            g[role][k] += s.get(role, {}).get(k, 0)
    g["all_total"] = g["generator"]["total"] + g["refiner"]["total"]