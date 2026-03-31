"""
test_runner_focal_fix.py  (v3 — focal coverage 修复版)
==========================================================

修复内容（相比 v2）：

问题1修复：多 modified class 场景下测试与被测类的映射错位
  - build_class_name_to_simple_map()
  - resolve_target_class_for_test()

问题3新增修复：focal method 覆盖率计算常见问题
  - 无参方法 descriptor "()" 正确匹配 JaCoCo desc="()I", desc="()V" 等
  - private 方法不在 JaCoCo XML 中（JaCoCo 只记录执行过的字节码，
    private 方法可以出现，但若未被调用则缺失 → 降级为仅按名匹配）
  - duplicate attribute XML 解析失败 → 增加 XML 清洗逻辑
  - not well-formed XML → 增加容错解析

问题4修复（保留）：多个 modified class 的覆盖率计算
问题6修复（保留）：JaCoCo descriptor 匹配失败
"""
from __future__ import annotations

import os
import re
from typing import Dict, List, Optional, Set, Tuple


# ════════════════════════════════════════════════════════════════════
# XML 清洗：处理 duplicate attribute 等解析错误
# ════════════════════════════════════════════════════════════════════

def _clean_jacoco_xml(raw: str) -> str:
    """
    清洗 JaCoCo XML，解决常见的解析错误：
    1. duplicate attribute：同一个元素中重复的属性名（取第一个）
    2. 非法字符：用空格替换
    3. 截断到 <report ...> 开始处
    """
    # 截断到 <report 开始
    start = raw.find('<report')
    if start < 0:
        return raw
    raw = raw[start:]

    # 替换 NUL 字节
    raw = raw.replace('\x00', '')

    # 处理 duplicate attribute：用正则找到重复属性并删除后面出现的
    def _dedup_attrs(m):
        tag_content = m.group(0)
        seen_attrs = set()
        def _attr_replacer(am):
            attr_name = am.group(1)
            if attr_name in seen_attrs:
                return ''   # 删除重复属性
            seen_attrs.add(attr_name)
            return am.group(0)
        return re.sub(r'\s(\w[\w:\-]*)=(?:"[^"]*"|\'[^\']*\')', _attr_replacer, tag_content)

    raw = re.sub(r'<\w[^>]*>', _dedup_attrs, raw)

    return raw


def _parse_jacoco_xml_safe(xml_path: str):
    """
    安全解析 JaCoCo XML，遇到解析错误时尝试清洗后重试。
    返回 (root_element, success_flag)
    """
    import xml.etree.ElementTree as ET

    if not xml_path or not os.path.exists(xml_path):
        return None, False

    # 先检查文件大小
    try:
        size = os.path.getsize(xml_path)
        if size < 100:
            return None, False
    except Exception:
        return None, False

    try:
        with open(xml_path, 'r', encoding='utf-8', errors='replace') as f:
            raw = f.read()
    except Exception as e:
        print(f"[WARN] Cannot read XML {xml_path}: {e}")
        return None, False

    # 尝试1：直接解析
    try:
        start = raw.find('<report')
        if start >= 0:
            root = ET.fromstring(raw[start:])
            return root, True
    except ET.ParseError as e:
        print(f"[WARN] JaCoCo XML parse error ({e}), attempting cleanup: {xml_path}")

    # 尝试2：清洗后解析
    try:
        cleaned = _clean_jacoco_xml(raw)
        root = ET.fromstring(cleaned)
        return root, True
    except ET.ParseError as e:
        print(f"[WARN] JaCoCo XML still invalid after cleanup ({e}): {xml_path}")

    # 尝试3：用 iterparse 容错读取（跳过问题节点）
    try:
        import io
        cleaned = _clean_jacoco_xml(raw)
        # 再次尝试，移除 DOCTYPE 声明（有时会导致问题）
        cleaned = re.sub(r'<!DOCTYPE[^>]*>', '', cleaned)
        cleaned = re.sub(r'<!ENTITY[^>]*>', '', cleaned)
        root = ET.fromstring(cleaned)
        return root, True
    except Exception as e:
        print(f"[WARN] JaCoCo XML all parse attempts failed for {xml_path}: {e}")
        return None, False


# ════════════════════════════════════════════════════════════════════
# 问题6修复：descriptor 生成和匹配
# ════════════════════════════════════════════════════════════════════

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
        return "()"  # 无参方法

    result_parts = []
    for t in param_types:
        t = t.strip()
        base = t
        array_prefix = ''
        while base.endswith('[]'):
            array_prefix += '['
            base = base[:-2].strip()
        if base in _JAVA_PRIMITIVE_MAP:
            result_parts.append(array_prefix + _JAVA_PRIMITIVE_MAP[base])
        else:
            return None  # 含对象类型，无法可靠转换
    return '(' + ''.join(result_parts)


