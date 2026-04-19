"""
assert_fixer.py  (v3 — 彻底修正版)
=====================================

为什么不能在fixed版本上替换断言值：
  
  场景：focal method 有一个 bug，buggy版本返回3，fixed版本返回4。
  LLM生成：assertEquals(3, result)  ← LLM猜错了，应该是4
  
  旧版MuTap做法：在fixed版本上运行 → 捕获"expected:<3> but was:<4>" 
                 → 把3替换成4 → assertEquals(4, result)
  
  问题：这个断言在fixed版本pass，但在buggy版本（返回3）时 assertEquals(4,3) FAIL
        ——好像这就是我们想要的？
  
  但实际情况更复杂：
  1. LLM往往生成的测试根本就构造不对（参数错、对象初始化错）
     在这种情况下，运行出来的result根本不是focal method的输出，
     而是某个初始化阶段的值或默认值。替换后断言毫无意义。
  2. 更重要的：LLM生成的测试可能已经编译失败，根本跑不到运行阶段，
     旧版assert_fixer遇到编译失败直接返回原始代码，什么都没做。
     但这路径走了很多时间和资源。

正确做法：
  - 不运行测试，不替换值
  - 只做静态代码清理：移除编译100%失败的模式（私有字段直接访问）
  - 让TestRunner真实评估，让Refiner基于真实诊断数据做修复
  - 详细记录每次改动，便于观察

额外日志：
  - 记录到 <test_dir>/assert_fixer.log，每次调用都追加
  - 格式清晰，能快速看到哪个测试哪行被改了什么
"""
from __future__ import annotations

import logging
import os
import re
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# ── 模块级日志文件路径（可在外部设置）────────────────────────────
_LOG_FILE: Optional[str] = None


def set_log_file(path: str):
    """设置assert_fixer的日志文件路径，便于外部控制。"""
    global _LOG_FILE
    _LOG_FILE = path


