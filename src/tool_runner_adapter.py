"""
tool_runner_adapter.py  (with Issue-3 fix: focal line counts in diag)

Changes:
  - _parse_coverage_csv now also reads f_per_line_cov / f_per_line_total
    and stores them as focal_line_covered / focal_line_total in the diag entry.
  - _parse_diag_block retains existing logic unchanged.
  - _load_full_errors_from_files retained unchanged.
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

# 单条错误消息最大字符数（防止超长日志撑爆 prompt）
_MAX_SINGLE_ERROR_CHARS = 2000
# 编译错误文件最大读取行数
_MAX_COMPILE_ERROR_LINES = 80
# 运行错误文件最大读取行数
_MAX_RUNTIME_ERROR_LINES = 60

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
# Main entry
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
    _load_full_errors_from_files(tests_output_dir, diag_map)

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
    candidates = [os.path.join(focal_method_result_dir, DIAG_JSON_NAME)]
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
# Full error loading from disk files (unchanged)
# ════════════════════════════════════════════════════════════════════

def _load_full_errors_from_files(tests_output_dir: str, diag: dict):
    """
    从 compiler_output/ 和 test_output/ 目录读取完整的错误文件内容，
    用完整错误信息替换/补充 diagnosis.log 中可能被截断的错误条目。

    文件命名约定（test_runner.py 生成）：
      compiler_output/CompilerOutput-<ClassName>.java.txt  → 编译错误
      test_output/TestOutput-<ClassName>.java.txt          → 运行错误
    """
    compile_dir = os.path.join(tests_output_dir, "compiler_output")
    test_dir    = os.path.join(tests_output_dir, "test_output")

    # ── 读取编译错误文件 ─────────────────────────────────────────────
    if os.path.isdir(compile_dir):
        for fname in os.listdir(compile_dir):
            if not fname.endswith(".txt"):
                continue
            tc_name = _extract_tc_name_from_compile_file(fname)
            if not tc_name:
                continue
            fpath = os.path.join(compile_dir, fname)
            full_errors = _read_error_file(fpath, max_lines=_MAX_COMPILE_ERROR_LINES)
            if not full_errors:
                continue
            tc_key = _find_diag_key(diag, tc_name)
            if tc_key is None:
                continue
            entry = diag[tc_key]
            if entry.get("compile_status") == "fail":
                parsed_errors = _parse_compile_error_content(full_errors)
                if parsed_errors:
                    entry["compile_errors"] = parsed_errors[:30]

    # ── 读取运行错误文件 ─────────────────────────────────────────────
    if os.path.isdir(test_dir):
        for fname in os.listdir(test_dir):
            if not fname.endswith(".txt"):
                continue
            tc_name = _extract_tc_name_from_test_file(fname)
            if not tc_name:
                continue
            fpath = os.path.join(test_dir, fname)
            full_errors = _read_error_file(fpath, max_lines=_MAX_RUNTIME_ERROR_LINES)
            if not full_errors:
                continue
            tc_key = _find_diag_key(diag, tc_name)
            if tc_key is None:
                continue
            entry = diag[tc_key]
            if entry.get("exec_status") == "fail":
                parsed_errors = _parse_runtime_error_content(full_errors)
                if parsed_errors:
                    entry["exec_errors"] = parsed_errors[:20]


def _extract_tc_name_from_compile_file(fname: str) -> str:
    """
    从编译错误文件名提取测试类名。
    示例：
      CompilerOutput-Lexer_4_2Test.java.txt → Lexer_4_2Test
      compile_error.txt → (空，跳过)
    """
    # 去掉 .txt 后缀
    base = fname
    if base.endswith(".txt"):
        base = base[:-4]
    if base.endswith(".java"):
        base = base[:-5]
    for prefix in ("CompilerOutput-", "CompilerOutput_"):
        if base.startswith(prefix):
            return base[len(prefix):]
    if base.lower() in ("compile_error", "compileroutput"):
        return ""
    return ""


def _extract_tc_name_from_test_file(fname: str) -> str:
    """
    从运行错误文件名提取测试类名。
    示例：
      TestOutput-Lexer_4_2Test.java.txt → Lexer_4_2Test
      runtime_error.txt → (空，跳过)
    """
    base = fname
    if base.endswith(".txt"):
        base = base[:-4]
    if base.endswith(".java"):
        base = base[:-5]
    for prefix in ("TestOutput-", "TestOutput_", "runtime_error-"):
        if base.startswith(prefix):
            return base[len(prefix):]
    if base.lower() in ("runtime_error", "testoutput"):
        return ""
    return ""


def _read_error_file(fpath: str, max_lines: int = 80) -> str:
    try:
        with open(fpath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        if len(lines) > max_lines:
            content = "".join(lines[:max_lines])
            content += f"\n... [{len(lines) - max_lines} more lines truncated] ..."
        else:
            content = "".join(lines)
        return content.strip()
    except Exception as e:
        logger.debug("[FullError] read %s failed: %s", fpath, e)
        return ""


def _parse_compile_error_content(raw: str) -> List[str]:
    """
    将原始编译错误文本解析为有意义的错误行列表。
    保留 error/warning 行及其上下文，去掉纯空行。
    """
    lines = raw.splitlines()
    result = []
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        # 保留包含 error: 或 warning: 的行及其前后1行上下文
        if ": error:" in line or ": warning:" in line or "error:" in line.lower():
            # 加入前一行（通常是文件位置行）
            if i > 0 and lines[i-1].strip() and lines[i-1].strip() not in result:
                result.append(lines[i-1].rstrip())
            result.append(line)
            # 加入后面的 ^ 指示行
            if i + 1 < len(lines) and (lines[i+1].strip().startswith("^") or
                                         "symbol" in lines[i+1].lower() or
                                         "location" in lines[i+1].lower()):
                result.append(lines[i+1].rstrip())
                if i + 2 < len(lines) and ("symbol" in lines[i+2].lower() or
                                             "location" in lines[i+2].lower()):
                    result.append(lines[i+2].rstrip())
        i += 1

    if not result:
        for line in lines:
            stripped = line.strip()
            if stripped:
                result.append(stripped[:_MAX_SINGLE_ERROR_CHARS])
            if len(result) >= 30:
                break

    seen = set()
    deduped = []
    for item in result:
        key = item.strip()
        if key and key not in seen:
            seen.add(key)
            deduped.append(item[:_MAX_SINGLE_ERROR_CHARS])
    return deduped


def _parse_runtime_error_content(raw: str) -> List[str]:
    """
    将原始运行错误文本解析为有意义的错误行列表。
    重点提取：AssertionError、Exception、expected/but was、FAILED 等关键行。
    """
    lines = raw.splitlines()
    result = []
    key_patterns = [
        "AssertionError", "AssertionFailedError",
        "expected:", "but was:", "expected:<", "but was:<",
        "Exception", "Error",
        "FAILED", "FAILURE",
        "org.opentest4j", "junit.framework",
        "NullPointerException", "IllegalArgumentException",
        "IllegalStateException", "IndexOutOfBoundsException",
    ]
    # 第一遍：提取关键行
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        # 跳过纯 at 栈帧行（只保留前几行栈帧）
        if stripped.startswith("at ") and len([r for r in result if r.startswith("at ")]) >= 3:
            continue
        if any(kw in line for kw in key_patterns):
            result.append(stripped[:_MAX_SINGLE_ERROR_CHARS])
        elif stripped.startswith("at ") and len([r for r in result if r.startswith("at ")]) < 3:
            result.append(stripped[:200])

    # 如果关键行太少，补充原始内容
    if len(result) < 3:
        for line in lines:
            stripped = line.strip()
            if stripped and stripped not in result:
                result.append(stripped[:_MAX_SINGLE_ERROR_CHARS])
            if len(result) >= 20:
                break

    # 去重
    seen = set()
    deduped = []
    for item in result:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped[:20]


def _find_diag_key(diag: dict, tc_name: str) -> Optional[str]:
    """在 diag 字典中找到与 tc_name 匹配的键。"""
    # 精确匹配
    if tc_name in diag:
        return tc_name
    tc_short = tc_name.rsplit(".", 1)[-1]
    if tc_short in diag:
        return tc_short
    for key in diag:
        key_short = key.rsplit(".", 1)[-1]
        if key_short == tc_short or tc_short in key_short or key_short in tc_short:
            return key
    return None


# ════════════════════════════════════════════════════════════════════
# Data extraction
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
            # Issue 3: focal line counts
            "focal_line_covered": None,
            "focal_line_total":   None,
            "missed_methods":    [],
            "partial_methods":   [],
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
    search_dirs = [tests_output_dir, os.path.dirname(tests_output_dir)]
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
                if _status_priority(row_status) >= _status_priority(current_status):
                    if cs:
                        entry["compile_status"] = cs
                    if es and es != "pending":
                        entry["exec_status"] = es if es != "timeout" else "timeout"
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
    except Exception:
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
    current_status = _get_current_status(entry)

    block_status     = None
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

    new_prio     = _status_priority(block_status)
    current_prio = _status_priority(current_status)
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

    in_core_errors     = False
    in_missed_methods  = False
    in_partial_methods = False
    in_full_stderr     = False

    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "---":
            break

        if re.match(r'core_errors\s*(\(\d+\))?:', stripped):
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

        if re.match(r'(missed_methods|uncovered_methods)(\s*\(\d+\))?:', stripped):
            in_core_errors     = False
            in_full_stderr     = False
            in_missed_methods  = True
            in_partial_methods = False
            continue

        if re.match(r'(partial_methods|partial_branch_methods)(\s*\(\d+\))?:', stripped):
            in_core_errors     = False
            in_full_stderr     = False
            in_missed_methods  = False
            in_partial_methods = True
            continue

        item_m = re.match(r'-\s+(.+)', stripped)
        if item_m:
            val = item_m.group(1).strip()
            if in_core_errors and not in_full_stderr:
                if block_status == "compile_fail":
                    entry["compile_errors"].append(val)
                elif block_status in ("exec_fail", "exec_timeout"):
                    entry["exec_errors"].append(val)
            elif in_missed_methods:
                entry["missed_methods"].append(val)
            elif in_partial_methods:
                entry["partial_methods"].append(val)
            continue

        if in_full_stderr:
            continue

        is_meta = (
            not stripped
            or stripped.startswith("project=")
            or stripped.startswith("target_class=")
            or stripped.startswith("focal_method=")
            or stripped.startswith("status=")
            or stripped.startswith("error_type=")
            or stripped.startswith("line_rate=")
            or stripped.startswith("branch_rate=")
            or stripped.startswith("coverage_score=")
            or stripped.startswith("... [")
        )
        if is_meta:
            continue

        if stripped and not stripped.startswith("-"):
            in_core_errors = in_missed_methods = in_partial_methods = False

    entry["compile_errors"]  = list(dict.fromkeys(entry["compile_errors"]))[:30]
    entry["exec_errors"]     = list(dict.fromkeys(entry["exec_errors"]))[:30]
    entry["missed_methods"]  = list(dict.fromkeys(entry["missed_methods"]))
    entry["partial_methods"] = list(dict.fromkeys(entry["partial_methods"]))


# ── *coveragedetail*.csv  (Issue 3: also read focal line counts) ──

def _load_coverage_csv(tests_output_dir: str, diag: dict):
    search_dirs = [tests_output_dir, os.path.dirname(tests_output_dir)]
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
    Read per-test focal method coverage from coveragedetail CSV.

    Issue 3 fix: also populate focal_line_covered / focal_line_total
    so the Refiner can give the LLM concrete line counts instead of
    only showing class-level missed methods.
    """
    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                tc = _short(row.get("test_class", "").strip())
                if not tc:
                    continue
                entry = _ensure(diag, tc)

                exec_note = row.get("exec_status", "").strip().lower()
                if exec_note == "compile_fail":
                    continue

                # Focal method line/branch rates
                for field, key in [("f_per_line_rate",   "focal_line_rate"),
                                    ("f_per_branch_rate", "focal_branch_rate")]:
                    val = row.get(field, "").strip()
                    if val:
                        try:
                            entry[key] = round(float(val), 2)
                        except Exception:
                            pass

                # ── Issue 3: focal line counts ──────────────────────
                for csv_col, diag_key in [
                    ("f_per_line_cov",   "focal_line_covered"),
                    ("f_per_line_total", "focal_line_total"),
                ]:
                    val = row.get(csv_col, "").strip()
                    if val:
                        try:
                            entry[diag_key] = int(float(val))
                        except Exception:
                            pass

    except Exception as e:
        logger.warning("coveragedetail csv %s: %s", csv_path, e)


# ════════════════════════════════════════════════════════════════════
# Read suite_diagnosis.json
# ════════════════════════════════════════════════════════════════════

def load_suite_diagnosis(tests_output_dir: str) -> Dict[str, dict]:
    path = os.path.join(tests_output_dir, DIAG_JSON_NAME)
    if not os.path.exists(path):
        logger.warning("suite_diagnosis.json not found: %s", path)
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for entry in data.values():
            entry.pop("_current_status", None)
        logger.info("[ToolRunner] loaded suite_diagnosis.json: %d entries from %s",
                    len(data), path)
        return data
    except Exception as e:
        logger.warning("failed to load suite_diagnosis.json: %s", e)
        return {}


# ════════════════════════════════════════════════════════════════════
# Helpers
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