def is_focal_method_match_fixed(
    method_name: str,
    focal_name: str,
    modified_class_name: str,
    focal_descriptor: Optional[str] = None,
    method_desc: Optional[str] = None,
) -> bool:
    """
    修复版 focal method 匹配：

    1. 无参方法 descriptor="()" 正确匹配 desc="()I", "()V", "()[D" 等
    2. 构造函数识别
    3. 有 descriptor 时精确匹配参数部分，无时按名匹配所有重载
    4. 新增：私有方法的特殊处理
       - JaCoCo 会记录被调用的私有方法，但可能使用合成桥接方法名
       - 当 focal_descriptor 为 None 时，允许宽松匹配
    """
    if not focal_name:
        return False

    # ── 构造函数识别 ──────────────────────────────────────────────
    if method_name == '<init>' and modified_class_name:
        simple_class = modified_class_name.split('.')[-1].split('$')[0]
        if focal_name in (modified_class_name, simple_class):
            if focal_descriptor and method_desc:
                method_params = _extract_param_part(method_desc)
                focal_params  = _extract_param_part(focal_descriptor)
                return method_params == focal_params
            return True

    if method_name != focal_name:
        return False

    # ── 方法名匹配后验证 descriptor ──────────────────────────────
    if focal_descriptor and method_desc:
        focal_params  = _extract_param_part(focal_descriptor)
        method_params = _extract_param_part(method_desc)

        if focal_params == '()':
            # 无参方法：只要参数部分相同（即空括号）就匹配
            return method_params == '()'

        if focal_params:
            # 有参方法：参数部分完全匹配
            if method_params == focal_params:
                return True
            # 前缀匹配（descriptor 不完整时）
            if focal_params.endswith(')'):
                return method_params == focal_params
            return method_desc.startswith(focal_params)

    # 无 descriptor：按名匹配所有重载
    return True


def _extract_param_part(descriptor: str) -> str:
    """
    从 JVM descriptor 中提取参数部分（括号内，包含括号）。
    例：
      "(ILjava/lang/String;)V" → "(ILjava/lang/String;)"
      "()"                    → "()"
      "()I"                   → "()"
    """
    if not descriptor:
        return ''
    open_p = descriptor.find('(')
    close_p = descriptor.find(')')
    if open_p < 0 or close_p < 0:
        return descriptor
    return descriptor[open_p:close_p + 1]


# ════════════════════════════════════════════════════════════════════
# 问题1修复（新增）：测试类名 → 正确的 modified class 映射
# ════════════════════════════════════════════════════════════════════

def build_class_name_to_simple_map(project_dir: str) -> Dict[str, str]:
    all_classes = resolve_all_target_classes(project_dir)
    return {cls.lower(): cls for cls in all_classes}


def resolve_target_class_for_test(
    test_class_name: str,
    all_modified_classes: List[str],
    fallback: str = "",
) -> str:
    """
    根据测试类名前缀，推断该测试对应的 modified class。
    命名约定：<ClassName>_<method_id>_<seq>Test
    """
    if not all_modified_classes:
        return fallback
    if len(all_modified_classes) == 1:
        return all_modified_classes[0]

    name = test_class_name
    if name.endswith('.java'):
        name = name[:-5]
    if name.endswith('Test'):
        name = name[:-4]

    parts = name.split('_')
    lower_map = {cls.lower(): cls for cls in all_modified_classes}

    for strip_count in range(1, min(4, len(parts))):
        prefix = '_'.join(parts[:len(parts) - strip_count])
        if not prefix:
            continue
        if prefix.lower() in lower_map:
            return lower_map[prefix.lower()]

    if len(parts) >= 3:
        class_prefix = '_'.join(parts[:-2])
    elif len(parts) >= 2:
        class_prefix = parts[0]
    else:
        class_prefix = name

    class_prefix_lower = class_prefix.lower()
    if class_prefix_lower in lower_map:
        return lower_map[class_prefix_lower]

    for cls_lower, cls in lower_map.items():
        if class_prefix_lower == cls_lower or class_prefix_lower.startswith(cls_lower + '_'):
            return cls

    for cls_lower, cls in lower_map.items():
        if cls_lower in class_prefix_lower:
            return cls

    return fallback if fallback else (all_modified_classes[0] if all_modified_classes else "")


# ════════════════════════════════════════════════════════════════════
# 问题4修复：多个 modified class 支持
# ════════════════════════════════════════════════════════════════════

def resolve_all_target_classes(project_dir: str) -> List[str]:
    """返回项目的所有 modified class 简单类名列表。"""
    classes = []

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

    return classes


def resolve_target_class_primary(project_dir: str) -> str:
    classes = resolve_all_target_classes(project_dir)
    return classes[0] if classes else ''


# ════════════════════════════════════════════════════════════════════
# 覆盖率计算（修复版）：支持安全 XML 解析 + 更好的方法匹配
# ════════════════════════════════════════════════════════════════════

def compute_coverage_for_all_classes(
    jacoco_xml_path: str,
    target_classes: List[str],
    focal_name: str = "",
    focal_descriptor: Optional[str] = None,
) -> Dict[str, dict]:
    """
    从 JaCoCo XML 中提取所有 modified class 的覆盖率数据。
    修复：使用安全 XML 解析 + 修复版方法匹配。
    """
    result = {}
    if not jacoco_xml_path or not os.path.exists(jacoco_xml_path):
        return result

    root, ok = _parse_jacoco_xml_safe(jacoco_xml_path)
    if not ok or root is None:
        return result

    for target_class in target_classes:
        simple = target_class.split('.')[-1].split('$')[0]
        class_data = {
            'm_line_cov': 0, 'm_line_total': 0,
            'm_branch_cov': 0, 'm_branch_total': 0,
            'f_line_cov': 0, 'f_line_total': 0,
            'f_branch_cov': 0, 'f_branch_total': 0,
        }

        found_focal = False
        for class_elem in root.findall('.//class'):
            cname = class_elem.get('name', '')
            cname_simple = cname.split('/')[-1].split('$')[0]
            if cname_simple != simple:
                continue

            # Class-level coverage
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
                    if mn == focal_name:
                        print(f"[DEBUG] Found method name match: {mn}, but desc compare: XML({md}) vs Target({focal_descriptor})")
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