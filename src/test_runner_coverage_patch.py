"""
test_runner_coverage_patch.py
==============================
针对 test_runner.py 中 focal method 覆盖率计算的专项修复补丁。

修复的问题：
  1. "focal method 'xxx'(desc=()) not found" 
     → 无参方法 descriptor "()" 匹配不上 JaCoCo 的 "()I" / "()V" 等
     
  2. "TestRunner failed: duplicate attribute"
     → JaCoCo XML 中存在重复属性导致 ET.parse 失败
     
  3. "TestRunner failed: not well-formed (invalid token)"
     → JaCoCo XML 格式不合法，需要清洗后重试
     
  4. "focal method 'boxBoundary'(desc=None) not found"
     → 私有方法 descriptor 为 None 时，应尝试宽松匹配

使用方式：在 task.py 中：
    import test_runner as _tr_mod
    from test_runner_coverage_patch import patch_all
    patch_all(_tr_mod)
"""
from __future__ import annotations

import re
import os
from typing import Optional
import xml.etree.ElementTree as ET


# ════════════════════════════════════════════════════════════════════
# XML 清洗工具
# ════════════════════════════════════════════════════════════════════

def _clean_xml_for_parse(raw: str) -> str:
    """
    清洗 XML 字符串，解决常见的 JaCoCo XML 解析问题：
    1. duplicate attribute → 保留第一个，删除后续重复的
    2. 非法字符 → 替换
    3. DOCTYPE/ENTITY 声明 → 移除（可能导致 expat 报错）
    """
    # 移除 DOCTYPE 和 ENTITY 声明
    raw = re.sub(r'<!DOCTYPE[^>]*(?:>|\[.*?\]>)', '', raw, flags=re.DOTALL)
    raw = re.sub(r'<!ENTITY[^>]*>', '', raw)

    # 替换 NUL 字节
    raw = raw.replace('\x00', '')

    # 处理 duplicate attribute：扫描每个标签内的属性
    def _dedup_tag_attrs(m):
        full_tag = m.group(0)
        seen = set()
        result = []
        # 拆分：先找标签名
        name_m = re.match(r'<(/?\w[\w:\-]*)', full_tag)
        if not name_m:
            return full_tag
        result.append(name_m.group(0))
        rest = full_tag[name_m.end():]
        # 逐个属性处理
        for attr_m in re.finditer(r'\s+([\w:\-]+)=(?:"[^"]*"|\'[^\']*\')', rest):
            attr_name = attr_m.group(1)
            if attr_name not in seen:
                seen.add(attr_name)
                result.append(attr_m.group(0))
        # 加上结尾
        end_m = re.search(r'\s*/?>$', full_tag)
        if end_m:
            result.append(end_m.group(0))
        return ''.join(result)

    raw = re.sub(r'<[^>]+>', _dedup_tag_attrs, raw)
    return raw


def parse_xml_safe(xml_path: str):
    """
    安全解析 XML 文件，遇到解析错误时进行清洗重试。
    返回 (root_element_or_None, success: bool)
    """
    if not xml_path or not os.path.exists(xml_path):
        return None, False

    try:
        fsize = os.path.getsize(xml_path)
        if fsize < 50:
            return None, False
    except Exception:
        return None, False

    try:
        with open(xml_path, 'r', encoding='utf-8', errors='replace') as f:
            raw = f.read()
    except Exception as e:
        print(f"[WARN] Cannot read {xml_path}: {e}")
        return None, False

    # 截断到 <report
    start = raw.find('<report')
    if start < 0:
        return None, False
    raw = raw[start:]

    # 尝试1：直接解析
    try:
        return ET.fromstring(raw), True
    except ET.ParseError as e1:
        print(f"[WARN] XML parse error ({e1}), cleaning: {os.path.basename(xml_path)}")

    # 尝试2：清洗后解析
    try:
        cleaned = _clean_xml_for_parse(raw)
        return ET.fromstring(cleaned), True
    except ET.ParseError as e2:
        print(f"[WARN] XML still invalid after cleaning ({e2}): {os.path.basename(xml_path)}")
        return None, False


# ════════════════════════════════════════════════════════════════════
# 修复版 _is_focal_method_match
# ════════════════════════════════════════════════════════════════════

