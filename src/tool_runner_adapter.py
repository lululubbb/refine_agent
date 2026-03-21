"""
tool_runner_adapter.py
======================
TestRunner 适配器：调用 TestRunner.start_all_test()，然后从已有输出文件
提取所有 Tool 1+2 的诊断数据，序列化为统一的 suite_diagnosis.json。

问题1根本原因修复（suite_diagnosis.json 数据错误）：
─────────────────────────────────────────────────────────────────
  每次 run_and_export() 前必须删除旧的 suite_diagnosis.json，
  防止 TestRunner 崩溃时读到上一轮残留的旧文件。

  另外 _load_status_csv 增加详细日志，方便排查 compile_status 来源。

问题2根本原因修复（tests_output_dir 定位错误）：
─────────────────────────────────────────────────────────────────
  TestRunner 分支1（test_cases/存在）→ 输出在 FOCAL_DIR 本身
  _resolve_tests_output_dir() 先检查 FOCAL_DIR，再回退到 project_dir/tests%T/
─────────────────────────────────────────────────────────────────
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
    1. ★ 先清除旧的 suite_diagnosis.json（防止读到过期数据）
    2. 调用 TestRunner.start_all_test()
    3. 定位输出目录（tests_output_dir）
    4. 从该目录提取 compile/exec/coverage 数据
    5. 写入 tests_output_dir/suite_diagnosis.json
    6. 返回 tests_output_dir（None = 失败）
    """
    focal_method_result_dir = os.path.abspath(focal_method_result_dir)

    # ★ 修复问题1：每次运行前清除旧的 suite_diagnosis.json，
    # 防止 TestRunner 崩溃时 load_suite_diagnosis() 读到上轮残留的旧数据，
    # 导致 compile_status='pass' 的假阳性"全部通过"。
    _clear_stale_diag(focal_method_result_dir, project_dir)

    try:
        from test_runner import TestRunner
        runner = TestRunner(
            test_path   = focal_method_result_dir,
            target_path = project_dir,
        )
        runner.start_all_test()
    except Exception as e:
        logger.warning("[ToolRunner] TestRunner failed: %s", e)
        # TestRunner 失败时，尝试从已写出的部分数据中恢复
        # （makedirs 修复后 per_test_status_map 在崩溃前可能已部分写出）

    # ★ 修复问题2：正确定位 tests_output_dir
    tests_output_dir = _resolve_tests_output_dir(focal_method_result_dir, project_dir)

    if not tests_output_dir:
        logger.warning("[ToolRunner] tests_output_dir not found (focal=%s, project=%s)",
                       focal_method_result_dir, project_dir)
        return None

    logger.info("[ToolRunner] tests_output_dir = %s", tests_output_dir)

    # 构建诊断数据
    diag_map = _build_diag_map(tests_output_dir)

    # 写出 suite_diagnosis.json
    out_path = os.path.join(tests_output_dir, DIAG_JSON_NAME)
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(diag_map, f, indent=2, ensure_ascii=False)
        logger.info("[ToolRunner] suite_diagnosis.json → %d tests: %s", len(diag_map), out_path)

        # 打印摘要，方便排查
        compile_fail = sum(1 for v in diag_map.values() if v.get("compile_status") == "fail")
        compile_pass = sum(1 for v in diag_map.values() if v.get("compile_status") == "pass")
        exec_fail    = sum(1 for v in diag_map.values() if v.get("exec_status") == "fail")
        exec_pass    = sum(1 for v in diag_map.values() if v.get("exec_status") == "pass")
        logger.info("[ToolRunner] diag summary: compile_pass=%d fail=%d | exec_pass=%d fail=%d",
                    compile_pass, compile_fail, exec_pass, exec_fail)
    except Exception as e:
        logger.warning("[ToolRunner] failed to write suite_diagnosis.json: %s", e)

    return tests_output_dir


