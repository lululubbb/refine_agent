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
# 主入口：调用 TestRunner 并输出 suite_diagnosis.json
# ════════════════════════════════════════════════════════════════════

def run_and_export(
    focal_method_result_dir: str,
    project_dir: str,
) -> Optional[str]:
    """
    1. 调用 TestRunner.start_all_test()
    2. 找到 TestRunner 在 project_dir 下创建的最新 tests%T/ 目录
    3. 从该目录下的 *_status.csv + diagnosis.log + coveragedetail.csv 提取数据
    4. 写入 tests_output_dir/suite_diagnosis.json
    5. 返回 tests_output_dir 路径（None = TestRunner 失败）

    Parameters
    ----------
    focal_method_result_dir : base_dir，含 test_cases/ 子目录
    project_dir             : defect4j_projects/Csv_1_b（Maven 项目根目录）
    """
    tests_output_dir = None
    try:
        from test_runner import TestRunner
        runner = TestRunner(
            test_path   = focal_method_result_dir,
            target_path = project_dir,
        )
        runner.start_all_test()
        tests_output_dir = _find_latest_tests_dir(project_dir)
    except Exception as e:
        logger.warning("[ToolRunner] TestRunner failed: %s", e)
        return None

    if not tests_output_dir:
        logger.warning("[ToolRunner] tests output dir not found under %s", project_dir)
        return None

    # 从多个文件提取数据，整合成统一 dict
    diag_map = _build_diag_map(tests_output_dir)

    # 写入 JSON
    out_path = os.path.join(tests_output_dir, DIAG_JSON_NAME)
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(diag_map, f, indent=2, ensure_ascii=False)
        logger.info("[ToolRunner] suite_diagnosis.json written: %s (%d tests)",
                    out_path, len(diag_map))
    except Exception as e:
        logger.warning("[ToolRunner] failed to write JSON: %s", e)

    return tests_output_dir


# ════════════════════════════════════════════════════════════════════
# 数据提取：从 tests_output_dir 下的已有文件构建统一 dict
# ════════════════════════════════════════════════════════════════════

def _build_diag_map(tests_output_dir: str) -> Dict[str, dict]:
    """
    整合 status.csv + diagnosis.log + coveragedetail.csv → {test_name: diag_dict}
    """
    diag: Dict[str, dict] = {}

    # ── Step 1: 从 *_status.csv 获取 compile/exec 状态 ─────────────
    _load_status_csv(tests_output_dir, diag)

    # ── Step 2: 从 diagnosis.log 获取错误详情 + missed_methods ──────
    _load_diagnosis_log(tests_output_dir, diag)

    # ── Step 3: 从 coveragedetail.csv 获取覆盖率 ────────────────────
    _load_coverage_csv(tests_output_dir, diag)

    return diag


def _short(full_name: str) -> str:
    """org.pkg.Token_1_1Test → Token_1_1Test"""
    return full_name.rsplit(".", 1)[-1]


def _ensure(diag: dict, tc: str) -> dict:
    """确保 tc 在 diag 中存在，返回其 entry。"""
    if tc not in diag:
        diag[tc] = {
            "compile_status":   "unknown",
            "exec_status":      "unknown",
            "compile_errors":   [],
            "exec_errors":      [],
            "focal_line_rate":  None,
            "focal_branch_rate":None,
            "missed_methods":   [],
            "partial_methods":  [],
        }
    return diag[tc]


# ── Step 1: *_status.csv ─────────────────────────────────────────────

def _load_status_csv(tests_output_dir: str, diag: dict):
    """
    *_status.csv 列：project, target_class, test_class, compile_status,
                     exec_status, exec_timeout, jacoco_exec_size, compile_score, exec_score
    注：compile_status = 'pass'/'fail', exec_status = 'pass'/'fail'/'skip'
    """
    # status CSV 在 tests_output_dir 的父目录（global_csv_parent_dir）
    # TestRunner 把它写到和 tests%T/ 同级的 results_batch 目录下
    # 查找策略：先查 tests_output_dir 本身，再查其父目录
    search_dirs = [
        tests_output_dir,
        os.path.dirname(tests_output_dir),
    ]
    for d in search_dirs:
        csv_files = glob.glob(os.path.join(d, "*_status*.csv"))
        if csv_files:
            for csv_path in sorted(csv_files):
                _parse_status_csv(csv_path, diag)
            return


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
                    # exec_timeout 字段
                    is_timeout = str(row.get("exec_timeout", "false")).lower() in ("true", "1")
                    if is_timeout and es == "fail":
                        entry["exec_status"] = "timeout"
                    else:
                        entry["exec_status"] = es
    except Exception as e:
        logger.debug("status csv %s: %s", csv_path, e)


# ── Step 2: diagnosis.log（Block 解析，正确处理多行格式） ────────────

