"""
test_runner.py  — patched version
主要修复：
  Bug-Coverage-1: per_class_coverage 统计时只匹配外部类 (PolygonsSet)，
                  忽略了内部类 (PolygonsSet$Edge 等)，导致行数远小于
                  focal method 所在的实际类行数。
                  修复：对所有 name.split('$')[0] == simple 的 <class> 元素求和。

  Bug-Coverage-2: 与 Bug-Coverage-1 同根因 —— _resolve_target_class 返回的
                  简单类名与 JaCoCo XML 中的类名匹配逻辑不一致。
                  统一改用 _jacoco_class_matches() 辅助函数做匹配。

新增：
  - 在 generate_one_test / build_fix_messages 调用前加入 Rule-based Validator。
  - validate_before_write() 在写入 test_cases/ 前做快速检查，记录到日志。
"""
# ── 本文件只包含差异补丁（patch），在 askGPT_refine.py 中通过 monkeypatch 注入 ──
# 也可以直接替换 test_runner.py 中的对应方法。
# 以下是独立可运行的补丁函数，直接 import 即可使用。

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
    """
    判断 JaCoCo XML 中的 <class name="org/foo/Bar$Inner"> 是否属于
    target_simple（如 "Bar"）。

    规则：
      1. 取 jacoco_class_name 的最后一段（去掉包名）
      2. 再去掉 $ 及其后面的内部类名
      3. 与 target_simple 做精确匹配
    
    例：
      "org/apache/commons/math3/geometry/euclidean/twod/PolygonsSet$Edge"
        → 外部类简单名 = "PolygonsSet" ✓
      "org/apache/commons/math3/geometry/euclidean/twod/PolygonsSet"
        → 外部类简单名 = "PolygonsSet" ✓
      "org/apache/commons/csv/CSVRecord"
        → 外部类简单名 = "CSVRecord" ✓
    """
    if not jacoco_class_name or not target_simple:
        return False
    # 取最后一段（去包名）
    last_segment = jacoco_class_name.split('/')[-1]
    # 取外部类名（去掉 $ 及内部类部分）
    outer_class = last_segment.split('$')[0]
    return outer_class == target_simple


def _sum_class_coverage_from_xml(
    root_elem: ET.Element,
    target_simple: str,
) -> Dict[str, int]:
    """
    从 JaCoCo XML 的根元素中，汇总 target_simple 类（含所有内部类）
    的 LINE 和 BRANCH 覆盖数据。

    返回：
      {
        'line_cov': int, 'line_total': int,
        'branch_cov': int, 'branch_total': int,
      }
    """
    totals = dict(line_cov=0, line_total=0, branch_cov=0, branch_total=0)

    for class_elem in root_elem.findall('.//class'):
        cname = class_elem.get('name', '')
        if not _jacoco_class_matches(cname, target_simple):
            continue
        # 读取该 <class> 下的 <counter> 元素（class 级别）
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
    """
    Bug-Coverage-1 修复版：正确汇总含内部类的覆盖率。

    返回：
      { simple_class_name: { line_cov, line_total, line_rate,
                              branch_cov, branch_total, branch_rate } }
    """
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
# Rule-based Validator 集成
# ════════════════════════════════════════════════════════════════════

def validate_before_write(
    java_source: str,
    tc_name: str,
    log_path: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    在将 Java 代码写入 test_cases/ 之前调用 Rule-based Validator。

    Returns
    -------
    (has_critical_errors: bool, prompt_text: str)
        has_critical_errors: True 表示存在会导致编译失败的错误
        prompt_text: 可注入 LLM prompt 的问题描述（空字符串 = 无问题）
    """
    try:
        from java_syntax_validator import validate_java
        result = validate_java(java_source)

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
                    f"  ⚠️  [Validator] {tc_name}: {result.error_count} error(s) detected before write",
                    flush=True
                )
                for iss in result.issues:
                    if iss.severity == 'error':
                        print(f"     [{iss.rule_id}] {iss.message}", flush=True)

            return result.error_count > 0, prompt_text

        return False, ""

    except ImportError:
        # java_syntax_validator 未安装时静默跳过
        return False, ""
    except Exception as e:
        print(f"  [Validator] warning: validation failed for {tc_name}: {e}", flush=True)
        return False, ""


# ════════════════════════════════════════════════════════════════════
# 补丁注入函数：修复 run_all_tests 中 per_class_coverage 的计算
# ════════════════════════════════════════════════════════════════════

def patch_test_runner_coverage(test_runner_module):
    """
    将 Bug-Coverage-1/2 修复注入到已导入的 test_runner 模块。

    用法（在 run_tests.py 或 task.py 中）：
        import test_runner as _tr_mod
        from test_runner_patch import patch_test_runner_coverage
        patch_test_runner_coverage(_tr_mod)
    """
    # 替换 TestRunner 中用于计算类级覆盖率的逻辑
    # 由于 run_all_tests 是一个大方法，我们通过 monkeypatch 替换辅助函数
    original_run_all = test_runner_module.TestRunner.run_all_tests

    def patched_run_all_tests(self, tests_dir, compiled_test_dir,
                              compiler_output, test_output, report_dir, logs=None):
        # 调用原始方法
        result = original_run_all(
            self, tests_dir, compiled_test_dir,
            compiler_output, test_output, report_dir, logs
        )
        # 在原始方法完成后，重新计算 per_class_coverage 并更新 CSV
        _recompute_coverage_csv(self, tests_dir, logs)
        return result

    test_runner_module.TestRunner.run_all_tests = patched_run_all_tests
    print("[Patch] test_runner.TestRunner.run_all_tests patched for coverage fix.", flush=True)


def _recompute_coverage_csv(runner_instance, tests_dir: str, logs=None):
    """
    在 run_all_tests 完成后，重新用修复版函数计算 per_class_coverage，
    并将结果追加到 execution_stats.log。
    """
    from test_runner_focal_fix import resolve_all_target_classes

    project_dir   = runner_instance.target_path
    project_name  = os.path.basename(project_dir.rstrip('/'))
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