def _clear_stale_diag(focal_method_result_dir: str, project_dir: str):
    """
    ★ 修复问题1：清除本轮运行前可能存在的旧 suite_diagnosis.json。
    同时清除 project_dir 下最新 tests%T%/ 里的旧文件（分支2兼容）。
    """
    candidates = [
        os.path.join(focal_method_result_dir, DIAG_JSON_NAME),
    ]
    # 也检查 project_dir 下最新的 tests%T%/
    latest = _find_latest_tests_dir(project_dir)
    if latest:
        candidates.append(os.path.join(latest, DIAG_JSON_NAME))

    for path in candidates:
        if os.path.exists(path):
            try:
                os.remove(path)
                logger.debug("[ToolRunner] cleared stale %s", path)
            except Exception as e:
                logger.debug("[ToolRunner] failed to clear %s: %s", path, e)


def _resolve_tests_output_dir(focal_method_result_dir: str,
                               project_dir: str) -> Optional[str]:
    """
    两步策略定位 tests_output_dir。

    分支1（本项目走这条，test_cases/存在）：
      TestRunner 把所有输出写在 focal_method_result_dir 本身。
      检测特征文件之一存在 → 返回 focal_method_result_dir。

    分支2（ChatUniTest 原始，test_cases/不存在）：
      TestRunner 在 project_dir 下新建 tests%T%/。
      → 返回最新的 tests%T%/ 目录。
    """
    # 分支1检测
    branch1_indicators = [
        os.path.join(focal_method_result_dir, "logs", "diagnosis.log"),
        os.path.join(focal_method_result_dir, "tests_ChatGPT"),
        os.path.join(focal_method_result_dir, "compiler_output"),
        os.path.join(focal_method_result_dir, "test_output"),
    ]
    for indicator in branch1_indicators:
        if os.path.exists(indicator):
            logger.debug("[ToolRunner] branch1 → tests_output_dir = FOCAL_DIR")
            return focal_method_result_dir

    # 分支2检测
    latest = _find_latest_tests_dir(project_dir)
    if latest:
        logger.debug("[ToolRunner] branch2 → tests_output_dir = %s", latest)
        return latest

    # 兜底：直接用 focal_method_result_dir（比返回 None 导致假阳性要好）
    logger.warning("[ToolRunner] no indicator found, fallback to focal_method_result_dir")
    return focal_method_result_dir


# ════════════════════════════════════════════════════════════════════
# 数据提取
# ════════════════════════════════════════════════════════════════════

def _build_diag_map(tests_output_dir: str) -> Dict[str, dict]:
    diag: Dict[str, dict] = {}
    _load_status_csv(tests_output_dir, diag)
    _load_diagnosis_log(tests_output_dir, diag)
    _load_coverage_csv(tests_output_dir, diag)
    logger.info("[ToolRunner] diag_map built: %d entries from %s", len(diag), tests_output_dir)
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


# ── *_status.csv ──────────────────────────────────────────────────

def _load_status_csv(tests_output_dir: str, diag: dict):
    search_dirs = [
        tests_output_dir,
        os.path.dirname(tests_output_dir),
    ]
    for d in search_dirs:
        if not os.path.isdir(d):
            continue
        csv_files = glob.glob(os.path.join(d, "*_status*.csv"))
        if csv_files:
            for csv_path in sorted(csv_files):
                logger.info("[ToolRunner] loading status csv: %s", csv_path)
                _parse_status_csv(csv_path, diag)
            return
    logger.warning("[ToolRunner] no *_status*.csv found under %s", tests_output_dir)


def _parse_status_csv(csv_path: str, diag: dict):
    try:
        rows_read = 0
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
                    entry["exec_status"] = "timeout" if (is_timeout and es == "fail") else es
                rows_read += 1
                logger.debug("[ToolRunner] status csv row: tc=%s compile=%s exec=%s", tc, cs, es)
        logger.info("[ToolRunner] status csv parsed: %d rows from %s", rows_read, csv_path)
    except Exception as e:
        logger.warning("status csv %s: %s", csv_path, e)


