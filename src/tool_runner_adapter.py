"""
tool_runner_adapter.py
======================
TestRunner 适配器：调用 TestRunner.start_all_test()，然后从已有输出文件
提取所有 Tool 1+2 的诊断数据，序列化为统一的 suite_diagnosis.json。
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

# 状态优先级（数字越大，优先级越高）
_STATUS_PRIORITY = {
    "compile_fail": 3,
    "exec_timeout": 2,
    "exec_fail":    1,
    "exec_ok":      0,
    "unknown":      -1,
}


def _status_priority(status_str: str) -> int:
    return _STATUS_PRIORITY.get(status_str, -1)


# ════════════════════════════════════════════════════════════════════
# 主入口
# ════════════════════════════════════════════════════════════════════

def run_and_export(
    focal_method_result_dir: str,
    project_dir: str,
) -> Optional[str]:
    focal_method_result_dir = os.path.abspath(focal_method_result_dir)
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

    tests_output_dir = _resolve_tests_output_dir(focal_method_result_dir, project_dir)

    if not tests_output_dir:
        logger.warning("[ToolRunner] tests_output_dir not found (focal=%s, project=%s)",
                       focal_method_result_dir, project_dir)
        return None

    logger.info("[ToolRunner] tests_output_dir = %s", tests_output_dir)

    diag_map = _build_diag_map(tests_output_dir)

    out_path = os.path.join(tests_output_dir, DIAG_JSON_NAME)
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(diag_map, f, indent=2, ensure_ascii=False)
        logger.info("[ToolRunner] suite_diagnosis.json → %d tests: %s", len(diag_map), out_path)

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
    candidates = [
        os.path.join(focal_method_result_dir, DIAG_JSON_NAME),
    ]
    latest = _find_latest_tests_dir(project_dir)
    if latest:
        candidates.append(os.path.join(latest, DIAG_JSON_NAME))

    for path in candidates:
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception as e:
                logger.debug("[ToolRunner] failed to clear %s: %s", path, e)


def _resolve_tests_output_dir(focal_method_result_dir: str,
                               project_dir: str) -> Optional[str]:
    branch1_indicators = [
        os.path.join(focal_method_result_dir, "logs", "diagnosis.log"),
        os.path.join(focal_method_result_dir, "tests_ChatGPT"),
        os.path.join(focal_method_result_dir, "compiler_output"),
        os.path.join(focal_method_result_dir, "test_output"),
    ]
    for indicator in branch1_indicators:
        if os.path.exists(indicator):
            return focal_method_result_dir

    latest = _find_latest_tests_dir(project_dir)
    if latest:
        return latest

    return focal_method_result_dir


# ════════════════════════════════════════════════════════════════════
# 数据提取
# ════════════════════════════════════════════════════════════════════

def _build_diag_map(tests_output_dir: str) -> Dict[str, dict]:
    diag: Dict[str, dict] = {}
    _load_status_csv(tests_output_dir, diag)
    _load_diagnosis_log(tests_output_dir, diag)
    _load_coverage_csv(tests_output_dir, diag)
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
            # 内部跟踪当前已知的最高优先级状态
            "_current_status":   "unknown",
        }
    return diag[tc]


def _get_current_status(entry: dict) -> str:
    """从 entry 推断当前已知的最高优先级状态字符串。"""
    cs = entry.get("compile_status", "unknown")
    es = entry.get("exec_status",    "unknown")
    if cs == "fail":
        return "compile_fail"
    if es == "timeout":
        return "exec_timeout"
    if es == "fail":
        return "exec_fail"
    if es == "pass":
        return "exec_ok"
    return "unknown"


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
    """
    从 status CSV 读取 compile/exec 状态。
    对于同一个 test_class 出现多次（追加模式的多轮），
    采用高优先级状态优先原则（compile_fail > exec_timeout > exec_fail > exec_ok）。
    """
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
                is_timeout = str(row.get("exec_timeout", "false")).lower() in ("true", "1")
                if is_timeout and es == "fail":
                    es = "timeout"

                # 推断本行的状态
                if cs == "fail":
                    row_status = "compile_fail"
                elif es == "timeout":
                    row_status = "exec_timeout"
                elif es == "fail":
                    row_status = "exec_fail"
                elif es in ("pass", "ok"):
                    row_status = "exec_ok"
                else:
                    row_status = "unknown"

                current_status = _get_current_status(entry)

                # 只有新状态优先级 >= 当前状态才更新（高优先级不被低优先级覆盖）
                if _status_priority(row_status) >= _status_priority(current_status):
                    if cs:
                        entry["compile_status"] = cs
                    if es and es != "pending":
                        entry["exec_status"] = es if es != "timeout" else "timeout"

                rows_read += 1
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
            break

    if not log_path:
        return

    try:
        with open(log_path, encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception as e:
        return

    raw_blocks = re.split(r'\[DIAGNOSIS\]', content)
    parsed = 0
    for block in raw_blocks[1:]:
        _parse_diag_block(block, diag)
        parsed += 1
    logger.info("[ToolRunner] parsed %d [DIAGNOSIS] blocks from %s", parsed, log_path)


def _parse_diag_block(block: str, diag: dict):
    """
    解析单个 [DIAGNOSIS] 块并更新 diag 字典。

    关键修复：
    1. 正确处理缺少 error_type 的 exec_fail 块（test_runner.py 的 bug）
    2. 高优先级状态不被低优先级覆盖
       （compile_fail > exec_timeout > exec_fail > exec_ok）
    3. compile_errors 和 exec_errors 根据 status 正确分类，
       而不是根据 error_type（因为 error_type 可能缺失）
    4. exec_ok 块（coverage_gap）只更新覆盖率相关字段，
       不覆盖已知的 compile_fail/exec_fail 状态
    """
    lines = block.splitlines()
    if not lines:
        return

    tc_match = re.match(r'\s*test_class=(.+)', lines[0])
    if not tc_match:
        return
    tc = _short(tc_match.group(1).strip())

    entry = _ensure(diag, tc)
    current_status = _get_current_status(entry)

    # ── 第一遍：解析 status 和 error_type ──────────────────────
    block_status    = None
    block_error_type = None
    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "---":
            break
        sm = re.match(r'status=(\S+)', stripped)
        if sm:
            block_status = sm.group(1)
        etm = re.match(r'error_type=(\S+)', stripped)
        if etm:
            block_error_type = etm.group(1)

    if block_status is None:
        return

    # ── 决定是否允许本块更新状态 ────────────────────────────────
    # exec_ok（coverage_gap）块不应覆盖 compile_fail / exec_fail 状态
    new_prio     = _status_priority(block_status)
    current_prio = _status_priority(current_status)

    # 如果 block_status == exec_ok 但当前已知更高优先级状态，
    # 本块只更新覆盖率等辅助字段，不覆盖 compile/exec status
    can_update_status = (new_prio >= current_prio)

    if can_update_status:
        entry["compile_status"] = "pass"
        entry["exec_status"]    = "pass"
        if block_status == "compile_fail":
            entry["compile_status"] = "fail"
            entry["exec_status"]    = "skip"
        elif block_status == "exec_fail":
            entry["exec_status"] = "fail"
        elif block_status == "exec_timeout":
            entry["exec_status"] = "timeout"
        # exec_ok → compile=pass, exec=pass（已在上面设置）

    # ── 第二遍：解析详细内容 ────────────────────────────────────
    in_core_errors     = False
    in_missed_methods  = False
    in_partial_methods = False
    in_full_stderr     = False

    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "---":
            break

        # 跳过已解析的 status / error_type 行
        if re.match(r'status=', stripped) or re.match(r'error_type=', stripped):
            in_core_errors = in_missed_methods = in_partial_methods = in_full_stderr = False
            continue

        # 进入各节
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
                # 根据 block_status 决定放入 compile_errors 还是 exec_errors
                if block_status == "compile_fail":
                    entry["compile_errors"].append(val)
                elif block_status in ("exec_fail", "exec_timeout"):
                    # ★ 修复：exec_fail 的 core_errors 应该放入 exec_errors
                    entry["exec_errors"].append(val)
                # exec_ok 的 core_errors 忽略（不应该有）
            elif in_missed_methods:
                entry["missed_methods"].append(val)
            elif in_partial_methods:
                entry["partial_methods"].append(val)
            continue

        if in_full_stderr:
            continue
        if stripped and not stripped.startswith("-"):
            # 遇到非列表行，重置节标志
            in_core_errors = in_missed_methods = in_partial_methods = False

    # 去重并截断
    entry["compile_errors"] = list(dict.fromkeys(entry["compile_errors"]))[:10]
    entry["exec_errors"]    = list(dict.fromkeys(entry["exec_errors"]))[:10]
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
    """
    从 coveragedetail CSV 读取覆盖率数据。
    追加模式下同一 test_class 可能出现多次，取最后一行的值
    （最后一轮 refine 后的覆盖率）。
    """
    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                tc = _short(row.get("test_class", "").strip())
                if not tc:
                    continue
                entry = _ensure(diag, tc)

                # 覆盖率数据：compile_fail 的 test 跳过（值为空）
                exec_note = row.get("exec_status", "").strip().lower()
                if exec_note == "compile_fail":
                    continue

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
        # 清理内部字段
        for entry in data.values():
            entry.pop("_current_status", None)
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