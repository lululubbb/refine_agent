"""
tool_runner_adapter.py  (bug-fix edition — Issues 1 & 2)

Bug 1 fix: status/coveragedetail/diagnosis CSVs and diagnosis.log are all
  opened in APPEND mode by test_runner.py, so the same test_class appears
  multiple times across rounds.  The old "high priority wins" strategy kept
  a compile_fail row from round N even after it was fixed in round N+1.
  Fix: "last row wins" — the final occurrence always reflects the most
  recent test run, which is exactly what the fix prompt must show.

Bug 2 fix: compiler_output/ and test_output/ directories are never cleaned
  between rounds, so _load_full_errors_from_files() was overwriting fresh
  diagnosis data with stale error files from previous rounds.
  Fix: only use a disk error file when its mtime >= the java source file's
  mtime (i.e. it was written AFTER the current version of the test).

Redundancy note (Issue 2 of original report): the score stored in
  bigSims.csv column 'redundancy_score' is already (1 - similarity).
  refine_agent.py was doing `1 - score` again → fixed there, not here.
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
        logger.warning("[ToolRunner] tests_output_dir not found")
        return None

    logger.info("[ToolRunner] tests_output_dir = %s", tests_output_dir)

    diag_map = _build_diag_map(tests_output_dir)
    _load_full_errors_from_files(tests_output_dir, diag_map)

    out_path = os.path.join(tests_output_dir, DIAG_JSON_NAME)
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(diag_map, f, indent=2, ensure_ascii=False)
        compile_fail = sum(1 for v in diag_map.values() if v.get("compile_status") == "fail")
        compile_pass = sum(1 for v in diag_map.values() if v.get("compile_status") == "pass")
        exec_fail    = sum(1 for v in diag_map.values() if v.get("exec_status") == "fail")
        exec_pass    = sum(1 for v in diag_map.values() if v.get("exec_status") == "pass")
        logger.info("[ToolRunner] diag: compile_pass=%d fail=%d exec_pass=%d fail=%d",
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
            except Exception:
                pass


def _resolve_tests_output_dir(focal_method_result_dir: str,
                               project_dir: str) -> Optional[str]:
    indicators = [
        os.path.join(focal_method_result_dir, "logs", "diagnosis.log"),
        os.path.join(focal_method_result_dir, "tests_ChatGPT"),
        os.path.join(focal_method_result_dir, "compiler_output"),
        os.path.join(focal_method_result_dir, "test_output"),
    ]
    for p in indicators:
        if os.path.exists(p):
            return focal_method_result_dir
    latest = _find_latest_tests_dir(project_dir)
    return latest or focal_method_result_dir


# ════════════════════════════════════════════════════════════════════
# Bug 2 fix: load disk errors only when file is fresh
# ════════════════════════════════════════════════════════════════════

def _java_mtime(tests_output_dir: str, tc_key: str) -> float:
    """Return mtime of test_cases/<tc_key>.java, 0.0 if absent."""
    tc_short = tc_key.rsplit(".", 1)[-1]
    for name in (tc_key, tc_short):
        p = os.path.join(tests_output_dir, "test_cases", f"{name}.java")
        if os.path.exists(p):
            try:
                return os.path.getmtime(p)
            except Exception:
                return 0.0
    return 0.0


def _is_fresh(file_path: str, java_mtime: float) -> bool:
    """True if file_path was written at or after the java source."""
    if java_mtime == 0.0:
        return True   # unknown source mtime → be permissive
    try:
        return os.path.getmtime(file_path) >= java_mtime - 1.0  # 1s tolerance
    except Exception:
        return False


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
            tc_key = _find_diag_key(diag, tc_name)
            if tc_key is None:
                continue
            entry = diag[tc_key]
            if entry.get("compile_status") != "fail":
                continue  # current round compile passed → ignore old file

            fpath = os.path.join(compile_dir, fname)
            jm = _java_mtime(tests_output_dir, tc_key)
            if not _is_fresh(fpath, jm):
                logger.debug("[FullError] skip stale compile file for %s", tc_key)
                continue

            raw = _read_error_file(fpath, _MAX_COMPILE_ERROR_LINES)
            if raw:
                parsed = _parse_compile_error_content(raw)
                if parsed:
                    entry["compile_errors"] = parsed[:30]

    if os.path.isdir(test_dir):
        for fname in os.listdir(test_dir):
            if not fname.endswith(".txt"):
                continue
            tc_name = _extract_tc_name_from_test_file(fname)
            if not tc_name:
                continue
            tc_key = _find_diag_key(diag, tc_name)
            if tc_key is None:
                continue
            entry = diag[tc_key]
            if entry.get("exec_status") != "fail":
                continue

            fpath = os.path.join(test_dir, fname)
            jm = _java_mtime(tests_output_dir, tc_key)
            if not _is_fresh(fpath, jm):
                logger.debug("[FullError] skip stale exec file for %s", tc_key)
                continue

            raw = _read_error_file(fpath, _MAX_RUNTIME_ERROR_LINES)
            if raw:
                parsed = _parse_runtime_error_content(raw)
                if parsed:
                    entry["exec_errors"] = parsed[:20]


def _extract_tc_name_from_compile_file(fname: str) -> str:
    base = fname[:-4] if fname.endswith(".txt") else fname
    base = base[:-5] if base.endswith(".java") else base
    for prefix in ("CompilerOutput-", "CompilerOutput_"):
        if base.startswith(prefix):
            return base[len(prefix):]
    return ""


def _extract_tc_name_from_test_file(fname: str) -> str:
    base = fname[:-4] if fname.endswith(".txt") else fname
    base = base[:-5] if base.endswith(".java") else base
    for prefix in ("TestOutput-", "TestOutput_", "runtime_error-"):
        if base.startswith(prefix):
            return base[len(prefix):]
    return ""


def _read_error_file(fpath: str, max_lines: int = 80) -> str:
    try:
        with open(fpath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        if len(lines) > max_lines:
            return "".join(lines[:max_lines]) + f"\n... [{len(lines)-max_lines} more lines] ..."
        return "".join(lines).strip()
    except Exception:
        return ""


def _parse_compile_error_content(raw: str) -> List[str]:
    """
    将原始编译错误文本解析为有意义的错误行列表。
    保留 error/warning 行及其上下文，去掉纯空行。
    """
    lines = raw.splitlines()
    result = []
    for i, line in enumerate(lines):
        if ": error:" in line or "error:" in line.lower():
            if i > 0 and lines[i-1].strip() and lines[i-1].rstrip() not in result:
                result.append(lines[i-1].rstrip())
            result.append(line.rstrip())
            for j in (i+1, i+2):
                if j < len(lines) and (lines[j].strip().startswith("^") or
                        "symbol" in lines[j].lower() or "location" in lines[j].lower()):
                    result.append(lines[j].rstrip())
    if not result:
        for line in lines:
            s = line.strip()
            if s:
                result.append(s[:_MAX_SINGLE_ERROR_CHARS])
            if len(result) >= 30:
                break
    seen, deduped = set(), []
    for item in result:
        k = item.strip()
        if k and k not in seen:
            seen.add(k)
            deduped.append(item[:_MAX_SINGLE_ERROR_CHARS])
    return deduped


def _parse_runtime_error_content(raw: str) -> List[str]:
    """
    将原始运行错误文本解析为有意义的错误行列表。
    重点提取：AssertionError、Exception、expected/but was、FAILED 等关键行。
    """
    lines = raw.splitlines()
    key_kw = ["AssertionError","AssertionFailedError","expected:","but was:",
               "Exception","Error","FAILED","FAILURE","NullPointerException",
               "IllegalArgumentException","IllegalStateException",
               "IndexOutOfBoundsException","org.opentest4j","junit.framework"]
    result = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if s.startswith("at ") and len([r for r in result if r.startswith("at ")]) >= 3:
            continue
        if any(k in line for k in key_kw):
            result.append(s[:_MAX_SINGLE_ERROR_CHARS])
        elif s.startswith("at ") and len([r for r in result if r.startswith("at ")]) < 3:
            result.append(s[:200])
    if len(result) < 3:
        for line in lines:
            s = line.strip()
            if s and s not in result:
                result.append(s[:_MAX_SINGLE_ERROR_CHARS])
            if len(result) >= 20:
                break
    seen, deduped = set(), []
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
        if key.rsplit(".", 1)[-1] == tc_short:
            return key
    return None


# ════════════════════════════════════════════════════════════════════
# Diag map construction
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
            "compile_status":     "unknown",
            "exec_status":        "unknown",
            "compile_errors":     [],
            "exec_errors":        [],
            "focal_line_rate":    None,
            "focal_branch_rate":  None,
            "focal_line_covered": None,
            "focal_line_total":   None,
            "missed_methods":     [],
            "partial_methods":    [],
        }
    return diag[tc]


# ── *_status.csv ─────────────────────────────────────────────────
# Bug 1 fix: last row wins (append mode → last = most recent round)

def _load_status_csv(tests_output_dir: str, diag: dict):
    search_dirs = [tests_output_dir, os.path.dirname(tests_output_dir)]
    for d in search_dirs:
        if not os.path.isdir(d):
            continue
        csv_files = glob.glob(os.path.join(d, "*_status*.csv"))
        if csv_files:
            for csv_path in sorted(csv_files):
                _parse_status_csv(csv_path, diag)
            return
    logger.warning("[ToolRunner] no *_status*.csv found under %s", tests_output_dir)


def _parse_status_csv(csv_path: str, diag: dict):
    """Last row wins: final occurrence of each test_class = most recent result."""
    try:
        latest: Dict[str, dict] = {}
        with open(csv_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                tc = _short(row.get("test_class", "").strip())
                if tc:
                    latest[tc] = row   # overwrite → last row wins

        for tc, row in latest.items():
            entry = _ensure(diag, tc)
            cs = row.get("compile_status", "").lower().strip()
            es = row.get("exec_status",    "").lower().strip()
            is_timeout = str(row.get("exec_timeout", "false")).lower() in ("true", "1")
            if is_timeout and es == "fail":
                es = "timeout"
            if cs:
                entry["compile_status"] = cs
            if es and es not in ("pending",):
                entry["exec_status"] = es
    except Exception as e:
        logger.warning("status csv %s: %s", csv_path, e)


# ── diagnosis.log ─────────────────────────────────────────────────
# Bug 1 fix: last [DIAGNOSIS] block for each test_class wins

def _load_diagnosis_log(tests_output_dir: str, diag: dict):
    candidates = [
        os.path.join(tests_output_dir, "logs", "diagnosis.log"),
        os.path.join(tests_output_dir, "diagnosis.log"),
        os.path.join(os.path.dirname(tests_output_dir), "logs", "diagnosis.log"),
    ]
    log_path = next((c for c in candidates if os.path.exists(c) and os.path.getsize(c) > 0), None)
    if not log_path:
        return
    try:
        with open(log_path, encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception:
        return

    raw_blocks = re.split(r'\[DIAGNOSIS\]', content)

    # Collect all parsed blocks, keep only the last one per tc
    per_tc: Dict[str, dict] = {}
    for block in raw_blocks[1:]:
        parsed = _parse_diag_block_to_dict(block)
        if parsed:
            tc = parsed["tc"]
            per_tc[tc] = parsed   # last block wins

    for tc, parsed in per_tc.items():
        entry = _ensure(diag, tc)
        _apply_diag_block(entry, parsed)

    logger.info("[ToolRunner] applied %d diagnosis blocks from %s", len(per_tc), log_path)


def _parse_diag_block_to_dict(block: str) -> Optional[dict]:
    """Parse a [DIAGNOSIS] block into a dict; return None if unparseable."""
    lines = block.splitlines()
    if not lines:
        return None
    tc_match = re.match(r'\s*test_class=(.+)', lines[0])
    if not tc_match:
        return None
    tc = _short(tc_match.group(1).strip())

    block_status = None
    for line in lines[1:]:
        s = line.strip()
        if s == "---":
            break
        m = re.match(r'status=(\S+)', s)
        if m:
            block_status = m.group(1)

    if block_status is None:
        return None

    compile_errors: List[str] = []
    exec_errors:    List[str] = []
    missed:         List[str] = []
    partial:        List[str] = []

    in_core = in_missed = in_partial = in_full_stderr = False

    for line in lines[1:]:
        s = line.strip()
        if s == "---":
            break
        if re.match(r'core_errors\s*(\(\d+\))?:', s):
            in_core = True; in_missed = in_partial = in_full_stderr = False; continue
        if re.match(r'full_stderr\s*\(', s):
            in_full_stderr = True; in_core = in_missed = in_partial = False; continue
        if re.match(r'(missed_methods|uncovered_methods)(\s*\(\d+\))?:', s):
            in_missed = True; in_core = in_partial = in_full_stderr = False; continue
        if re.match(r'(partial_methods|partial_branch_methods)(\s*\(\d+\))?:', s):
            in_partial = True; in_core = in_missed = in_full_stderr = False; continue

        item_m = re.match(r'-\s+(.+)', s)
        if item_m:
            val = item_m.group(1).strip()
            if in_core and not in_full_stderr:
                if block_status == "compile_fail":
                    compile_errors.append(val)
                elif block_status in ("exec_fail", "exec_timeout"):
                    exec_errors.append(val)
            elif in_missed:
                missed.append(val)
            elif in_partial:
                partial.append(val)
            continue

        if in_full_stderr:
            continue
        is_meta = (not s or any(s.startswith(p) for p in
                   ("project=","target_class=","focal_method=","status=","error_type=",
                    "line_rate=","branch_rate=","coverage_score=","... [")))
        if is_meta:
            continue
        if s and not s.startswith("-"):
            in_core = in_missed = in_partial = False

    return {
        "tc": tc,
        "block_status": block_status,
        "compile_errors": list(dict.fromkeys(compile_errors))[:30],
        "exec_errors":    list(dict.fromkeys(exec_errors))[:30],
        "missed_methods": list(dict.fromkeys(missed)),
        "partial_methods":list(dict.fromkeys(partial)),
    }


def _apply_diag_block(entry: dict, parsed: dict):
    """Apply a parsed diagnosis block to an entry dict."""
    block_status = parsed["block_status"]
    # Always reset and re-apply from the latest block
    entry["compile_status"] = "pass"
    entry["exec_status"]    = "pass"
    entry["compile_errors"] = []
    entry["exec_errors"]    = []
    entry["missed_methods"] = []
    entry["partial_methods"]= []

    if block_status == "compile_fail":
        entry["compile_status"] = "fail"
        entry["exec_status"]    = "skip"
    elif block_status == "exec_fail":
        entry["exec_status"] = "fail"
    elif block_status == "exec_timeout":
        entry["exec_status"] = "timeout"

    entry["compile_errors"]  = parsed["compile_errors"]
    entry["exec_errors"]     = parsed["exec_errors"]
    entry["missed_methods"]  = parsed["missed_methods"]
    entry["partial_methods"] = parsed["partial_methods"]


# ── coveragedetail CSV ─────────────────────────────────────────────

def _load_coverage_csv(tests_output_dir: str, diag: dict):
    search_dirs = [tests_output_dir, os.path.dirname(tests_output_dir)]
    for d in search_dirs:
        if not os.path.isdir(d):
            continue
        cov_files = sorted(glob.glob(os.path.join(d, "*coveragedetail*.csv")))
        if cov_files:
            _parse_coverage_csv(cov_files[-1], diag)
            return


def _parse_coverage_csv(csv_path: str, diag: dict):
    """Last row wins (append mode)."""
    try:
        latest: Dict[str, dict] = {}
        with open(csv_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                tc = _short(row.get("test_class", "").strip())
                if tc:
                    latest[tc] = row

        for tc, row in latest.items():
            entry = _ensure(diag, tc)
            if row.get("exec_status", "").strip().lower() == "compile_fail":
                continue
            for field, key in [("f_per_line_rate","focal_line_rate"),
                                ("f_per_branch_rate","focal_branch_rate")]:
                v = row.get(field, "").strip()
                if v:
                    try: entry[key] = round(float(v), 2)
                    except Exception: pass
            for fc, dk in [("f_per_line_cov","focal_line_covered"),
                           ("f_per_line_total","focal_line_total")]:
                v = row.get(fc, "").strip()
                if v:
                    try: entry[dk] = int(float(v))
                    except Exception: pass
    except Exception as e:
        logger.warning("coveragedetail csv %s: %s", csv_path, e)


# ════════════════════════════════════════════════════════════════════
# Public loader
# ════════════════════════════════════════════════════════════════════

def load_suite_diagnosis(tests_output_dir: str) -> Dict[str, dict]:
    path = os.path.join(tests_output_dir, DIAG_JSON_NAME)
    if not os.path.exists(path):
        logger.warning("suite_diagnosis.json not found: %s", path)
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        logger.info("[ToolRunner] loaded suite_diagnosis.json: %d entries", len(data))
        return data
    except Exception as e:
        logger.warning("failed to load suite_diagnosis.json: %s", e)
        return {}


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