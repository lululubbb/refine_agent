"""
compile_error_analyzer.py  (v2 — 删除 fix_code，只保留错误类型标签)
==========================

修改说明：
  原版会生成 fix_code（Java 代码模板）注入到 prompt 中，这会：
  1. 限制 LLM 的修复空间（LLM 倾向于照搬模板，而不是真正理解问题）
  2. 模板代码可能不适用具体场景（如类名、字段名硬编码）
  3. 增加 prompt 冗余，干扰 LLM 判断

  修改后只保留：
  - error_type 标签（CE-1, CE-2 等），用于 Refiner 做问题分类
  - 简洁的一句话 fix_hint，描述问题是什么（不给具体代码）
  - 原始错误消息（供 LLM 自行分析）

  这样 LLM 可以根据完整的错误信息和自身知识生成更适合具体场景的修复。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ════════════════════════════════════════════════════════════════════
# 错误类型枚举
# ════════════════════════════════════════════════════════════════════

class CompileErrorType:
    PRIVATE_ACCESS          = "CE-1"   # private字段/方法直接访问
    SYMBOL_NOT_FOUND        = "CE-2"   # 找不到符号（API不存在）
    EXTEND_FINAL            = "CE-3"   # 继承final类
    TYPE_INCOMPATIBLE       = "CE-4"   # 类型不兼容
    UNCHECKED_EXCEPTION     = "CE-5"   # 未声明checked异常
    AMBIGUOUS_METHOD        = "CE-6"   # 方法引用不明确
    ASSERT_THROWS_LAMBDA    = "CE-7"   # assertThrows lambda参数错误
    WRONG_CONSTRUCTOR_ARGS  = "CE-8"   # 构造函数参数错误
    FINAL_VARIABLE_ASSIGN   = "CE-9"   # 赋值给final变量
    TYPE_MISMATCH           = "CE-10"  # 类型不匹配
    GENERIC_TYPE_ERROR      = "CE-11"  # 泛型类型参数错误
    ACCESS_CONTROL          = "CE-12"  # 访问控制（protected/package-private）
    ABSTRACT_METHOD         = "CE-13"  # 抽象方法未实现
    UNKNOWN                 = "CE-XX"


class RuntimeErrorType:
    WRONG_ASSERTION_VALUE   = "RE-1"
    WRONG_EXCEPTION_TYPE    = "RE-2"
    EXCEPTION_NOT_THROWN    = "RE-3"
    NO_SUCH_FIELD           = "RE-4"
    NO_SUCH_METHOD          = "RE-4b"
    NULL_ARGUMENT           = "RE-5"
    TYPE_CAST               = "RE-6"
    UNKNOWN                 = "RE-XX"


# ════════════════════════════════════════════════════════════════════
# 错误分类结果（★ 删除 fix_code 字段）
# ════════════════════════════════════════════════════════════════════

@dataclass
class ClassifiedError:
    error_type: str
    original_message: str
    fix_hint: str          # 一句话描述问题是什么，不给具体代码
    priority: int = 5


# ════════════════════════════════════════════════════════════════════
# 主分类器
# ════════════════════════════════════════════════════════════════════

class CompileErrorAnalyzer:
    """
    将原始错误信息分类并生成简洁的问题标签。

    ★ 设计原则：只标识"是什么问题"，不给出"怎么修"的代码模板。
    让 LLM 根据完整错误信息和自身知识决定如何修复。
    """

    # ── 编译错误模式（中英双语）────────────────────────────────────
    # 格式: (pattern, error_type, fix_hint)
    # ★ 删除了原来的第4个元素 fix_code

    _COMPILE_PATTERNS: List[Tuple[str, str, str]] = [

        # CE-1: private 访问
        (
            r'(\w+)\s+在\s+(\w+)\s+中是\s+private\s+访问控制',
            CompileErrorType.PRIVATE_ACCESS,
            "Direct access to private member — use Java Reflection (getDeclaredField/getDeclaredMethod + setAccessible).",
        ),
        (
            r'(\w+) has private access in (\w+)',
            CompileErrorType.PRIVATE_ACCESS,
            "Direct access to private member — use Java Reflection.",
        ),
        (
            r'(\w+)\(.*?\)\s+has private access in (\w+)',
            CompileErrorType.PRIVATE_ACCESS,
            "Private method called directly — use getDeclaredMethod + setAccessible.",
        ),

        # CE-11: 泛型类型参数错误
        (
            r'类型参数\S+不在类型变量\S+的范围内',
            CompileErrorType.GENERIC_TYPE_ERROR,
            "Generic type argument is out of bounds — check the type parameter constraints in the class context.",
        ),
        (
            r'type argument \S+ is not within bounds of type-variable \S+',
            CompileErrorType.GENERIC_TYPE_ERROR,
            "Generic type argument is not within bounds — check type parameter constraints.",
        ),

        # CE-2: 找不到符号
        (
            r'找不到符号\s*\n?\s*符号:\s+(?:方法|变量|类)\s+(\w+)',
            CompileErrorType.SYMBOL_NOT_FOUND,
            "Symbol not found — this API may not exist in this version; check the provided class context for available APIs.",
        ),
        (
            r'cannot find symbol\s*\n?\s*symbol:\s+(?:method|variable|class)\s+(\w+)',
            CompileErrorType.SYMBOL_NOT_FOUND,
            "Symbol not found — use only APIs shown in the provided class context.",
        ),

        # CE-3: 继承 final 类
        (
            r'无法从最终(\w+)进行继承',
            CompileErrorType.EXTEND_FINAL,
            "Cannot extend final class — use Mockito.spy() instead of anonymous subclass.",
        ),
        (
            r'cannot inherit from final (\w+)',
            CompileErrorType.EXTEND_FINAL,
            "Cannot extend final class — use Mockito.spy() instead of anonymous subclass.",
        ),

        # CE-4: 类型不兼容
        (
            r'不兼容的类型.*(?:Closeable|Flushable).*(?:Appendable|无法转换)',
            CompileErrorType.TYPE_INCOMPATIBLE,
            "Closeable/Flushable does not implement Appendable — use a type that implements Appendable (e.g., StringWriter).",
        ),
        (
            r'不兼容的类型[：:]\s*(\S+)\s*(?:无法转换为|cannot be converted to)\s*(\S+)',
            CompileErrorType.TYPE_INCOMPATIBLE,
            "Type incompatibility — check the expected type from the class context.",
        ),
        (
            r'incompatible types[:\s]+(\S+)\s+cannot be converted to\s+(\S+)',
            CompileErrorType.TYPE_INCOMPATIBLE,
            "Type incompatibility — check the expected type from the class context.",
        ),

        # CE-5: 未声明 checked 异常
        (
            r'未报告的异常错误\s*(?:java\.io\.)?IOException',
            CompileErrorType.UNCHECKED_EXCEPTION,
            "IOException must be declared — add 'throws Exception' to the @Test method signature.",
        ),
        (
            r'unreported exception\s+(?:java\.io\.)?IOException',
            CompileErrorType.UNCHECKED_EXCEPTION,
            "IOException must be declared — add 'throws Exception' to the @Test method signature.",
        ),
        (
            r'未报告的异常错误\s*(?:java\.sql\.)?SQLException|unreported exception\s+(?:java\.sql\.)?SQLException',
            CompileErrorType.UNCHECKED_EXCEPTION,
            "SQLException must be declared — add 'throws Exception' to the @Test method signature.",
        ),

        # CE-6: 引用不明确
        (
            r'对(\w+)的引用不明确',
            CompileErrorType.AMBIGUOUS_METHOD,
            "Ambiguous method call with null — cast null to the specific overload type.",
        ),
        (
            r'reference to (\w+) is ambiguous',
            CompileErrorType.AMBIGUOUS_METHOD,
            "Ambiguous method call — cast the null argument to the specific type.",
        ),

        # CE-7: assertThrows lambda 参数错误
        (
            r'assertThrows.*\(e\)->|assertThrows.*lambda.*parameter',
            CompileErrorType.ASSERT_THROWS_LAMBDA,
            "assertThrows requires zero-argument lambda — use '() ->' not 'e ->'.",
        ),

        # CE-8: 构造函数参数不匹配
        (
            r'无法将类\s+\w+中的构造器.*应用到给定类型',
            CompileErrorType.WRONG_CONSTRUCTOR_ARGS,
            "Constructor argument types do not match — check the constructor signature in the class context.",
        ),
        (
            r'constructor \w+ in class \w+ cannot be applied to given types',
            CompileErrorType.WRONG_CONSTRUCTOR_ARGS,
            "Constructor arguments do not match — check the exact signature in the class context.",
        ),

        # CE-9: 赋值 final 变量
        (
            r'无法为最终变量(\w+)分配值',
            CompileErrorType.FINAL_VARIABLE_ASSIGN,
            "Cannot reassign final variable — declare a new variable instead.",
        ),
        (
            r'cannot assign a value to final variable (\w+)',
            CompileErrorType.FINAL_VARIABLE_ASSIGN,
            "Cannot reassign final variable — use a new variable.",
        ),

        # CE-10: 类型不匹配
        (
            r'不兼容的类型.*String.*long|不兼容的类型.*String.*StringBuilder',
            CompileErrorType.TYPE_MISMATCH,
            "String cannot be used where long/StringBuilder is expected — parse or convert appropriately.",
        ),

        # CE-12: 访问控制
        (
            r'(\w+)\s+在\s+(\w+)\s+中不是公共的.*无法从外部程序包中对其进行访问|'
            r'(\w+) is not public in (\w+); cannot be accessed from outside package',
            CompileErrorType.ACCESS_CONTROL,
            "Method/field is not public — use reflection or test from same package.",
        ),

        # CE-13: 抽象类
        (
            r'(\w+)是抽象的.*无法实例化|(\w+) is abstract; cannot be instantiated',
            CompileErrorType.ABSTRACT_METHOD,
            "Cannot instantiate abstract class — use a concrete subclass or mock.",
        ),
    ]

    # ── 运行时错误模式（★ 同样删除 fix_code）──────────────────────

    _RUNTIME_PATTERNS: List[Tuple[str, str, str]] = [
        (
            r'expected:.*StringIndexOutOfBoundsException.*but was:.*IndexOutOfBoundsException|'
            r'Unexpected exception type thrown',
            RuntimeErrorType.WRONG_EXCEPTION_TYPE,
            "Wrong exception subclass thrown — use the parent class in assertThrows.",
        ),
        (
            r'Expected.*to be thrown.*but nothing was thrown',
            RuntimeErrorType.EXCEPTION_NOT_THROWN,
            "Expected exception was not thrown — fix mock setup or remove assertThrows.",
        ),
        (
            r'java\.lang\.NoSuchFieldException:\s*(\w+)',
            RuntimeErrorType.NO_SUCH_FIELD,
            "Field name in reflection call is wrong — check the exact field name in the source code.",
        ),
        (
            r'java\.lang\.NoSuchMethodException',
            RuntimeErrorType.NO_SUCH_METHOD,
            "Method name or signature in reflection call is wrong — check exact name and parameter types.",
        ),
        (
            r"Parameter '(\w+)' must not be null|IllegalArgumentException.*null",
            RuntimeErrorType.NULL_ARGUMENT,
            "Null passed where non-null is required — initialize the argument properly.",
        ),
        (
            r'expected:\s*<([^>]*)>\s*but was:\s*<([^>]*)>',
            RuntimeErrorType.WRONG_ASSERTION_VALUE,
            "Assertion expected value is wrong — trace the focal method carefully for the correct return value; use weaker assertions (assertNotNull) when uncertain.",
        ),
    ]

    def classify_compile_errors(self, compile_errors: List[str]) -> List[ClassifiedError]:
        results = []
        for raw_msg in compile_errors:
            classified = self._match_compile(raw_msg)
            results.append(classified)
        return results

    def classify_exec_errors(self, exec_errors: List[str]) -> List[ClassifiedError]:
        results = []
        seen_types = set()
        for raw_msg in exec_errors:
            classified = self._match_runtime(raw_msg)
            if classified.error_type not in seen_types:
                results.append(classified)
                seen_types.add(classified.error_type)
        return results

    def _match_compile(self, msg: str) -> ClassifiedError:
        for pattern, err_type, hint in self._COMPILE_PATTERNS:
            if re.search(pattern, msg, re.IGNORECASE | re.DOTALL):
                return ClassifiedError(
                    error_type=err_type,
                    original_message=msg.strip()[:200],
                    fix_hint=hint,
                    priority=1,
                )
        return ClassifiedError(
            error_type=CompileErrorType.UNKNOWN,
            original_message=msg.strip()[:200],
            fix_hint="Compile error — analyze the error message and fix accordingly.",
            priority=1,
        )

    def _match_runtime(self, msg: str) -> ClassifiedError:
        for pattern, err_type, hint in self._RUNTIME_PATTERNS:
            if re.search(pattern, msg, re.IGNORECASE | re.DOTALL):
                return ClassifiedError(
                    error_type=err_type,
                    original_message=msg.strip()[:300],
                    fix_hint=hint,
                    priority=3 if 'WRONG_ASSERTION' in err_type else 2,
                )
        return ClassifiedError(
            error_type=RuntimeErrorType.UNKNOWN,
            original_message=msg.strip()[:300],
            fix_hint="Runtime error — analyze the error message and fix the test logic.",
            priority=4,
        )

    def generate_fix_instructions(
        self,
        compile_errors: List[str],
        exec_errors: List[str],
        compile_ok: bool,
        exec_ok: bool,
    ) -> List[str]:
        """
        生成注入 Refiner prompt 的错误分类标签列表。

        ★ 修改：只输出 [类型标签] + 一句话描述，不输出代码模板。
        让 LLM 根据完整错误信息自行决定修复方案。
        """
        instructions = []

        if not compile_ok and compile_errors:
            classified = self.classify_compile_errors(compile_errors)

            # 按类型去重
            seen_types: dict = {}
            for ce in classified:
                if ce.error_type not in seen_types:
                    seen_types[ce.error_type] = ce

            for err_type, ce in seen_types.items():
                same_type_errors = [
                    c.original_message for c in classified
                    if c.error_type == err_type
                ]

                if err_type == CompileErrorType.UNKNOWN:
                    # 未识别的错误直接给原始消息，让 LLM 自行分析
                    for raw_msg in same_type_errors[:2]:
                        instr = f"[{err_type}] Compile error: {raw_msg[:150]}"
                        instructions.append(instr)
                else:
                    # 已识别类型：给出类型标签 + 简洁描述
                    if len(same_type_errors) > 1:
                        examples = "; ".join(e[:80] for e in same_type_errors[:2])
                        instr = f"[{err_type}] {ce.fix_hint}\nAffected: {examples}"
                    else:
                        instr = f"[{err_type}] {ce.fix_hint}"
                    # ★ 不再附加 fix_code
                    instructions.append(instr)

        elif not exec_ok and exec_errors:
            classified = self.classify_exec_errors(exec_errors)
            for re_err in classified:
                instr = f"[{re_err.error_type}] {re_err.fix_hint}"
                # ★ 不再附加 fix_code
                instructions.append(instr)

        return instructions[:4]


# ════════════════════════════════════════════════════════════════════
# 集成入口
# ════════════════════════════════════════════════════════════════════

_analyzer = CompileErrorAnalyzer()


def enrich_diag_with_fix_hints(diag) -> List[str]:
    """
    从 TestDiag 对象生成错误分类标签，供 Refiner 使用。
    ★ 现在只返回类型标签，不返回代码模板。
    """
    return _analyzer.generate_fix_instructions(
        compile_errors=getattr(diag, 'compile_errors', []),
        exec_errors=getattr(diag, 'exec_errors', []),
        compile_ok=getattr(diag, 'compile_ok', True),
        exec_ok=getattr(diag, 'exec_ok', True),
    )


def get_error_summary(compile_errors: List[str], exec_errors: List[str]) -> str:
    """生成简洁的错误类型摘要文本（仅类型标签，无代码）。"""
    if not compile_errors and not exec_errors:
        return ""

    parts = []
    if compile_errors:
        classified = _analyzer.classify_compile_errors(compile_errors)
        seen = []
        for ce in classified:
            if ce.error_type not in seen:
                seen.append(ce.error_type)
        parts.append(f"Compile errors: {', '.join(seen)}")

    if exec_errors:
        classified = _analyzer.classify_exec_errors(exec_errors)
        types = list(dict.fromkeys(re_e.error_type for re_e in classified))
        parts.append(f"Runtime errors: {', '.join(types)}")

    return "; ".join(parts)