def _fixed_is_focal_method_match(
    self_instance,
    method_name: str,
    focal_name: str,
    modified_class_name: str,
    focal_descriptor: Optional[str] = None,
    method_desc: Optional[str] = None,
) -> bool:
    """
    修复版 focal method 匹配，解决以下问题：

    问题1: 无参方法 focal_descriptor="()" 无法匹配 method_desc="()I"
      → 正确提取并比较参数部分

    问题2: focal_descriptor=None（私有方法无法生成 descriptor）时
      → 宽松匹配（仅按方法名），不再报 WARN "not found"

    问题3: 构造函数匹配改进
    """
    if not focal_name:
        return False

    # ── 构造函数 ────────────────────────────────────────────────────
    if method_name == '<init>' and modified_class_name:
        simple = modified_class_name.split('.')[-1].split('$')[0]
        if focal_name in (modified_class_name, simple):
            if focal_descriptor and method_desc:
                fp = _param_part(focal_descriptor)
                mp = _param_part(method_desc)
                return mp == fp
            return True

    if method_name != focal_name:
        return False

    # ── 方法名匹配：根据 descriptor 情况判断 ──────────────────────
    if focal_descriptor is None:
        # 无 descriptor（如私有方法、对象参数方法）→ 宽松匹配所有重载
        return True

    if not method_desc:
        # JaCoCo XML 没有 desc 属性 → 宽松匹配
        return True

    fp = _param_part(focal_descriptor)
    mp = _param_part(method_desc)

    if not fp:
        # descriptor 解析失败 → 宽松匹配
        return True

    # 完整参数部分比较
    if mp == fp:
        return True

    # 前缀匹配（descriptor 不完整时）
    if not focal_descriptor.endswith(')') and method_desc.startswith(focal_descriptor):
        return True

    return False


def _param_part(descriptor: str) -> str:
    """提取 descriptor 的参数部分（括号内，含括号）。"""
    if not descriptor:
        return ''
    op = descriptor.find('(')
    cp = descriptor.find(')')
    if op < 0 or cp < 0:
        return ''
    return descriptor[op:cp + 1]


# ════════════════════════════════════════════════════════════════════
# 修复版 report() → 使用安全 XML 解析
# ════════════════════════════════════════════════════════════════════

def _fixed_run_all_tests_xml_reading(test_runner_class):
    """
    为 TestRunner 的 run_all_tests 方法中涉及 JaCoCo XML 读取的部分打补丁。
    通过替换 ET.parse 为 parse_xml_safe 实现。
    """
    # 将 parse_xml_safe 注入到 test_runner 模块的全局命名空间
    import test_runner as tr_module
    tr_module._parse_xml_safe = parse_xml_safe
    tr_module._fixed_is_focal_method_match = _fixed_is_focal_method_match


# ════════════════════════════════════════════════════════════════════
# 综合补丁入口
# ════════════════════════════════════════════════════════════════════

def patch_all(test_runner_module):
    """
    将所有 focal coverage 修复注入到 test_runner 模块。

    修复点：
    1. TestRunner._is_focal_method_match → 使用修复版
    2. ET.parse → 使用 parse_xml_safe（处理 duplicate attribute 等错误）
    """
    import types

    # ── 补丁1：_is_focal_method_match ────────────────────────────
    test_runner_module.TestRunner._is_focal_method_match = _fixed_is_focal_method_match
    print("[Patch] TestRunner._is_focal_method_match patched (no-arg method + private method fix).",
          flush=True)

    # ── 补丁2：在 run_all_tests 中使用安全 XML 解析 ──────────────
    _patch_xml_parsing(test_runner_module)


def _patch_xml_parsing(test_runner_module):
    """
    替换 test_runner.py 中对 ET.parse / ET.fromstring 的直接调用。
    通过在模块级别注入 parse_xml_safe，并修改 run_all_tests 中的 XML 读取逻辑。
    """
    # 注入安全解析函数到模块命名空间
    test_runner_module._parse_xml_safe_fn = parse_xml_safe

    # 保存原始的 run_all_tests
    original_run_all = test_runner_module.TestRunner.run_all_tests

    def patched_run_all_tests(self, tests_dir, compiled_test_dir,
                               compiler_output, test_output, report_dir, logs=None):
        """
        包装 run_all_tests，在调用前注入修复版 XML 解析。
        """
        # 临时替换 ET.parse 为安全版本
        import xml.etree.ElementTree as ET_orig
        original_parse = ET_orig.parse

        def safe_et_parse(source, parser=None):
            """安全版 ET.parse：处理 duplicate attribute 等问题。"""
            if isinstance(source, str) and os.path.exists(source):
                root, ok = parse_xml_safe(source)
                if ok and root is not None:
                    # 包装为 ElementTree 对象
                    return ET_orig.ElementTree(root)
            # 降级到原始解析
            return original_parse(source, parser)

        ET_orig.parse = safe_et_parse

        try:
            result = original_run_all(
                self, tests_dir, compiled_test_dir,
                compiler_output, test_output, report_dir, logs
            )
        finally:
            # 恢复原始 ET.parse
            ET_orig.parse = original_parse

        return result

    test_runner_module.TestRunner.run_all_tests = patched_run_all_tests
    print("[Patch] TestRunner.run_all_tests XML parsing patched (duplicate attribute fix).",
          flush=True)


