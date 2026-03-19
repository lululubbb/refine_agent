"""
tool_runner_adapter.py
======================
TestRunner 适配器：调用 TestRunner.start_all_test()，然后从已有输出文件
提取所有 Tool 1+2 的诊断数据，序列化为统一的 suite_diagnosis.json。

改进点（对比直接读文件的旧方式）：
─────────────────────────────────────────────────────────────────
旧方式问题                      新方式解决
─────────────────────────────────────────────────────────────────
regex 解析自定义 .log 格式      → JSON 标准格式，json.load() 一次搞定
coveragedetail.csv 路径错误     → 在 tests_output_dir 内直接找正确路径
missed_methods 逐行格式匹配失败 → 从 diagnosis.log 用 block 方式正确解析
5 段独立解析逻辑                → 1 个统一 JSON 出口
─────────────────────────────────────────────────────────────────

输出文件：tests_output_dir/suite_diagnosis.json
格式：
{
  "Token_1_1Test": {
    "compile_status":      "pass" | "fail",
    "exec_status":         "pass" | "fail" | "timeout" | "skip",
    "compile_errors":      ["Token_1_1Test.java:12: error: cannot find symbol"],
    "exec_errors":         ["org.opentest4j.AssertionFailedError: expected:<1> but was:<0>"],
    "focal_line_rate":     45.0,     # 0~100，null 如未测量
    "focal_branch_rate":   33.3,     # 0~100，null 如未测量
    "missed_methods":      ["reset", "close"],
    "partial_methods":     ["read"]
  },
  ...
}
"""
from __future__ import annotations

import csv
import glob
import json
import logging
import os
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

DIAG_JSON_NAME = "suite_diagnosis.json"


# ════════════════════════════════════════════════════════════════════
# 主入口
# ════════════════════════════════════════════════════════════════════