# ── diagnosis.log ─────────────────────────────────────────────────

def _load_diagnosis_log(tests_output_dir: str, diag: dict):
    candidates = [
        os.path.join(tests_output_dir, "logs", "diagnosis.log"),
        os.path.join(tests_output_dir, "diagnosis.log"),
        os.path.join(os.path.dirname(tests_output_dir), "logs", "diagnosis.log"),
    ]
    log_path = None
    for c in candidates:
        if os.path.exists(c) and os.path.getsize(c) > 0:
            log_path = c
            logger.debug("[ToolRunner] diagnosis.log found: %s", log_path)
            break

    if not log_path:
        logger.warning("[ToolRunner] diagnosis.log not found under %s", tests_output_dir)
        return

    logger.debug("[ToolRunner] loading diagnosis.log: %s", log_path)

    try:
        with open(log_path, encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception as e:
        logger.warning("diagnosis.log read error: %s", e)
        return

    raw_blocks = re.split(r'\[DIAGNOSIS\]', content)
    parsed = 0
    for block in raw_blocks[1:]:
        _parse_diag_block(block, diag)
        parsed += 1
    logger.info("[ToolRunner] parsed %d [DIAGNOSIS] blocks from %s", parsed, log_path)


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
            in_core_errors     = True
            in_missed_methods  = False
            in_partial_methods = False
            in_full_stderr     = False
            continue
        if re.match(r'full_stderr\s*\(', stripped):
            in_core_errors     = False
            in_full_stderr     = True
            in_missed_methods  = False
            in_partial_methods = False
            continue
        if re.match(r'(missed_methods|uncovered_methods):', stripped):
            in_core_errors     = False
            in_full_stderr     = False
            in_missed_methods  = True
            in_partial_methods = False
            continue
        if re.match(r'(partial_methods|partial_branch_methods):', stripped):
            in_core_errors     = False
            in_full_stderr     = False
            in_missed_methods  = False
            in_partial_methods = True
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


# ── *coveragedetail*.csv ─────────────────────────────────────────

def _load_coverage_csv(tests_output_dir: str, diag: dict):
    search_dirs = [
        tests_output_dir,
        os.path.dirname(tests_output_dir),
    ]
    for d in search_dirs:
        if not os.path.isdir(d):
            continue
        cov_files = sorted(glob.glob(os.path.join(d, "*coveragedetail*.csv")))
        if cov_files:
            logger.info("[ToolRunner] loading coveragedetail: %s", cov_files[-1])
            _parse_coverage_csv(cov_files[-1], diag)
            return
    logger.debug("[ToolRunner] no *coveragedetail*.csv found under %s", tests_output_dir)


def _parse_coverage_csv(csv_path: str, diag: dict):
    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                tc = _short(row.get("test_class", "").strip())
                if not tc:
                    continue
                entry = _ensure(diag, tc)
                for field, key in [("f_per_line_rate", "focal_line_rate"),
                                    ("f_per_branch_rate", "focal_branch_rate")]:
                    val = row.get(field, "").strip()
                    if val:
                        try:
                            entry[key] = round(float(val), 2)
                        except Exception:
                            pass
    except Exception as e:
        logger.warning("coveragedetail csv %s: %s", csv_path, e)


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
            data = json.load(f)
        logger.info("[ToolRunner] loaded suite_diagnosis.json: %d entries from %s",
                    len(data), path)
        return data
    except Exception as e:
        logger.warning("failed to load suite_diagnosis.json: %s", e)
        return {}


# ════════════════════════════════════════════════════════════════════
# 辅助
# ════════════════════════════════════════════════════════════════════

def _find_latest_tests_dir(project_dir: str) -> Optional[str]:
    try:
        candidates = [
            os.path.join(project_dir, d)
            for d in os.listdir(project_dir)
            if d.startswith("tests%") and os.path.isdir(os.path.join(project_dir, d))
        ]
        return max(candidates, key=os.path.getmtime) if candidates else None
    except Exception:
        return None