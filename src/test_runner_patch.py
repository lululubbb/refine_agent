"""
test_runner_patch.py  (v2 — 验证器真正集成版)
=============================================

修复：
  1. validate_before_write() 增加 focal_class_context 参数，
     传入上下文以启用动态规则（R-05/R-08）

  2. 修复主要集成问题：
     旧版 validate_before_write 定义了但从未在 askGPT_refine.py 中被调用。
     本版提供清晰的集成接口，并在 patch_test_runner_coverage 中
     同时把验证工具函数注入到 askGPT_refine 模块。
"""
from __future__ import annotations

import csv
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from config import JACOCO_CLI, TIMEOUT, test_number, dataset_dir, JACOCO_AGENT
from scoring_ablation import global_ablation_config, compute_final_score_ablation


# ════════════════════════════════════════════════════════════════════
# Bug-Coverage-1/2 修复：统一的 JaCoCo class 匹配函数
# ════════════════════════════════════════════════════════════════════

def _jacoco_class_matches(jacoco_class_name: str, target_simple: str) -> bool:
    if not jacoco_class_name or not target_simple:
        return False
    last_segment = jacoco_class_name.split('/')[-1]
    outer_class = last_segment.split('$')[0]
    return outer_class == target_simple


def _sum_class_coverage_from_xml(
    root_elem: ET.Element,
    target_simple: str,
) -> Dict[str, int]:
    totals = dict(line_cov=0, line_total=0, branch_cov=0, branch_total=0)
    for class_elem in root_elem.findall('.//class'):
        cname = class_elem.get('name', '')
        if not _jacoco_class_matches(cname, target_simple):
            continue
        for counter in class_elem.findall('counter'):
            ctype   = counter.get('type', '')
            covered = int(counter.get('covered', 0))
            missed  = int(counter.get('missed', 0))
            if ctype == 'LINE':
                totals['line_cov']   += covered
                totals['line_total'] += covered + missed
            elif ctype == 'BRANCH':
                totals['branch_cov']   += covered
                totals['branch_total'] += covered + missed
    return totals


def _compute_per_class_coverage_fixed(
    jacoco_xml_path: str,
    all_target_classes: List[str],
) -> Dict[str, dict]:
    result: Dict[str, dict] = {}
    if not jacoco_xml_path or not os.path.exists(jacoco_xml_path):
        return result
    try:
        with open(jacoco_xml_path, 'r', encoding='utf-8', errors='replace') as f:
            raw = f.read()
        start = raw.find('<report')
        if start < 0:
            return result
        root = ET.fromstring(raw[start:])
    except Exception as e:
        print(f"[WARN] _compute_per_class_coverage_fixed: XML parse failed: {e}")
        return result

    for tc in all_target_classes:
        simple = tc.split('.')[-1].split('$')[0]
        totals = _sum_class_coverage_from_xml(root, simple)
        lt = totals['line_total']
        bt = totals['branch_total']
        result[simple] = {
            'line_cov':    totals['line_cov'],
            'line_total':  lt,
            'line_rate':   round(100.0 * totals['line_cov'] / lt, 2) if lt else 0.0,
            'branch_cov':  totals['branch_cov'],
            'branch_total': bt,
            'branch_rate': round(100.0 * totals['branch_cov'] / bt, 2) if bt else 0.0,
        }
    return result


# ════════════════════════════════════════════════════════════════════
# Rule-based Validator 集成（v2 — 传入上下文的版本）
# ════════════════════════════════════════════════════════════════════