def run_and_export(
    focal_method_result_dir: str,
    project_dir: str,
) -> Optional[str]:
    """
    1. 调用 TestRunner.start_all_test()
    2. 找到输出目录（兼容分支A/B两种路径）
    3. 从 status.csv + diagnosis.log + coveragedetail.csv 提取数据
    4. 写入 tests_output_dir/suite_diagnosis.json
    5. 返回 tests_output_dir 路径（None = 失败）

    Bug Fix:
      旧版 _find_latest_tests_dir 只找 project_dir/tests%T/（分支B输出），
      当 TestRunner 走分支A（in-place）时永远找不到。
      修复后同时检查 focal_method_result_dir 本身（分支A）和 project_dir/tests%T/（分支B）。
    """
    tests_output_dir = None
    try:
        from test_runner import TestRunner
        runner = TestRunner(
            test_path   = focal_method_result_dir,
            target_path = project_dir,
        )
        runner.start_all_test()
    except Exception as e:
        logger.warning("[ToolRunner] TestRunner failed: %s", e)
        # TestRunner 抛异常通常是因为某个文件写入失败（目录权限/路径问题）
        # 但测试可能已经部分运行，仍尝试找输出目录
        logger.info("[ToolRunner] Attempting to find partial output...")

    # ★ 修复：兼容两种输出路径
    tests_output_dir = _find_tests_output_dir(focal_method_result_dir, project_dir)

    if not tests_output_dir:
        logger.warning(
            "[ToolRunner] tests output dir not found.\n"
            "  Checked: %s/logs/  and  %s/tests%%*/\n"
            "  This usually means TestRunner crashed before writing any output.",
            focal_method_result_dir, project_dir
        )
        # 最后兜底：用 focal_method_result_dir 本身（哪怕 diagnosis.log 为空）
        tests_output_dir = focal_method_result_dir

    # 构建诊断 dict
    diag_map = _build_diag_map(tests_output_dir, focal_method_result_dir)

    # 写入 JSON
    out_path = os.path.join(tests_output_dir, DIAG_JSON_NAME)
    try:
        os.makedirs(tests_output_dir, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(diag_map, f, indent=2, ensure_ascii=False)
        logger.info("[ToolRunner] suite_diagnosis.json written: %s (%d tests)",
                    out_path, len(diag_map))
    except Exception as e:
        logger.warning("[ToolRunner] failed to write JSON: %s", e)

    return tests_output_dir


# ════════════════════════════════════════════════════════════════════
# 输出目录查找（兼容分支A/B）
# ════════════════════════════════════════════════════════════════════

def _find_tests_output_dir(focal_method_result_dir: str, project_dir: str) -> Optional[str]:
    """
    查找 TestRunner 实际写入输出的目录，兼容两种分支：

    分支A（in-place）：
      focal_method_result_dir/logs/diagnosis.log 存在
      → 返回 focal_method_result_dir

    分支B（copy-to-defect4j）：
      project_dir/tests%YYYYMMDDHHMMSS/ 存在且有 logs/diagnosis.log
      → 返回最新的 tests%T/ 目录
    """
    # 检查分支A：diagnosis.log 在 focal_method_result_dir/logs/ 下
    diag_a = os.path.join(focal_method_result_dir, "logs", "diagnosis.log")
    if os.path.exists(diag_a):
        logger.info("[ToolRunner] Found in-place output (branch A): %s", focal_method_result_dir)
        return focal_method_result_dir

    # 检查分支A 备用：status.csv 在 focal_method_result_dir 下
    status_files_a = glob.glob(os.path.join(focal_method_result_dir, "*_status*.csv"))
    if status_files_a:
        logger.info("[ToolRunner] Found status CSV in focal dir (branch A): %s", focal_method_result_dir)
        return focal_method_result_dir

    # 检查分支B：project_dir/tests%T/
    b_dir = _find_latest_tests_dir_in_project(project_dir)
    if b_dir:
        logger.info("[ToolRunner] Found tests%T dir (branch B): %s", b_dir)
        return b_dir

    return None


def _find_latest_tests_dir_in_project(project_dir: str) -> Optional[str]:
    """在 project_dir 下找最新的 tests%YYYYMMDDHHMMSS/ 目录（分支B输出）。"""
    try:
        candidates = [
            os.path.join(project_dir, d)
            for d in os.listdir(project_dir)
            if d.startswith("tests%") and os.path.isdir(os.path.join(project_dir, d))
        ]
        return max(candidates, key=os.path.getmtime) if candidates else None
    except Exception:
        return None


# ════════════════════════════════════════════════════════════════════
# 数据提取
# ════════════════════════════════════════════════════════════════════

def _build_diag_map(
    tests_output_dir: str,
    focal_method_result_dir: str = None,
) -> Dict[str, dict]:
    """
    从 tests_output_dir 和（可选的）focal_method_result_dir 提取诊断数据。
    当两者不同时（分支B），logs/ 在 tests_output_dir，coveragedetail.csv 也在那里。
    当两者相同时（分支A），所有文件都在 focal_method_result_dir 下。
    """
    diag: Dict[str, dict] = {}

    # 候选搜索目录（去重）
    search_dirs = list({tests_output_dir, focal_method_result_dir} - {None})

    _load_status_csv_multi(search_dirs, diag)
    _load_diagnosis_log_multi(search_dirs, diag)
    _load_coverage_csv_multi(search_dirs, diag)

    return diag


def _short(full_name: str) -> str:
    return full_name.rsplit(".", 1)[-1]


def _ensure(diag: dict, tc: str) -> dict:
    if tc not in diag:
        diag[tc] = {
            "compile_status":    "unknown",
            "exec_status":       "unknown",
            "compile_errors":    [],
            "exec_errors":       [],
            "focal_line_rate":   None,
            "focal_branch_rate": None,
            "missed_methods":    [],
            "partial_methods":   [],
        }
    return diag[tc]


# ── Step 1: *_status.csv ─────────────────────────────────────────────

def _load_status_csv_multi(search_dirs: list, diag: dict):
    for d in search_dirs:
        csv_files = glob.glob(os.path.join(d, "*_status*.csv"))
        for csv_path in sorted(csv_files):
            _parse_status_csv(csv_path, diag)


def _parse_status_csv(csv_path: str, diag: dict):
    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                tc = _short(row.get("test_class", "").strip())
                if not tc:
                    continue
                entry = _ensure(diag, tc)
                cs = row.get("compile_status", "").lower().strip()
                es = row.get("exec_status",    "").lower().strip()
                if cs:
                    entry["compile_status"] = cs
                if es and es != "pending":
                    is_timeout = str(row.get("exec_timeout", "false")).lower() in ("true", "1")
                    if is_timeout and es == "fail":
                        entry["exec_status"] = "timeout"
                    else:
                        entry["exec_status"] = es
    except Exception as e:
        logger.debug("status csv %s: %s", csv_path, e)


# ── Step 2: diagnosis.log ─────────────────────────────────────────────

def _load_diagnosis_log_multi(search_dirs: list, diag: dict):
    for d in search_dirs:
        # 分支A：logs/ 在 focal_method_result_dir/logs/
        log_a = os.path.join(d, "logs", "diagnosis.log")
        if os.path.exists(log_a) and os.path.getsize(log_a) > 100:
            _load_diagnosis_log(log_a, diag)
            return
        # 分支B：logs/ 在 tests%T/logs/
        log_b = os.path.join(d, "logs", "diagnosis.log")
        if os.path.exists(log_b) and os.path.getsize(log_b) > 100:
            _load_diagnosis_log(log_b, diag)
            return

    # 都没找到，打印提示
    logger.warning(
        "[ToolRunner] diagnosis.log not found or empty in any of: %s\n"
        "  Hint: TestRunner may have crashed during compilation. "
        "Check logs/compile.log for details.",
        search_dirs
    )


def _load_diagnosis_log(log_path: str, diag: dict):
    try:
        with open(log_path, encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception as e:
        logger.debug("diagnosis.log read error: %s", e)
        return

    raw_blocks = re.split(r'\[DIAGNOSIS\]', content)
    for block in raw_blocks[1:]:
        _parse_diag_block(block, diag)

    logger.info("[ToolRunner] Parsed %d blocks from diagnosis.log", len(raw_blocks) - 1)


def _parse_diag_block(block: str, diag: dict):
    lines = block.splitlines()
    if not lines:
        return

    tc_match = re.match(r'\s*test_class=(.+)', lines[0])
    if not tc_match:
        return
    tc = _short(tc_match.group(1).strip())
    entry = _ensure(diag, tc)

    in_core_errors     = False
    in_missed_methods  = False
    in_partial_methods = False
    in_full_stderr     = False

    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "---":
            break

        sm = re.match(r'status=(\S+)', stripped)
        if sm:
            status = sm.group(1)
            entry["compile_status"] = "pass"
            entry["exec_status"]    = "pass"
            if status == "compile_fail":
                entry["compile_status"] = "fail"
                entry["exec_status"]    = "skip"
            elif status == "exec_fail":
                entry["exec_status"] = "fail"
            elif status == "exec_timeout":
                entry["exec_status"] = "timeout"
            in_core_errors = in_missed_methods = in_partial_methods = in_full_stderr = False
            continue

        if re.match(r'core_errors\s*\(?\d*\)?:', stripped):
            in_core_errors = True; in_missed_methods = in_partial_methods = in_full_stderr = False
            continue
        if re.match(r'full_stderr\s*\(', stripped):
            in_full_stderr = True; in_core_errors = in_missed_methods = in_partial_methods = False
            continue
        if re.match(r'(missed_methods|uncovered_methods):', stripped):
            in_missed_methods = True; in_core_errors = in_full_stderr = in_partial_methods = False
            continue
        if re.match(r'(partial_methods|partial_branch_methods):', stripped):
            in_partial_methods = True; in_core_errors = in_full_stderr = in_missed_methods = False
            continue

        item_m = re.match(r'-\s+(.+)', stripped)
        if item_m:
            val = item_m.group(1).strip()
            if in_core_errors and not in_full_stderr:
                if entry["compile_status"] == "fail":
                    entry["compile_errors"].append(val)
                else:
                    entry["exec_errors"].append(val)
            elif in_missed_methods:
                entry["missed_methods"].append(val)
            elif in_partial_methods:
                entry["partial_methods"].append(val)
            continue

        if in_full_stderr:
            continue
        if stripped and not stripped.startswith("-"):
            in_core_errors = in_missed_methods = in_partial_methods = False

    entry["compile_errors"] = list(dict.fromkeys(entry["compile_errors"]))[:8]
    entry["exec_errors"]    = list(dict.fromkeys(entry["exec_errors"]))[:8]
    entry["missed_methods"] = list(dict.fromkeys(entry["missed_methods"]))
    entry["partial_methods"]= list(dict.fromkeys(entry["partial_methods"]))


# ── Step 3: coveragedetail.csv ────────────────────────────────────────

def _load_coverage_csv_multi(search_dirs: list, diag: dict):
    for d in search_dirs:
        cov_files = sorted(glob.glob(os.path.join(d, "*coveragedetail*.csv")))
        if cov_files:
            _parse_coverage_csv(cov_files[-1], diag)
            return
        # 也检查父目录（分支B 把 csv 写在 project_dir 下）
        parent = os.path.dirname(d)
        cov_files_p = sorted(glob.glob(os.path.join(parent, "*coveragedetail*.csv")))
        if cov_files_p:
            _parse_coverage_csv(cov_files_p[-1], diag)
            return


def _parse_coverage_csv(csv_path: str, diag: dict):
    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                tc = _short(row.get("test_class", "").strip())
                if not tc:
                    continue
                entry = _ensure(diag, tc)
                lr = row.get("f_per_line_rate", "").strip()
                br = row.get("f_per_branch_rate", "").strip()
                if lr:
                    try:
                        entry["focal_line_rate"] = round(float(lr), 2)
                    except Exception:
                        pass
                if br:
                    try:
                        entry["focal_branch_rate"] = round(float(br), 2)
                    except Exception:
                        pass
    except Exception as e:
        logger.debug("coveragedetail csv %s: %s", csv_path, e)


# ════════════════════════════════════════════════════════════════════
# 读取 suite_diagnosis.json
# ════════════════════════════════════════════════════════════════════

def load_suite_diagnosis(tests_output_dir: str) -> Dict[str, dict]:
    path = os.path.join(tests_output_dir, DIAG_JSON_NAME)
    if not os.path.exists(path):
        logger.warning("suite_diagnosis.json not found: %s", path)
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("failed to load suite_diagnosis.json: %s", e)
        return {}