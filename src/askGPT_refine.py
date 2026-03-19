"""
askGPT_refine.py  (v3 — 概念修正版)
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
"""
from __future__ import annotations

import concurrent.futures
import copy
import json
import logging
import os
import sys
import time
from typing import Dict, List, Optional

from colorama import Fore, Style, init
from jinja2 import Environment, FileSystemLoader

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

init()
logger = logging.getLogger(__name__)

_PROMPT_DIR = os.path.join(os.path.dirname(HERE), "prompt")
env = Environment(loader=FileSystemLoader(_PROMPT_DIR))


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
) -> Optional[str]:
    """
    为 test_num=seq 生成一个 Test 文件（Token_1_{seq}Test.java）。
    返回生成的 Java 源码，或 None（失败时）。
    保存 LLM 原始输出到 gen_log_dir/{seq}/。
    """
    save_dir = os.path.join(gen_log_dir, str(seq))
    os.makedirs(save_dir, exist_ok=True)

    def _s(s): return _strip_pkg(s, imports, package)

    # 选模板（与 ChatUniTest 相同）
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
        return None

    gen_path = os.path.join(save_dir, "1_GEN.json")
    ok, gen_result = call_generator(gen_client, msgs, gen_path)
    if not ok:
        return None

    has_code, code, _ = extract_code(gen_result.content)
    if not has_code or not code.strip():
        return None

    if package:
        code = repair_package(code, f"package {package};")
    code = repair_imports(code, imports)

    # 写入 test_cases/ 目录，文件名 Token_1_{seq}Test.java
    tc_fname = f"{class_name}_{method_id}_{seq}Test.java"
    tc_path  = os.path.join(tc_dir, tc_fname)
    final_code = change_class_name(code, class_name, method_id, seq)
    if package:
        final_code = repair_package(final_code, f"package {package};")
    with open(tc_path, "w", encoding="utf-8") as f:
        f.write(final_code)

    # 保存快照
    snap_path = os.path.join(save_dir, "2_JAVA.java")
    with open(snap_path, "w", encoding="utf-8") as f:
        f.write(final_code)

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
    """
    为单个 Test 文件构建 fix prompt。
    传入该 Test 的具体修复指令列表。
    """
    context = {
        "class_name":      class_name,
        "focal_method":    focal_method,
        "test_name":       test_name,
        "current_suite":   current_code,   # 该 Test 文件的完整源码
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
    base_name: str,     # e.g. "1%Csv_1_b%Token%reset%d1.json"
    base_dir: str,      # e.g. "results_batch/.../1%Csv_1_b%Token%reset%d3"
    submits: int,
    total: int,
) -> dict:
    """
    针对一个 focal method 的完整 pipeline：
    1. 生成 test_number 个 Test 文件（Phase 1）
    2. max_rounds 轮 Refine Agent + per-Test 精修（Phase 2）

    与 ChatUniTest 的区别：
    - ChatUniTest: 每个 test_num 独立迭代（test_num × rounds 次 fix）
    - 本项目:     先批量生成所有 test_num 个文件，再整体 Refine（rounds 次 suite-level 评估）
    """
    process_start = time.time()
    progress_tag  = f"[{submits}/{total}]"

    method_id, proj_name, class_name, method_name = parse_file_name(base_name)

    # ── 目录 ─────────────────────────────────────────────────────
    tc_dir      = os.path.join(base_dir, "test_cases")   # ★ TestRunner 读取此处
    gen_log_dir = os.path.join(base_dir, "gen_logs")      # 初始生成记录
    ref_log_dir = os.path.join(base_dir, "refine_logs")   # Refine 迭代记录
    for d in [tc_dir, gen_log_dir, ref_log_dir]:
        os.makedirs(d, exist_ok=True)

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
    print(Fore.CYAN + f"{progress_tag} {method_id} [Phase 1] Generating {test_number} Test files" + Style.RESET_ALL)

    # current_codes: {test_name → java_source}（当前各 Test 文件的源码）
    current_codes: Dict[str, str] = {}

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
        )
        if result is None:
            logger.warning("%s test_%d generation failed", progress_tag, seq)
            continue

        code, gen_result = result
        current_codes[tc_name] = code
        _acc_gen(token_stats, gen_result)
        print(Fore.GREEN + f"{progress_tag} {method_id} test_{seq} generated" + Style.RESET_ALL)

    if not current_codes:
        logger.error("%s all generations failed", progress_tag)
        return token_stats

    time_stats["rounds"]["phase1"] = round(time.time() - phase1_start, 2)
    print(Fore.GREEN + f"{progress_tag} {method_id} [Phase 1] done: {len(current_codes)}/{test_number} Test files" + Style.RESET_ALL)

    # ════════════════════════════════════════════════════════════════
    # Phase 2: 迭代 Refine（固定 max_rounds 轮）
    # ════════════════════════════════════════════════════════════════
    for r in range(1, max_rounds + 1):
        round_start = time.time()
        round_log_dir = os.path.join(ref_log_dir, f"round_{r}")
        os.makedirs(round_log_dir, exist_ok=True)

        print(Fore.YELLOW + f"{progress_tag} {method_id} [Round {r}/{max_rounds}] Refine Agent on Suite ({len(current_codes)} Tests)" + Style.RESET_ALL)

        # ── Refine Agent：对整个 Suite 评估 ──────────────────────
        refine_result: RefineResult = agent.run(
            focal_method_result_dir = base_dir,
            project_dir             = buggy_dir,
            focal_method            = method_name,
            class_name              = class_name,
            target_class_fqn        = f"{package}.{class_name}" if package else class_name,
            focal_method_code       = focal_method_code,
            test_file_codes         = current_codes,    # 所有当前 Test 文件的源码
            iteration               = r,
            save_dir                = round_log_dir,
            step_counter_start      = 1,
        )

        _acc_ref(token_stats, refine_result)
        print(
            Fore.MAGENTA +
            f"{progress_tag} {method_id} [Round {r}] "
            f"SuiteScore: compile={refine_result.suite_score.compile_pass_rate:.0%} "
            f"exec={refine_result.suite_score.exec_pass_rate:.0%} "
            f"cov_avg={refine_result.suite_score.coverage_line_avg or 0:.1%} | "
            f"Refiner: instructions={len(refine_result.instructions)} Tests | "
            f"delete={refine_result.delete_tests}"
            + Style.RESET_ALL
        )

        if not refine_result.has_actionable_instructions():
            print(Fore.GREEN + f"{progress_tag} {method_id} [Round {r}] no instructions → early stop" + Style.RESET_ALL)
            time_stats["rounds"][f"round_{r}"] = round(time.time() - round_start, 2)
            break

        # ── 删除高冗余 Test 文件 ───────────────────────────────────
        for del_tc in refine_result.delete_tests:
            current_codes.pop(del_tc, None)
            tc_path = os.path.join(tc_dir, f"{del_tc}.java")
            if os.path.exists(tc_path):
                os.remove(tc_path)
                logger.info("[Round %d] deleted Test: %s", r, del_tc)

        # ── 针对性精修：只修复有指令的 Test 文件 ─────────────────
        for tc_name, instructions in refine_result.instructions.items():
            if tc_name not in current_codes:
                continue

            fix_dir = os.path.join(round_log_dir, f"fix_{tc_name}")
            os.makedirs(fix_dir, exist_ok=True)

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
            ok, fix_result = call_generator(gen_client, fix_msgs, fix_gen_path)
            _acc_gen(token_stats, fix_result)

            if ok:
                has_code, new_code, _ = extract_code(fix_result.content)
                if has_code and new_code.strip():
                    if package:
                        new_code = repair_package(new_code, f"package {package};")
                    new_code = repair_imports(new_code, imports)
                    # 确保类名正确
                    seq_num  = int(tc_name.split("_")[-1].replace("Test", ""))
                    new_code = change_class_name(new_code, class_name, method_id, seq_num)
                    if package:
                        new_code = repair_package(new_code, f"package {package};")
                    current_codes[tc_name] = new_code

                    # 更新 test_cases/ 中的文件
                    tc_path = os.path.join(tc_dir, f"{tc_name}.java")
                    with open(tc_path, "w", encoding="utf-8") as f:
                        f.write(new_code)

                    # 保存快照
                    with open(os.path.join(fix_dir, "new.java"), "w", encoding="utf-8") as f:
                        f.write(new_code)

                    print(Fore.GREEN + f"{progress_tag} {method_id} [Round {r}] fixed {tc_name}" + Style.RESET_ALL)
                else:
                    logger.warning("[Round %d] no valid code extracted for %s", r, tc_name)
            else:
                logger.warning("[Round %d] Generator fix failed for %s", r, tc_name)

        time_stats["rounds"][f"round_{r}"] = round(time.time() - round_start, 2)
        print(Fore.GREEN + f"{progress_tag} {method_id} [Round {r}] done" + Style.RESET_ALL)

    # ── 保存统计 ──────────────────────────────────────────────────
    time_stats["end"]   = time.time()
    time_stats["total"] = round(time_stats["end"] - process_start, 2)
    with open(os.path.join(base_dir, "time_stats.json"),  "w", encoding="utf-8") as f:
        json.dump(time_stats,  f, indent=2, ensure_ascii=False)
    with open(os.path.join(base_dir, "token_stats.json"), "w", encoding="utf-8") as f:
        json.dump(token_stats, f, indent=2, ensure_ascii=False)

    total_tok = token_stats["generator"]["total"] + token_stats["refiner"]["total"]
    print(
        Fore.BLUE +
        f"{progress_tag} {method_id} DONE | {time_stats['total']}s | "
        f"gen={token_stats['generator']['total']} | "
        f"ref={token_stats['refiner']['total']} | all={total_tok}"
        + Style.RESET_ALL
    )
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
    对每个 focal method 调用 focal_method_pipeline（不再按 test_num 分任务）。

    每个 focal method 是一个独立任务，内部自行生成 test_number 个 Test。
    """
    global_start = time.time()
    global_stats = {
        "generator": {"prompt": 0, "completion": 0, "total": 0},
        "refiner":   {"prompt": 0, "completion": 0, "total": 0},
    }

    # 收集 focal method JSON 文件
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

    submits = 0
    total   = len(file_paths)    # ★ 每个 focal method = 1 个任务（不乘以 test_number）
    tasks   = []

    for fp in file_paths:
        _, base_name = os.path.split(fp)
        base_name_result = base_name.replace(".json", "").replace("%d1", "%d3")
        base_dir = os.path.join(result_path, base_name_result)
        os.makedirs(os.path.join(base_dir, "test_cases"), exist_ok=True)
        submits += 1
        tasks.append((base_name, base_dir, submits, total))

    if multiprocess:
        print("Multi-process executing!")
        with concurrent.futures.ProcessPoolExecutor(max_workers=process_number) as executor:
            futures = {executor.submit(focal_method_pipeline, *t): t for t in tasks}
            for fut in concurrent.futures.as_completed(futures):
                try:
                    stats = fut.result()
                    _acc_global(global_stats, stats)
                except Exception as e:
                    logger.error("Worker error: %s", e)
    else:
        print("Single-process executing!")
        for t in tasks:
            stats = focal_method_pipeline(*t)
            _acc_global(global_stats, stats)

    elapsed = round(time.time() - global_start, 2)
    global_stats["elapsed_seconds"] = elapsed
    global_stats["total_focal_methods"] = total
    with open(os.path.join(result_path, "global_stats.json"), "w", encoding="utf-8") as f:
        json.dump(global_stats, f, indent=2, ensure_ascii=False)

    print(Fore.MAGENTA + f"\n=== Global Stats  elapsed={elapsed}s  focal_methods={total} ===")
    print(f"Generator tokens: {global_stats['generator']['total']}")
    print(f"Refiner   tokens: {global_stats['refiner']['total']}")
    print("=" * 50 + Style.RESET_ALL)


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
