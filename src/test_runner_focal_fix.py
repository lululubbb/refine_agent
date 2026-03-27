"""
test_runner_focal_fix.py
========================
修复 test_runner.py 中两个核心问题的补丁模块：

问题6修复：JaCoCo descriptor 匹配失败
  原因：`_safe_params_to_descriptor` 遇到对象类型（如 `double[][]`）返回 None，
        但 `double[][]` 是基本类型数组，应该能生成 descriptor。
  
  具体问题：`estimateError(desc=([[D[D[DD)` 中：
    - `[[D` = double[][]
    - `[D`  = double[]
    - `D`   = double
    这些全是基本类型，但代码中 `double[][]` 的解析路径有 bug：
    先 strip `[]` 变 `double`，是基本类型，OK。
    但原始参数字符串 `[[D[D[DD` 是 JVM descriptor 格式，
    而 raw_data JSON 里存的是 Java 格式 `double[][], double[], double, double`
    
  另一个问题：`getOrder()` 是无参方法，descriptor=`()`，
  JaCoCo XML 中 `desc="()I"` 或 `desc="()V"`，
  startswith("()") 是 True，但代码生成的 descriptor 是 "(" 而非 "()"

问题4修复：多个 modified class 的覆盖率计算
  原因：`_resolve_target_class` 只返回第一个 modified class，
       `modified_classes.src` 中可能有多个类。
"""
from __future__ import annotations

import os
import re
from typing import Dict, List, Optional, Set, Tuple


# ════════════════════════════════════════════════════════════════════
# 问题6修复：descriptor 生成和匹配
# ════════════════════════════════════════════════════════════════════

# 扩展基本类型映射（包含数组维度支持）
_JAVA_PRIMITIVE_MAP = {
    'int': 'I', 'long': 'J', 'double': 'D', 'float': 'F',
    'boolean': 'Z', 'byte': 'B', 'char': 'C', 'short': 'S',
    'void': 'V',
}


def safe_params_to_descriptor_fixed(param_types: list) -> Optional[str]:
    """
    修复版 _safe_params_to_descriptor：
    
    1. 正确处理多维基本类型数组（如 double[][], int[]）
    2. 无参数方法返回 "()" 而非 None
    3. 对象类型仍返回 None（无法确定包名）
    """
    if not param_types:
        return "()"  # ★ 修复：无参方法返回 "()" 而非 None

    result_parts = []
    for t in param_types:
        t = t.strip()
        # 剥离数组维度
        base = t
        array_prefix = ''
        while base.endswith('[]'):
            array_prefix += '['
            base = base[:-2].strip()
        if base in _JAVA_PRIMITIVE_MAP:
            result_parts.append(array_prefix + _JAVA_PRIMITIVE_MAP[base])
        else:
            # 含对象类型，无法可靠转换
            return None
    return '(' + ''.join(result_parts)


def is_focal_method_match_fixed(
    method_name: str,
    focal_name: str,
    modified_class_name: str,
    focal_descriptor: Optional[str] = None,
    method_desc: Optional[str] = None,
) -> bool:
    """
    修复版 _is_focal_method_match：
    
    1. 无参方法 descriptor="()" 能正确匹配 JaCoCo 的 desc="()I", desc="()V" 等
    2. 构造函数识别逻辑保持不变
    """
    if not focal_name:
        return False

    # 构造函数识别
    if method_name == '<init>' and modified_class_name:
        simple_class = modified_class_name.split('.')[-1].split('$')[0]
        if focal_name in (modified_class_name, simple_class):
            if focal_descriptor and method_desc:
                # focal_descriptor 可能是 "()" 或 "(I" 等参数前缀
                # 需要只匹配参数部分，不匹配返回值
                method_params = method_desc[:method_desc.find(')') + 1] if ')' in method_desc else method_desc
                focal_params  = focal_descriptor if focal_descriptor.endswith(')') else focal_descriptor
                if focal_params.endswith(')'):
                    return method_params == focal_params
                return method_params.startswith(focal_params)
            return True

    if method_name != focal_name:
        return False

    # 方法名匹配时，验证 descriptor
    if focal_descriptor and method_desc:
        # 提取 JaCoCo desc 的参数部分（括号内）
        if focal_descriptor.endswith(')'):
            # 完整参数 descriptor，如 "()" "(I)" "([[D[D[DD)"
            method_params = method_desc[:method_desc.find(')') + 1] if ')' in method_desc else method_desc
            return method_params == focal_descriptor
        else:
            # 前缀匹配（不完整时）
            return method_desc.startswith(focal_descriptor)

    return True


# ════════════════════════════════════════════════════════════════════
# 问题4修复：多个 modified class 支持
# ════════════════════════════════════════════════════════════════════

def resolve_all_target_classes(project_dir: str) -> List[str]:
    """
    返回项目的所有 modified class 简单类名列表（不只是第一个）。
    
    数据来源（优先级递减）：
    1. modified_classes.src（每行一个全限定类名）
    2. defects4j.build.properties 的 d4j.classes.modified
    3. test_cases 文件名推断（退化为单个类）
    """
    classes = []

    # 优先1: modified_classes.src
    meta_file = os.path.join(project_dir, 'modified_classes.src')
    if os.path.exists(meta_file):
        try:
            with open(meta_file) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        simple = line.split('.')[-1]
                        if simple and simple not in classes:
                            classes.append(simple)
            if classes:
                return classes
        except Exception:
            pass

    # 优先2: defects4j.build.properties
    prop_file = os.path.join(project_dir, 'defects4j.build.properties')
    if os.path.exists(prop_file):
        try:
            with open(prop_file) as f:
                for line in f:
                    if 'd4j.classes.modified' in line and '=' in line:
                        val = line.split('=', 1)[1].strip()
                        for cls in val.split(','):
                            cls = cls.strip()
                            if cls:
                                simple = cls.split('.')[-1]
                                if simple and simple not in classes:
                                    classes.append(simple)
            if classes:
                return classes
        except Exception:
            pass

    return classes  # 可能为空，调用方需要回退到旧逻辑