def _write_log(msg: str):
    """同时写入logger和日志文件。"""
    logger.info(msg)
    if _LOG_FILE:
        try:
            with open(_LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(msg + '\n')
        except Exception:
            pass


# ════════════════════════════════════════════════════════════════════
# 静态代码清理：只删除编译100%失败的模式
# ════════════════════════════════════════════════════════════════════

def _clean_private_field_direct_access(
    java_source: str,
    private_fields: List[str],
    class_name: str,
) -> Tuple[str, List[Dict]]:
    """
    移除直接访问私有字段的断言语句。
    这是唯一我们能确定"编译100%失败"的模式。

    返回 (修复后代码, 修改记录列表)
    """
    if not private_fields:
        return java_source, []

    changes = []
    lines = java_source.splitlines(keepends=True)
    result = []

    # 构建匹配任意私有字段直接访问的模式
    # 匹配 someObj.fieldName 且后面不是 ( 或 [ （排除方法调用）
    field_pattern = re.compile(
        r'\b\w+\.(' + '|'.join(re.escape(f) for f in private_fields) + r')\b(?!\s*[\(\[])'
    )

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # 只检查断言行
        is_assert = any(kw in stripped for kw in [
            'assertEquals', 'assertNotEquals', 'assertTrue', 'assertFalse',
            'assertNotNull', 'assertNull', 'assertThat', 'assertSame',
        ])

        if is_assert:
            m = field_pattern.search(stripped)
            if m:
                field_name = m.group(1)
                indent = re.match(r'^(\s*)', line).group(1)
                # 用注释替换，保留原始内容便于追踪
                replacement = (
                    f"{indent}// [AssertFixer] Removed: direct private field access "
                    f"'.{field_name}' causes compile error | "
                    f"original: {stripped[:120]}\n"
                )
                result.append(replacement)
                changes.append({
                    "line": i,
                    "action": "REMOVED",
                    "reason": f"private field direct access: .{field_name}",
                    "original": stripped[:120],
                })
                continue

        result.append(line)

    return ''.join(result), changes


def _fix_reflection_field_names(
    java_source: str,
    private_fields: List[str],
    class_name: str,
) -> Tuple[str, List[Dict]]:
    """
    修正 getDeclaredField("xxx") 中明显拼错的字段名。
    只有当编辑距离<=2时才替换（防止误改）。

    返回 (修复后代码, 修改记录列表)
    """
    if not private_fields:
        return java_source, []

    field_set = set(private_fields)
    changes = []
    lines = java_source.splitlines(keepends=True)
    result = []

    for i, line in enumerate(lines, 1):
        m = re.search(r'getDeclaredField\s*\(\s*"(\w+)"\s*\)', line)
        if m:
            field_name = m.group(1)
            if field_name not in field_set:
                similar = _find_similar(field_name, field_set, max_dist=2)
                if similar:
                    new_line = line.replace(f'"{field_name}"', f'"{similar}"', 1)
                    result.append(new_line)
                    changes.append({
                        "line": i,
                        "action": "FIXED",
                        "reason": f"reflection field name typo: '{field_name}' → '{similar}'",
                        "original": line.strip()[:100],
                        "replacement": new_line.strip()[:100],
                    })
                    continue
                else:
                    # 找不到相似的，注释掉整行
                    indent = re.match(r'^(\s*)', line).group(1)
                    replacement = (
                        f"{indent}// [AssertFixer] Removed: unknown field "
                        f"'{field_name}' not in [{', '.join(sorted(field_set)[:5])}] "
                        f"| original: {line.strip()[:80]}\n"
                    )
                    result.append(replacement)
                    changes.append({
                        "line": i,
                        "action": "REMOVED",
                        "reason": f"reflection field '{field_name}' not found in class",
                        "original": line.strip()[:100],
                    })
                    continue

        result.append(line)

    return ''.join(result), changes


def _find_similar(name: str, candidates: Set[str], max_dist: int = 2) -> Optional[str]:
    best, best_d = None, float('inf')
    for c in candidates:
        d = _edit_dist(name.lower(), c.lower())
        if d < best_d:
            best, best_d = c, d
    return best if best_d <= max_dist else None


def _edit_dist(s1: str, s2: str) -> int:
    if len(s1) > len(s2):
        s1, s2 = s2, s1
    prev = list(range(len(s2) + 1))
    for c1 in s1:
        curr = [prev[0] + 1]
        for j, c2 in enumerate(s2):
            curr.append(min(prev[j+1]+1, curr[j]+1, prev[j]+(0 if c1==c2 else 1)))
        prev = curr
    return prev[len(s2)]


# ════════════════════════════════════════════════════════════════════
# 主入口
# ════════════════════════════════════════════════════════════════════

def fix_assertions(
    java_source: str,
    class_name: str,
    package: str,
    project_dir: str,
    junit_jar: str = "",
    mockito_jar: str = "",
    log4j_jar: str = "",
    private_fields: Optional[List[str]] = None,
) -> str:
    """
    静态代码清理：移除编译必然失败的代码模式。

    不做：
    - 运行测试
    - 替换断言预期值（会破坏bugrevealing能力）

    做：
    - 移除直接访问私有字段的断言行
    - 修正反射中明显拼错的字段名

    所有改动都有详细日志输出。
    """
    if not private_fields:
        return java_source

    _write_log(f"\n{'='*60}")
    _write_log(f"[AssertFixer] Processing: {class_name}")
    _write_log(f"  Known private fields: {private_fields}")
    _write_log(f"{'='*60}")

    all_changes = []
    current = java_source

    # Step 1: 移除私有字段直接访问断言
    current, changes1 = _clean_private_field_direct_access(current, private_fields, class_name)
    all_changes.extend(changes1)

    # Step 2: 修正反射字段名拼写
    current, changes2 = _fix_reflection_field_names(current, private_fields, class_name)
    all_changes.extend(changes2)

    if all_changes:
        _write_log(f"[AssertFixer] {class_name}: {len(all_changes)} change(s) made:")
        for ch in all_changes:
            action = ch['action']
            reason = ch['reason']
            line_n = ch['line']
            orig   = ch.get('original', '')
            repl   = ch.get('replacement', '')
            if repl:
                _write_log(f"  Line {line_n} [{action}] {reason}")
                _write_log(f"    Before: {orig}")
                _write_log(f"    After:  {repl}")
            else:
                _write_log(f"  Line {line_n} [{action}] {reason}")
                _write_log(f"    Original: {orig}")
        print(
            f"  [AssertFixer] {class_name}: {len(all_changes)} fix(es) applied "
            f"({sum(1 for c in all_changes if c['action']=='REMOVED')} removed, "
            f"{sum(1 for c in all_changes if c['action']=='FIXED')} fixed)",
            flush=True
        )
    else:
        _write_log(f"[AssertFixer] {class_name}: no changes needed")

    return current