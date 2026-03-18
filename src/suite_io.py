"""
suite_io.py
===========
Suite 级别 I/O。

test_cases/ 文件命名约定（与 ChatUniTest 完全相同）：
  <ClassName>_<method_id>_<test_num>Test.java
  e.g.  Token_1_1Test.java  (class=Token, mid=1, seq=1)

对应的 Java 类名：Token_1_1Test
"""
from __future__ import annotations

import os
import re
from typing import Dict, List, Optional, Tuple


# ── 命名工具 ───────────────────────────────────────────────────────────

def tc_filename(class_name: str, method_id, seq: int) -> str:
    return f"{class_name}_{method_id}_{seq}Test.java"


def tc_class_name(class_name: str, method_id, seq: int) -> str:
    return f"{class_name}_{method_id}_{seq}Test"


# ── @Test 方法解析 ─────────────────────────────────────────────────────

def extract_test_methods(java_source: str) -> Dict[str, str]:
    """
    从 Java 源码中提取所有 @Test 方法。
    返回 {method_name: complete_method_source_including_annotation}
    """
    result: Dict[str, str] = {}
    lines = java_source.splitlines(keepends=True)
    i = 0
    while i < len(lines):
        if "@Test" not in lines[i]:
            i += 1
            continue
        ann_start = i
        # 找到方法签名行
        sig_pat = re.compile(r'(?:public|private|protected)?\s*(?:static\s+)?void\s+(\w+)\s*\(')
        while i < len(lines) and not sig_pat.search(lines[i]):
            i += 1
        if i >= len(lines):
            break
        m = sig_pat.search(lines[i])
        if not m:
            i += 1
            continue
        method_name = m.group(1)
        # 收集方法体
        depth = 0
        while i < len(lines):
            depth += lines[i].count("{") - lines[i].count("}")
            i += 1
            if depth == 0:
                break
        result[method_name] = "".join(lines[ann_start:i])
    return result


def rebuild_suite(
    original_source: str,
    updated_methods: Dict[str, str],
    deleted_methods: Optional[List[str]] = None,
) -> str:
    """
    用 updated_methods 中的新版本替换原 suite 中对应方法。
    deleted_methods 列出要删除的方法名。
    未出现在两个参数中的方法保持不变。
    """
    deleted_methods = deleted_methods or []
    existing = extract_test_methods(original_source)
    result   = original_source

    # 替换
    for name, new_body in updated_methods.items():
        if name in existing:
            result = result.replace(existing[name], new_body, 1)
        else:
            # 新增：插入到最后一个 } 之前
            last_brace = result.rfind("\n}")
            if last_brace != -1:
                result = result[:last_brace] + "\n\n" + new_body + "\n" + result[last_brace:]

    # 删除
    for name in deleted_methods:
        if name in existing:
            result = result.replace(existing[name], "", 1)

    return re.sub(r"\n{4,}", "\n\n\n", result)


# ── 文件读写 ───────────────────────────────────────────────────────────

def write_test_case_file(
    tc_dir: str,
    class_name: str,
    method_id,
    seq: int,
    java_source: str,
    package: str = "",
) -> str:
    """
    将 suite 写入 tc_dir/<ClassName>_<mid>_<seq>Test.java。
    自动修正类名和 package 声明。
    与 ChatUniTest 的 export_method_test_case 效果相同。
    """
    from tools import change_class_name, repair_package
    code = change_class_name(java_source, class_name, method_id, seq)
    if package:
        code = repair_package(code, f"package {package};")
    os.makedirs(tc_dir, exist_ok=True)
    path = os.path.join(tc_dir, tc_filename(class_name, method_id, seq))
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    return path


def read_test_case_file(
    tc_dir: str, class_name: str, method_id, seq: int
) -> Optional[str]:
    path = os.path.join(tc_dir, tc_filename(class_name, method_id, seq))
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
