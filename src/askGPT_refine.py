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
 
"""
from __future__ import annotations

import concurrent.futures
import copy
import json
import logging
import os
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
)
from jinja2 import Environment, FileSystemLoader

init()
logger = logging.getLogger(__name__)

_PROMPT_DIR = os.path.join(os.path.dirname(HERE), "prompt")
env = Environment(loader=FileSystemLoader(_PROMPT_DIR))


# ════════════════════════════════════════════════════════════════════
# 进度打印工具
# ════════════════════════════════════════════════════════════════════

def _divider(char="─", width=72, color=Fore.WHITE):
    print(color + char * width + Style.RESET_ALL, flush=True)


def _section(title: str, color=Fore.CYAN):
    w = 72
    pad = (w - len(title) - 4) // 2
    print(color + "┌" + "─" * (w - 2) + "┐" + Style.RESET_ALL, flush=True)
    print(color + "│" + " " * pad + f"  {title}  " + " " * (w - 2 - pad - len(title) - 4) + "│" + Style.RESET_ALL, flush=True)
    print(color + "└" + "─" * (w - 2) + "┘" + Style.RESET_ALL, flush=True)


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _progress_bar(current: int, total: int, width: int = 20) -> str:
    filled = int(width * current / total) if total > 0 else 0
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {current}/{total}"


def _print_suite_score(suite_score, tag=""):
    """打印 Suite 整体评分，高亮问题维度。"""
    ss = suite_score
    print(flush=True)
    _divider("·", color=Fore.YELLOW)
    print(Fore.YELLOW + f"  📊 Suite Score{' '+tag if tag else ''}" + Style.RESET_ALL, flush=True)
    _divider("·", color=Fore.YELLOW)

    # 编译率
    cr = ss.compile_pass_rate
    cr_color = Fore.GREEN if cr >= 0.8 else (Fore.YELLOW if cr >= 0.5 else Fore.RED)
    print(f"  {'编译通过率':<16}: {cr_color}{ss.compile_pass_count}/{ss.n_tests} ({cr*100:.0f}%){Style.RESET_ALL}", flush=True)

    # 执行率
    er = ss.exec_pass_rate
    er_color = Fore.GREEN if er >= 0.8 else (Fore.YELLOW if er >= 0.5 else Fore.RED)
    print(f"  {'执行通过率':<16}: {er_color}{ss.exec_pass_count}/{ss.n_tests} ({er*100:.0f}%){Style.RESET_ALL}", flush=True)

    # 行覆盖率
    if ss.coverage_line_avg is not None:
        lc = ss.coverage_line_avg
        lc_color = Fore.GREEN if lc >= 0.7 else (Fore.YELLOW if lc >= 0.4 else Fore.RED)
        print(f"  {'行覆盖率(avg)':<16}: {lc_color}{lc*100:.1f}%  (min={ss.coverage_line_min*100:.1f}%  max={ss.coverage_line_max*100:.1f}%){Style.RESET_ALL}", flush=True)
    else:
        print(f"  {'行覆盖率(avg)':<16}: {Fore.WHITE}N/A{Style.RESET_ALL}", flush=True)

    # 分支覆盖率
    if ss.coverage_branch_avg is not None:
        bc = ss.coverage_branch_avg
        bc_color = Fore.GREEN if bc >= 0.7 else (Fore.YELLOW if bc >= 0.4 else Fore.RED)
        print(f"  {'分支覆盖率(avg)':<16}: {bc_color}{bc*100:.1f}%{Style.RESET_ALL}", flush=True)
    else:
        print(f"  {'分支覆盖率(avg)':<16}: {Fore.WHITE}N/A{Style.RESET_ALL}", flush=True)

    # Bug Revealing
    if ss.bug_reveal_checked > 0:
        br = ss.bug_reveal_rate
        br_color = Fore.GREEN if br >= 0.5 else (Fore.YELLOW if br > 0 else Fore.RED)
        print(f"  {'Bug揭示率':<16}: {br_color}{ss.bug_reveal_count}/{ss.bug_reveal_checked} ({br*100:.0f}%){Style.RESET_ALL}", flush=True)
    else:
        print(f"  {'Bug揭示率':<16}: {Fore.WHITE}未检测{Style.RESET_ALL}", flush=True)

    # 相似度
    if ss.max_pairwise_similarity is not None:
        sim = ss.max_pairwise_similarity
        sim_color = Fore.RED if sim > 0.9 else (Fore.YELLOW if sim > 0.7 else Fore.GREEN)
        print(f"  {'最大用例相似度':<16}: {sim_color}{sim:.3f}{Style.RESET_ALL}", flush=True)
    else:
        print(f"  {'最大用例相似度':<16}: {Fore.WHITE}N/A{Style.RESET_ALL}", flush=True)

    # 问题汇总
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
                tc_list = ss.problem_tests[iss]
                c = issue_colors.get(iss, Fore.WHITE)
                print(f"    {c}[{iss}]{Style.RESET_ALL} → {', '.join(tc_list)}", flush=True)
    else:
        print(f"\n  ✅ 无问题！Suite 全部通过质量检查。", flush=True)

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

    print(f"\n  🔍 {Fore.WHITE}{tc_name}{Style.RESET_ALL}  问题: "
          + "  ".join([f"{issue_colors.get(i, Fore.WHITE)}[{i}]{Style.RESET_ALL}" for i in issues]),
          flush=True)

    # 编译错误
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
                        suite_summary: str):
    """将 refine 质量数据追加到 refine_quality.jsonl，供离线分析。"""
    log_path = os.path.join(save_dir, "..", "refine_quality.jsonl")
    log_path = os.path.normpath(log_path)
    entry = {
        "ts": _ts(),
        "focal_method": focal_method,
        "round": round_num,
        "suite_summary": suite_summary,
        "suite_score": suite_score.to_dict() if suite_score else {},
        "test_issues": {
            name: s.issues for name, s in test_scores.items()
        },
        "instructions_count": len(instructions),
        "tests_with_instructions": list(instructions.keys()),
    }
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.debug("refine_quality.jsonl write error: %s", e)


# ════════════════════════════════════════════════════════════════════
# Prompt 工具（与 ChatUniTest 相同）
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

def call_generator(
    gen_client: LLMClient,
    messages: List[Dict],
    save_path: str,
) -> tuple[bool, LLMCallResult]:
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
    """
    为 test_num=seq 生成一个 Test 文件（Token_1_{seq}Test.java）。
    返回 (java_source, gen_result) 或 None（失败时）。
    """
    save_dir = os.path.join(gen_log_dir, str(seq))
    os.makedirs(save_dir, exist_ok=True)

    def _s(s): return _strip_pkg(s, imports, package)

    tc_name = f"{class_name}_{method_id}_{seq}Test"
    print(f"\n  ⚙️  [{_ts()}] {progress_tag} 生成 Test #{seq}: {tc_name} ...", flush=True)

    # 选模板
    if not ctx_d3.get("c_deps") and not ctx_d3.get("m_deps"):
        ctx = copy.deepcopy(ctx_d1)
        msgs = generate_messages(TEMPLATE_NO_DEPS, ctx)
        if remain_prompt_tokens(msgs) < 0:
            ctx["information"] = _s(ctx["information"])
            msgs = generate_messages(TEMPLATE_NO_DEPS, ctx)
    else:
        ctx = copy.deepcopy(ctx_d3)
        msgs = generate_messages(TEMPLATE_WITH_DEPS, ctx)
        if remain_prompt_tokens(msgs) < 0:
            ctx["full_fm"] = _s(ctx.get("full_fm", ""))
            msgs = generate_messages(TEMPLATE_WITH_DEPS, ctx)

    if not msgs:
        print(f"    ❌ 无法构建 prompt，跳过", flush=True)
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

    if package:
        code = repair_package(code, f"package {package};")
    code = repair_imports(code, imports)

    tc_fname = f"{class_name}_{method_id}_{seq}Test.java"
    tc_path  = os.path.join(tc_dir, tc_fname)
    final_code = change_class_name(code, class_name, method_id, seq)
    if package:
        final_code = repair_package(final_code, f"package {package};")
    with open(tc_path, "w", encoding="utf-8") as f:
        f.write(final_code)

    snap_path = os.path.join(save_dir, "2_JAVA.java")
    with open(snap_path, "w", encoding="utf-8") as f:
        f.write(final_code)

    syntax_warn = " ⚠️ (语法修复)" if has_err else ""
    print(f"    ✅ 生成成功{syntax_warn} | "
          f"tokens={gen_result.prompt_tokens}+{gen_result.completion_tokens} | "
          f"{elapsed:.1f}s | 写入 {tc_fname}",
          flush=True)
    return final_code, gen_result


# ════════════════════════════════════════════════════════════════════
# Fix 单个 Test 文件（根据 Refiner 指令）
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
) -> List[Dict]:
    context = {
        "class_name":      class_name,
        "focal_method":    focal_method,
        "test_name":       test_name,
        "current_suite":   current_code,
        "suite_summary":   suite_summary,
        "instructions_json": json.dumps(instructions, indent=2, ensure_ascii=False),
        "delete_tests_json": "[]",
        "method_code":     ctx_d1.get("information", ctx_d3.get("full_fm", "")),
        "imports":         imports,
    }
    msgs = generate_messages(TEMPLATE_FIX, context)
    if remain_prompt_tokens(msgs) < 0:
        context["method_code"] = ctx_d3.get("full_fm", "")
        msgs = generate_messages(TEMPLATE_FIX, context)
    return msgs


# ════════════════════════════════════════════════════════════════════
# 主流程：针对一个 focal method 的完整 pipeline
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
    token_stats = {
        "generator": {"prompt": 0, "completion": 0, "total": 0},
        "refiner":   {"prompt": 0, "completion": 0, "total": 0},
        "rounds":    {},
    }
    time_stats = {"start": process_start, "end": 0, "total": 0, "rounds": {}}

    # ── 加载数据集 ────────────────────────────────────────────────
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

    # ── 构建 LLM 客户端 ───────────────────────────────────────────
    gen_client = make_generator_client()
    ref_client = make_refiner_client()

    proj_base = os.path.dirname(os.path.abspath(project_dir))
    buggy_dir = os.path.abspath(project_dir)
    fixed_dir_candidate = os.path.join(
        proj_base, proj_name.replace("_b", "_f").replace("_B", "_F")
    )
    fixed_dir = fixed_dir_candidate if os.path.isdir(fixed_dir_candidate) else None

    agent = RefineAgent(
        refiner_client    = ref_client,
        template_dir      = _PROMPT_DIR,
        buggy_dir         = buggy_dir,
        fixed_dir         = fixed_dir,
        skip_bug_revealing= (fixed_dir is None),
    )

    # ════════════════════════════════════════════════════════════════
    # Phase 1: 批量生成所有 test_number 个 Test 文件
    # ════════════════════════════════════════════════════════════════
    phase1_start = time.time()
    print(flush=True)
    _divider("═", color=Fore.GREEN)
    print(Fore.GREEN + f"  ▶ Phase 1: 初始生成 {test_number} 个 Test 文件" + Style.RESET_ALL, flush=True)
    _divider("═", color=Fore.GREEN)

    current_codes: Dict[str, str] = {}
    gen_failures = []

    for seq in range(1, test_number + 1):
        tc_name = f"{class_name}_{method_id}_{seq}Test"
        result = generate_one_test(
            seq        = seq,
            gen_client = gen_client,
            ctx_d1     = ctx_d1,
            ctx_d3     = ctx_d3,
            imports    = imports,
            package    = package,
            class_name = class_name,
            method_id  = method_id,
            tc_dir     = tc_dir,
            gen_log_dir= gen_log_dir,
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

    success_n = len(current_codes)
    fail_n    = len(gen_failures)
    bar = _progress_bar(success_n, test_number)
    status_color = Fore.GREEN if fail_n == 0 else (Fore.YELLOW if success_n > 0 else Fore.RED)
    print(flush=True)
    print(status_color +
          f"  ✔ Phase 1 完成 {bar}  失败: {fail_n}  耗时: {phase1_elapsed:.1f}s"
          + Style.RESET_ALL, flush=True)

    if not current_codes:
        print(f"  {Fore.RED}❌ 全部 Test 生成失败，跳过此 focal method{Style.RESET_ALL}", flush=True)
        logger.error("%s all generations failed", progress_tag)
        return token_stats

    # ════════════════════════════════════════════════════════════════
    # Phase 2: 迭代 Refine（固定 max_rounds 轮）
    # ════════════════════════════════════════════════════════════════
    for r in range(1, max_rounds + 1):
        round_start = time.time()
        round_log_dir = os.path.join(ref_log_dir, f"round_{r}")
        os.makedirs(round_log_dir, exist_ok=True)

        print(flush=True)
        _divider("═", color=Fore.MAGENTA)
        print(Fore.MAGENTA +
              f"  ▶ Phase 2 Round {r}/{max_rounds}: Refine Agent "
              f"({len(current_codes)} Tests)" + Style.RESET_ALL, flush=True)
        _divider("═", color=Fore.MAGENTA)

        # ── Refine Agent ──────────────────────────────────────────
        print(f"  [{_ts()}] 运行工具链 (编译/执行/覆盖率/相似度) ...", flush=True)
        t0_agent = time.time()
        refine_result: RefineResult = agent.run(
            focal_method_result_dir = base_dir,
            project_dir             = buggy_dir,
            focal_method            = method_name,
            class_name              = class_name,
            target_class_fqn        = f"{package}.{class_name}" if package else class_name,
            focal_method_code       = focal_method_code,
            test_file_codes         = current_codes,
            iteration               = r,
            save_dir                = round_log_dir,
            step_counter_start      = 1,
        )
        t_agent = time.time() - t0_agent
        print(f"  [{_ts()}] 工具链完成  耗时: {t_agent:.1f}s", flush=True)

        _acc_ref(token_stats, refine_result)

        # ── 打印 Suite Score ──────────────────────────────────────
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

        # ── 记录质量日志 ──────────────────────────────────────────
        _log_refine_quality(
            save_dir      = round_log_dir,
            focal_method  = f"{class_name}.{method_name}",
            round_num     = r,
            suite_score   = refine_result.suite_score,
            test_scores   = refine_result.test_scores,
            instructions  = refine_result.instructions,
            suite_summary = refine_result.suite_summary,
        )

        # ── Early Stop ────────────────────────────────────────────
        if not refine_result.has_actionable_instructions():
            print(flush=True)
            print(Fore.GREEN +
                  f"  🎉 Round {r}: 无修复指令，Suite 质量达标，提前结束 Refine"
                  + Style.RESET_ALL, flush=True)
            time_stats["rounds"][f"round_{r}"] = round(time.time() - round_start, 2)
            break

        # ── 打印修复指令预览 ──────────────────────────────────────
        _print_refine_instructions(refine_result.instructions, refine_result.delete_tests)

        # ── 删除高冗余 Test ───────────────────────────────────────
        for del_tc in refine_result.delete_tests:
            current_codes.pop(del_tc, None)
            tc_path = os.path.join(tc_dir, f"{del_tc}.java")
            if os.path.exists(tc_path):
                os.remove(tc_path)
                print(f"  🗑  已删除冗余 Test: {Fore.CYAN}{del_tc}{Style.RESET_ALL}", flush=True)

        # ── Fix 每个有指令的 Test ─────────────────────────────────
        fix_results = {"ok": [], "fail": [], "no_code": []}
        print(flush=True)
        print(f"  🔧 开始精修 {len(refine_result.instructions)} 个 Test 文件 ...", flush=True)

        for tc_name, instructions in refine_result.instructions.items():
            if tc_name not in current_codes:
                continue

            fix_dir = os.path.join(round_log_dir, f"fix_{tc_name}")
            os.makedirs(fix_dir, exist_ok=True)

            print(f"\n    [{_ts()}] 精修 {Fore.WHITE}{tc_name}{Style.RESET_ALL} "
                  f"({len(instructions)} 条指令) ...", flush=True)

            fix_msgs = build_fix_messages(
                test_name    = tc_name,
                current_code = current_codes[tc_name],
                instructions = instructions,
                focal_method = method_name,
                class_name   = class_name,
                ctx_d1       = ctx_d1,
                ctx_d3       = ctx_d3,
                imports      = imports,
                suite_summary= refine_result.suite_summary,
            )

            fix_gen_path = os.path.join(fix_dir, "fix_gen.json")
            t0_fix = time.time()
            ok, fix_result = call_generator(gen_client, fix_msgs, fix_gen_path)
            t_fix = time.time() - t0_fix
            _acc_gen(token_stats, fix_result)

            if ok:
                has_code, new_code, _ = extract_code(fix_result.content)
                if has_code and new_code.strip():
                    if package:
                        new_code = repair_package(new_code, f"package {package};")
                    new_code = repair_imports(new_code, imports)
                    seq_num  = int(tc_name.split("_")[-1].replace("Test", ""))
                    new_code = change_class_name(new_code, class_name, method_id, seq_num)
                    if package:
                        new_code = repair_package(new_code, f"package {package};")
                    current_codes[tc_name] = new_code

                    tc_path = os.path.join(tc_dir, f"{tc_name}.java")
                    with open(tc_path, "w", encoding="utf-8") as f:
                        f.write(new_code)
                    with open(os.path.join(fix_dir, "new.java"), "w", encoding="utf-8") as f:
                        f.write(new_code)

                    fix_results["ok"].append(tc_name)
                    print(f"    ✅ {tc_name} 精修成功 | "
                          f"tokens={fix_result.prompt_tokens}+{fix_result.completion_tokens} | "
                          f"{t_fix:.1f}s",
                          flush=True)
                else:
                    fix_results["no_code"].append(tc_name)
                    print(f"    ⚠️  {tc_name} LLM 响应中未提取到有效代码 ({t_fix:.1f}s)", flush=True)
                    logger.warning("[Round %d] no valid code extracted for %s", r, tc_name)
            else:
                fix_results["fail"].append(tc_name)
                print(f"    ❌ {tc_name} LLM 调用失败 ({t_fix:.1f}s)", flush=True)
                logger.warning("[Round %d] Generator fix failed for %s", r, tc_name)

        round_elapsed = time.time() - round_start
        time_stats["rounds"][f"round_{r}"] = round(round_elapsed, 2)

        # ── Round 小结 ────────────────────────────────────────────
        print(flush=True)
        print(Fore.MAGENTA +
              f"  ✔ Round {r} 完成 | 耗时 {round_elapsed:.1f}s | "
              f"精修成功: {len(fix_results['ok'])}  "
              f"无代码: {len(fix_results['no_code'])}  "
              f"失败: {len(fix_results['fail'])}"
              + Style.RESET_ALL, flush=True)

    # ── 保存统计 ──────────────────────────────────────────────────
    time_stats["end"]   = time.time()
    time_stats["total"] = round(time_stats["end"] - process_start, 2)
    with open(os.path.join(base_dir, "time_stats.json"),  "w", encoding="utf-8") as f:
        json.dump(time_stats,  f, indent=2, ensure_ascii=False)
    with open(os.path.join(base_dir, "token_stats.json"), "w", encoding="utf-8") as f:
        json.dump(token_stats, f, indent=2, ensure_ascii=False)

    total_tok = token_stats["generator"]["total"] + token_stats["refiner"]["total"]
    print(flush=True)
    _divider("═", color=Fore.BLUE)
    print(Fore.BLUE +
          f"  🏁 {progress_tag} {class_name}.{method_name} 全部完成\n"
          f"     总耗时: {time_stats['total']}s  |  "
          f"Generator tokens: {token_stats['generator']['total']}  |  "
          f"Refiner tokens: {token_stats['refiner']['total']}  |  "
          f"合计: {total_tok}"
          + Style.RESET_ALL, flush=True)
    _divider("═", color=Fore.BLUE)

    return token_stats


# ════════════════════════════════════════════════════════════════════
# 批量入口（与 ChatUniTest start_whole_process 兼容）
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
    global_stats = {
        "generator": {"prompt": 0, "completion": 0, "total": 0},
        "refiner":   {"prompt": 0, "completion": 0, "total": 0},
    }

    # 收集文件
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

    total   = len(file_paths)
    submits = 0
    tasks   = []

    print(flush=True)
    _section(f"RefineTestGen  共 {total} 个 focal method", Fore.CYAN)
    if method_ids:
        print(f"  筛选 method IDs: {method_ids}", flush=True)
    print(flush=True)

    for fp in file_paths:
        _, base_name = os.path.split(fp)
        base_name_result = base_name.replace(".json", "").replace("%d1", "%d3")
        base_dir = os.path.join(result_path, base_name_result)
        os.makedirs(os.path.join(base_dir, "test_cases"), exist_ok=True)
        submits += 1
        tasks.append((base_name, base_dir, submits, total))

    if multiprocess:
        print("  🔀 多进程模式 (workers={process_number})", flush=True)
        with concurrent.futures.ProcessPoolExecutor(max_workers=process_number) as executor:
            futures = {executor.submit(focal_method_pipeline, *t): t for t in tasks}
            for fut in concurrent.futures.as_completed(futures):
                try:
                    stats = fut.result()
                    _acc_global(global_stats, stats)
                except Exception as e:
                    logger.error("Worker error: %s", e)
    else:
        print("  📋 单进程顺序执行", flush=True)
        for t in tasks:
            stats = focal_method_pipeline(*t)
            _acc_global(global_stats, stats)

    elapsed = round(time.time() - global_start, 2)
    global_stats["elapsed_seconds"] = elapsed
    global_stats["total_focal_methods"] = total

    with open(os.path.join(result_path, "global_stats.json"), "w", encoding="utf-8") as f:
        json.dump(global_stats, f, indent=2, ensure_ascii=False)

    print(flush=True)
    _section("全局统计", Fore.MAGENTA)
    print(Fore.MAGENTA + f"  focal methods 处理: {total}  总耗时: {elapsed}s" + Style.RESET_ALL, flush=True)
    print(Fore.MAGENTA + f"  Generator tokens:   {global_stats['generator']['total']}" + Style.RESET_ALL, flush=True)
    print(Fore.MAGENTA + f"  Refiner tokens:     {global_stats['refiner']['total']}" + Style.RESET_ALL, flush=True)
    print(flush=True)


# ════════════════════════════════════════════════════════════════════
# 辅助函数
# ════════════════════════════════════════════════════════════════════

def _acc_gen(stats: dict, r: LLMCallResult):
    stats["generator"]["prompt"]     += r.prompt_tokens
    stats["generator"]["completion"] += r.completion_tokens
    stats["generator"]["total"]      += r.total_tokens


def _acc_ref(stats: dict, r: RefineResult):
    stats["refiner"]["prompt"]     += r.refiner_prompt_tokens
    stats["refiner"]["completion"] += r.refiner_completion_tokens
    stats["refiner"]["total"]      += r.refiner_prompt_tokens + r.refiner_completion_tokens


def _acc_global(g: dict, s: dict):
    for role in ("generator", "refiner"):
        for k in ("prompt", "completion", "total"):
            g[role][k] += s.get(role, {}).get(k, 0)