def resolve_target_class_primary(project_dir: str) -> str:
    """返回主要的 target class（向后兼容，返回第一个）。"""
    classes = resolve_all_target_classes(project_dir)
    return classes[0] if classes else ''


# ════════════════════════════════════════════════════════════════════
# Bug Revealing 中 modified class 的作用说明
# ════════════════════════════════════════════════════════════════════

"""
关于 Bug Revealing 为何需要 modified_class：

bug_revealing.py 在整个项目中运行测试，会得到所有测试的通过/失败结果。
但 bug_revealing 的核心判断是：某个测试在 buggy 版本 FAIL，在 fixed 版本 PASS。
这个判断与 modified_class 无关——只要测试在两个版本上行为不同，就是 bug-revealing。

然而，test_runner.py 中的 "target_class" 主要用于：
1. 覆盖率计算：只统计 target_class 的行/分支覆盖率
2. 诊断报告：diagnosis.log 中记录 target_class
3. CSV 文件命名：`{project}_{targetClass}_coveragedetail.csv`

因此，多个 modified class 的影响主要在覆盖率计算上，而非 bug_revealing 本身。

修复方案：当有多个 modified class 时，分别计算每个 class 的覆盖率，
然后取加权平均（或分别报告）。
"""


# ════════════════════════════════════════════════════════════════════
# 覆盖率计算：多个 modified class 的聚合
# ════════════════════════════════════════════════════════════════════

def compute_coverage_for_all_classes(
    jacoco_xml_path: str,
    target_classes: List[str],
    focal_name: str = "",
    focal_descriptor: Optional[str] = None,
) -> Dict[str, dict]:
    """
    从 JaCoCo XML 中提取所有 modified class 的覆盖率数据。
    
    Returns:
        {class_name: {
            'm_line_cov': int, 'm_line_total': int,
            'f_line_cov': int, 'f_line_total': int,
            'f_branch_cov': int, 'f_branch_total': int,
        }}
    """
    import xml.etree.ElementTree as ET

    result = {}
    if not jacoco_xml_path or not os.path.exists(jacoco_xml_path):
        return result

    try:
        with open(jacoco_xml_path, 'r', encoding='utf-8', errors='replace') as f:
            raw = f.read()
        _start = raw.find('<report')
        if _start < 0:
            return result
        root = ET.fromstring(raw[_start:])
    except Exception:
        return result

    for target_class in target_classes:
        simple = target_class.split('.')[-1].split('$')[0]
        class_data = {
            'm_line_cov': 0, 'm_line_total': 0,
            'm_branch_cov': 0, 'm_branch_total': 0,
            'f_line_cov': 0, 'f_line_total': 0,
            'f_branch_cov': 0, 'f_branch_total': 0,
        }

        for class_elem in root.findall('.//class'):
            cname = class_elem.get('name', '')
            cname_simple = cname.split('/')[-1].split('$')[0]
            if cname_simple != simple and not cname.endswith('/' + simple):
                continue

            # Class-level coverage (modified class)
            for c in class_elem.findall('counter'):
                ctype = c.get('type', '')
                cov = int(c.get('covered', 0))
                mis = int(c.get('missed', 0))
                if ctype == 'LINE':
                    class_data['m_line_cov']   += cov
                    class_data['m_line_total'] += cov + mis
                elif ctype == 'BRANCH':
                    class_data['m_branch_cov']   += cov
                    class_data['m_branch_total'] += cov + mis

            # Focal method coverage
            if focal_name:
                for me in class_elem.findall('method'):
                    mn = me.get('name', '')
                    md = me.get('desc', '')
                    if is_focal_method_match_fixed(mn, focal_name, simple,
                                                   focal_descriptor, md):
                        for cc in me.findall('counter'):
                            ct = cc.get('type', '')
                            cov = int(cc.get('covered', 0))
                            mis = int(cc.get('missed', 0))
                            if ct == 'LINE':
                                class_data['f_line_cov']   += cov
                                class_data['f_line_total'] += cov + mis
                            elif ct == 'BRANCH':
                                class_data['f_branch_cov']   += cov
                                class_data['f_branch_total'] += cov + mis

            result[simple] = class_data
            break  # 找到该类后不再继续

    return result


def aggregate_coverage(coverage_by_class: Dict[str, dict]) -> dict:
    """
    将多个 class 的覆盖率数据聚合为单一指标（用于向后兼容）。
    """
    if not coverage_by_class:
        return {}

    totals = {
        'm_line_cov': 0, 'm_line_total': 0,
        'm_branch_cov': 0, 'm_branch_total': 0,
        'f_line_cov': 0, 'f_line_total': 0,
        'f_branch_cov': 0, 'f_branch_total': 0,
    }
    for class_data in coverage_by_class.values():
        for k in totals:
            totals[k] += class_data.get(k, 0)

    return totals