def validate_before_write(
    java_source: str,
    tc_name: str,
    log_path: Optional[str] = None,
    focal_class_context: str = "",    # ★ 新增：传入上下文以启用动态规则
) -> Tuple[bool, str]:
    """
    在将 Java 代码写入 test_cases/ 之前调用 Rule-based Validator。

    Parameters
    ----------
    java_source          : 待检查的 Java 源码
    tc_name              : 测试类名（用于日志）
    log_path             : 可选的日志文件路径
    focal_class_context  : focal class 的信息字段（d1 information 或 d3 full_fm），
                           传入后启用动态 R-05/R-08 规则

    Returns
    -------
    (has_critical_errors: bool, prompt_text: str)
    """
    try:
        from java_syntax_validator import validate_java
        result = validate_java(
            java_source,
            focal_class_context=focal_class_context
        )

        if not result.is_valid or result.warning_count > 0:
            prompt_text = result.to_prompt_text(max_issues=5)

            if log_path:
                try:
                    os.makedirs(os.path.dirname(log_path), exist_ok=True)
                    with open(log_path, 'a', encoding='utf-8') as f:
                        f.write(f"\n[VALIDATOR] {tc_name}: {result.summary()}\n")
                        for issue in result.issues:
                            f.write(f"  {issue}\n")
                except Exception:
                    pass

            if result.error_count > 0:
                print(
                    f"  ⚠️  [Validator] {tc_name}: {result.error_count} error(s) detected",
                    flush=True
                )
                for iss in result.issues:
                    if iss.severity == 'error':
                        print(f"     [{iss.rule_id}] {iss.message}", flush=True)

            return result.error_count > 0, prompt_text

        return False, ""

    except ImportError:
        return False, ""
    except Exception as e:
        print(f"  [Validator] warning: validation failed for {tc_name}: {e}", flush=True)
        return False, ""


# ════════════════════════════════════════════════════════════════════
# 补丁注入函数
# ════════════════════════════════════════════════════════════════════

def patch_test_runner_coverage(test_runner_module):
    """
    将 Bug-Coverage-1/2 修复注入到已导入的 test_runner 模块。
    同时注入验证工具函数，供 askGPT_refine 调用。
    """
    original_run_all = test_runner_module.TestRunner.run_all_tests

    def patched_run_all_tests(self, tests_dir, compiled_test_dir,
                              compiler_output, test_output, report_dir, logs=None):
        result = original_run_all(
            self, tests_dir, compiled_test_dir,
            compiler_output, test_output, report_dir, logs
        )
        _recompute_coverage_csv(self, tests_dir, logs)
        return result

    test_runner_module.TestRunner.run_all_tests = patched_run_all_tests

    # ★ 注入验证函数到模块命名空间，供 askGPT_refine 等直接调用
    test_runner_module._validate_before_write = validate_before_write

    print("[Patch] test_runner.TestRunner.run_all_tests patched for coverage fix.", flush=True)


def _recompute_coverage_csv(runner_instance, tests_dir: str, logs=None):
    from test_runner_focal_fix import resolve_all_target_classes

    project_dir   = runner_instance.target_path
    all_tcs       = resolve_all_target_classes(project_dir)
    if not all_tcs:
        return

    jacoco_xml = os.path.join(project_dir, 'target', 'site', 'jacoco', 'jacoco.xml')
    if not os.path.exists(jacoco_xml):
        return

    per_class = _compute_per_class_coverage_fixed(jacoco_xml, all_tcs)

    print("\n[PatchedCoverage] 修复后的 target_class 覆盖率（含内部类）:", flush=True)
    for cls_name, stats in per_class.items():
        print(
            f"  {cls_name}: "
            f"行={stats['line_rate']}% ({stats['line_cov']}/{stats['line_total']}), "
            f"分支={stats['branch_rate']}% ({stats['branch_cov']}/{stats['branch_total']})",
            flush=True
        )

    if logs and 'execution_stats' in logs:
        try:
            with open(logs['execution_stats'], 'a') as f:
                f.write("\n[PATCHED_COVERAGE] 修复后 target_class 覆盖率（含内部类）:\n")
                for cls_name, stats in per_class.items():
                    f.write(
                        f"  {cls_name}: "
                        f"行={stats['line_rate']}% ({stats['line_cov']}/{stats['line_total']}), "
                        f"分支={stats['branch_rate']}% ({stats['branch_cov']}/{stats['branch_total']})\n"
                    )
        except Exception:
            pass