# ════════════════════════════════════════════════════════════════════
# 用于 tool_runner_adapter.py 中的安全 XML 读取
# ════════════════════════════════════════════════════════════════════

def safe_parse_jacoco_for_coverage(xml_path: str, target_class: str, focal_name: str,
                                    focal_descriptor: Optional[str] = None) -> dict:
    """
    安全地从 JaCoCo XML 中提取特定类和 focal method 的覆盖率。
    修复：使用安全 XML 解析 + 修复版方法匹配。

    返回：
    {
        'focal_line_rate': float or None,   # 0-100
        'focal_branch_rate': float or None, # 0-100
        'missed_methods': list,
        'partial_methods': list,
    }
    """
    result = {
        'focal_line_rate': None,
        'focal_branch_rate': None,
        'missed_methods': [],
        'partial_methods': [],
    }

    root, ok = parse_xml_safe(xml_path)
    if not ok or root is None:
        return result

    simple = target_class.split('.')[-1].split('$')[0] if target_class else ''
    if not simple:
        return result

    fl_cov = fl_tot = fb_cov = fb_tot = 0
    found_focal = False

    for class_elem in root.findall('.//class'):
        cname = class_elem.get('name', '')
        cname_simple = cname.split('/')[-1].split('$')[0]
        if cname_simple != simple:
            continue

        # Missed / partial methods
        for me in class_elem.findall('method'):
            mn = me.get('name', '')
            mline = me.get('line', '?')
            if mn in ('<clinit>',):
                continue
            display = f"{simple}()" if mn == '<init>' else mn

            lc = lm = bc = bm = 0
            for cc in me.findall('counter'):
                ct = cc.get('type', '')
                if ct == 'LINE':
                    lc = int(cc.get('covered', 0))
                    lm = int(cc.get('missed',  0))
                elif ct == 'BRANCH':
                    bc = int(cc.get('covered', 0))
                    bm = int(cc.get('missed',  0))

            if lc == 0 and lm > 0:
                result['missed_methods'].append(
                    f"line {mline}: {display}() — completely uncovered")
            elif bm > 0:
                result['partial_methods'].append(
                    f"line {mline}: {display}() — {bm}/{bm+bc} branches missed")

        # Focal method coverage
        if focal_name:
            for me in class_elem.findall('method'):
                mn = me.get('name', '')
                md = me.get('desc', '')
                if mn == focal_name:
                    print(f"[DEBUG] 2 Found method name match: {mn}, but desc compare: XML({md}) vs Target({focal_descriptor})")
                if _fixed_is_focal_method_match(
                        None, mn, focal_name, simple, focal_descriptor, md):
                    found_focal = True
                    for cc in me.findall('counter'):
                        ct = cc.get('type', '')
                        cov = int(cc.get('covered', 0))
                        mis = int(cc.get('missed',  0))
                        if ct == 'LINE':
                            fl_cov += cov; fl_tot += cov + mis
                        elif ct == 'BRANCH':
                            fb_cov += cov; fb_tot += cov + mis

    # 如果 descriptor 匹配失败，尝试宽松匹配（忽略 descriptor）
    if focal_name and not found_focal:
        for class_elem in root.findall('.//class'):
            cname = class_elem.get('name', '')
            if cname.split('/')[-1].split('$')[0] != simple:
                continue
            for me in class_elem.findall('method'):
                if me.get('name', '') == focal_name:
                    found_focal = True
                    for cc in me.findall('counter'):
                        ct = cc.get('type', '')
                        cov = int(cc.get('covered', 0))
                        mis = int(cc.get('missed',  0))
                        if ct == 'LINE':
                            fl_cov += cov; fl_tot += cov + mis
                        elif ct == 'BRANCH':
                            fb_cov += cov; fb_tot += cov + mis

    if fl_tot > 0:
        result['focal_line_rate'] = round(100.0 * fl_cov / fl_tot, 2)
    if fb_tot > 0:
        result['focal_branch_rate'] = round(100.0 * fb_cov / fb_tot, 2)

    return result