def _load_diagnosis_log(tests_output_dir: str, diag: dict):
    """
    diagnosis.log 格式（由 TestRunner 写入）：

    [DIAGNOSIS] test_class=org.pkg.Token_1_1Test
      project=Csv_1_b  target_class=Token
      status=compile_fail
      error_type=compile_error
      core_errors (3):
        - Token_1_1Test.java:12: error: cannot find symbol 'Assertions'
        - Token_1_1Test.java:15: error: ...
      full_stderr (45/89 lines):
        ...（可忽略）
    ---

    [DIAGNOSIS] test_class=org.pkg.Token_1_1Test
      status=exec_ok
      error_type=coverage_gap
      line_rate=45.0000%  (9/20)
      branch_rate=33.3333%  (2/6)
      coverage_score=0.39
      missed_methods:
        - reset
        - close
      partial_methods:
        - read
    ---

    解析策略：按 [DIAGNOSIS] 分 block，每个 block 内逐行读取字段。
    """
    log_path = os.path.join(tests_output_dir, "logs", "diagnosis.log")
    if not os.path.exists(log_path):
        return

    # 读取全文，按 [DIAGNOSIS] 切 block
    try:
        with open(log_path, encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception as e:
        logger.debug("diagnosis.log read error: %s", e)
        return

    # 用 [DIAGNOSIS] 作为分隔符切块
    raw_blocks = re.split(r'\[DIAGNOSIS\]', content)
    for block in raw_blocks[1:]:   # 跳过第一个空块
        _parse_diag_block(block, diag)


def _parse_diag_block(block: str, diag: dict):
    """
    解析单个 [DIAGNOSIS] block（已去掉 '[DIAGNOSIS]' 前缀）。
    """
    lines = block.splitlines()
    if not lines:
        return

    # 第一行：test_class=org.pkg.Token_1_1Test
    tc_match = re.match(r'\s*test_class=(.+)', lines[0])
    if not tc_match:
        return
    tc = _short(tc_match.group(1).strip())
    entry = _ensure(diag, tc)

    status = ""
    in_core_errors    = False
    in_missed_methods = False
    in_partial_methods= False
    in_full_stderr    = False

    for line in lines[1:]:
        stripped = line.strip()

        # Block 分隔符
        if stripped == "---":
            break

        # 状态行
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

        # 进入 core_errors 区块
        if re.match(r'core_errors\s*\(?\d*\)?:', stripped):
            in_core_errors     = True
            in_missed_methods  = False
            in_partial_methods = False
            in_full_stderr     = False
            continue

        # 进入 full_stderr 区块（忽略内容，太长）
        if re.match(r'full_stderr\s*\(', stripped):
            in_core_errors     = False
            in_full_stderr     = True
            in_missed_methods  = False
            in_partial_methods = False
            continue

        # 进入 missed_methods 区块
        if re.match(r'missed_methods:', stripped):
            in_core_errors     = False
            in_full_stderr     = False
            in_missed_methods  = True
            in_partial_methods = False
            continue

        # 进入 partial_methods 区块
        if re.match(r'partial_methods:', stripped):
            in_core_errors     = False
            in_full_stderr     = False
            in_missed_methods  = False
            in_partial_methods = True
            continue

        # 列表条目（- xxx）
        item_m = re.match(r'-\s+(.+)', stripped)
        if item_m:
            val = item_m.group(1).strip()
            if in_core_errors and not in_full_stderr:
                # 按 compile/exec 分类到不同 errors 列表
                if entry["compile_status"] == "fail":
                    entry["compile_errors"].append(val)
                else:
                    entry["exec_errors"].append(val)
            elif in_missed_methods:
                entry["missed_methods"].append(val)
            elif in_partial_methods:
                entry["partial_methods"].append(val)
            continue

        # 非列表行进入 full_stderr 时，跳过（避免垃圾数据进 errors）
        if in_full_stderr:
            continue

        # 重置列表状态：遇到非列表、非空行时
        if stripped and not stripped.startswith("-"):
            in_core_errors = in_missed_methods = in_partial_methods = False

    # 去重 + 截断（防止 token 爆炸）
    entry["compile_errors"] = list(dict.fromkeys(entry["compile_errors"]))[:8]
    entry["exec_errors"]    = list(dict.fromkeys(entry["exec_errors"]))[:8]
    entry["missed_methods"] = list(dict.fromkeys(entry["missed_methods"]))
    entry["partial_methods"]= list(dict.fromkeys(entry["partial_methods"]))


# ── Step 3: *coveragedetail*.csv ─────────────────────────────────────

def _load_coverage_csv(tests_output_dir: str, diag: dict):
    """
    *coveragedetail*.csv 列（由 TestRunner._write_per_test_status 写入）：
    project, target_class, test_class, exec_status,
    m_per_line_cov, m_per_line_total, m_per_line_rate,  ...（class 级）
    f_per_line_cov, f_per_line_total, f_per_line_rate,  ...（focal method 级）
    f_per_branch_cov, f_per_branch_total, f_per_branch_rate, ...

    注：coveragedetail.csv 也写在 global_csv_parent_dir（tests%T/ 的父目录）。
    """
    search_dirs = [
        tests_output_dir,
        os.path.dirname(tests_output_dir),
    ]
    for d in search_dirs:
        cov_files = sorted(glob.glob(os.path.join(d, "*coveragedetail*.csv")))
        if cov_files:
            _parse_coverage_csv(cov_files[-1], diag)
            return

    # 如果还是找不到，也不报错：coverage 字段保持 None 即可


def _parse_coverage_csv(csv_path: str, diag: dict):
    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                tc = _short(row.get("test_class", "").strip())
                if not tc:
                    continue
                entry = _ensure(diag, tc)
                # focal method 行覆盖率（0~100）
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
# 读取已有的 suite_diagnosis.json（给 Refine Agent 用）
# ════════════════════════════════════════════════════════════════════

def load_suite_diagnosis(tests_output_dir: str) -> Dict[str, dict]:
    """
    从 tests_output_dir 读取 suite_diagnosis.json。
    返回 {test_name: diag_dict} 或 {}（文件不存在时）。
    """
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


# ════════════════════════════════════════════════════════════════════
# 目录查找工具
# ════════════════════════════════════════════════════════════════════

def _find_latest_tests_dir(project_dir: str) -> Optional[str]:
    """在 project_dir 下找最新的 tests%YYYYMMDDHHMMSS/ 目录。"""
    try:
        candidates = [
            os.path.join(project_dir, d)
            for d in os.listdir(project_dir)
            if d.startswith("tests%") and os.path.isdir(os.path.join(project_dir, d))
        ]
        return max(candidates, key=os.path.getmtime) if candidates else None
    except Exception:
        return None
