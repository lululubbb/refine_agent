"""
test_runner_diagnosis_patch.py
================================
在 test_runner.py 的 run_all_tests() 方法完成后，
确保 diagnosis.log 中为每个已编译的测试用例写入诊断条目。

使用场景：
  当 test_runner.py 的原始诊断写入因为 target_class 为空、
  JaCoCo XML 不存在等原因静默失败时，此补丁确保至少写入
  compile/exec 状态条目，让 tool_runner_adapter 能解析出正确结果。

集成方式：在 tool_runner_adapter.run_and_export() 中，TestRunner 运行完毕后
调用 ensure_diagnosis_log(tests_output_dir, per_test_status_map)。
但由于 per_test_status_map 在 test_runner 内部，这里提供独立的扫描方案：
通过读取 *_status.csv 重建 diagnosis.log 缺失的条目。
"""
from __future__ import annotations

import csv
import glob
import logging
import os
import re
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def ensure_diagnosis_log(tests_output_dir: str):
    """
    ★ Bug 4 修复补充：
    扫描 tests_output_dir 下的 *_status.csv，
    对于 diagnosis.log 中缺失的测试用例条目，补写基本的 [DIAGNOSIS] 块。

    这样即使 test_runner.py 的原有诊断写入失败，
    tool_runner_adapter 也能从 diagnosis.log 解析出正确的 compile/exec 状态。

    此函数在 run_and_export() 中 TestRunner 完成后、_build_diag_map() 之前调用。
    """
    logs_dir  = os.path.join(tests_output_dir, "logs")
    diag_path = os.path.join(logs_dir, "diagnosis.log")

    # 若 logs/ 不存在，先创建
    os.makedirs(logs_dir, exist_ok=True)

    # 读取已有 diagnosis.log 中记录的 test_class 集合
    existing_tcs: set = set()
    if os.path.exists(diag_path):
        try:
            with open(diag_path, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    m = re.match(r'\s*test_class=(.+)', line.strip())
                    if m:
                        tc = m.group(1).strip().rsplit(".", 1)[-1]
                        existing_tcs.add(tc)
        except Exception as e:
            logger.debug("reading existing diagnosis.log: %s", e)

    # 从 *_status.csv 获取所有测试状态
    status_rows = _read_status_rows(tests_output_dir)
    if not status_rows:
        # logger.debug("[DiagPatch] no status rows found, skip patching")
        return

    new_entries = 0
    with open(diag_path, "a", encoding="utf-8") as df:
        for row in status_rows:
            full_name = row.get("test_class", "").strip()
            if not full_name:
                continue
            tc_short = full_name.rsplit(".", 1)[-1]

            # 已有诊断条目，跳过
            if tc_short in existing_tcs:
                continue

            cs = row.get("compile_status", "unknown").lower().strip()
            es = row.get("exec_status",    "unknown").lower().strip()
            is_timeout = str(row.get("exec_timeout", "false")).lower() in ("true", "1")

            # 推断 status 值
            if cs == "fail":
                status_str = "compile_fail"
                error_type = "compile_error"
                core_error = "Compilation failed (details unavailable in diagnosis patch)"
            elif es == "timeout" or (is_timeout and es == "fail"):
                status_str = "exec_timeout"
                error_type = "timeout"
                core_error = "Exceeded TIMEOUT limit"
            elif es == "fail":
                status_str = "exec_fail"
                error_type = "runtime_error"
                core_error = "Runtime error (details unavailable in diagnosis patch)"
            else:
                status_str = "exec_ok"
                error_type = "coverage_gap"
                core_error = None

            df.write(f"\n[DIAGNOSIS] test_class={full_name}\n")
            df.write(f"  status={status_str}\n")
            df.write(f"  error_type={error_type}\n")
            if core_error:
                df.write(f"  core_errors (1):\n")
                df.write(f"    - {core_error}\n")
            else:
                df.write(f"  missed_methods:\n")
                df.write(f"  partial_methods:\n")
            df.write("---\n")
            existing_tcs.add(tc_short)
            new_entries += 1

    if new_entries > 0:
        logger.info("[DiagPatch] patched %d missing entries into %s", new_entries, diag_path)


def _read_status_rows(tests_output_dir: str) -> list:
    """读取 tests_output_dir 及其父目录下的 *_status*.csv，返回所有行。"""
    rows = []
    search_dirs = [tests_output_dir, os.path.dirname(tests_output_dir)]
    for d in search_dirs:
        if not os.path.isdir(d):
            continue
        for csv_path in sorted(glob.glob(os.path.join(d, "*_status*.csv"))):
            try:
                with open(csv_path, newline="", encoding="utf-8") as f:
                    rows.extend(list(csv.DictReader(f)))
                if rows:
                    return rows
            except Exception as e:
                logger.debug("reading %s: %s", csv_path, e)
    return rows