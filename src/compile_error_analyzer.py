"""
compile_error_analyzer.py
==========================
编译错误分类器：将 diagnosis.log 中的编译/运行时错误自动分类，
并生成结构化的修复提示，注入到 Refiner 的 Prompt 中。

核心思路：
  - 通过正则模式识别错误类型（CE-1 ~ CE-10，RE-1 ~ RE-6）
  - 为每种错误生成具体的、代码级别的修复提示
  - 优先级：编译错误 > 运行时错误 > 覆盖率问题
  
这解决了 diagnosis.log 中发现的主要问题类型：
  - 85次 "找不到符号"（主要是CSVFormat.Builder）
  - 19次 构造函数参数数量不匹配
  - 14次 未报告的IOException
  - 12次 方法引用不明确（null重载）
  - 10次 private字段/方法访问
  - 73次 AssertionFailedError（断言值错误）
  - 11次 IllegalArgumentException（null参数）
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
    TYPE_INCOMPATIBLE       = "CE-4"   # 类型不兼容（Closeable→Appendable等）
    UNCHECKED_EXCEPTION     = "CE-5"   # 未声明checked异常
    AMBIGUOUS_METHOD        = "CE-6"   # 方法引用不明确
    ASSERT_THROWS_LAMBDA    = "CE-7"   # assertThrows lambda参数错误
    WRONG_CONSTRUCTOR_ARGS  = "CE-8"   # 构造函数参数错误
    FINAL_VARIABLE_ASSIGN   = "CE-9"   # 赋值给final变量
    TYPE_MISMATCH           = "CE-10"  # String/long等类型不匹配
    UNKNOWN                 = "CE-XX"


class RuntimeErrorType:
    WRONG_ASSERTION_VALUE   = "RE-1"   # expected:<X> but was:<Y>
    WRONG_EXCEPTION_TYPE    = "RE-2"   # wrong exception subclass
    EXCEPTION_NOT_THROWN    = "RE-3"   # expected exception not thrown
    NO_SUCH_FIELD           = "RE-4"   # NoSuchFieldException
    NO_SUCH_METHOD          = "RE-4b"  # NoSuchMethodException
    NULL_ARGUMENT           = "RE-5"   # IllegalArgumentException null
    TYPE_CAST               = "RE-6"   # ClassCastException
    UNKNOWN                 = "RE-XX"


# ════════════════════════════════════════════════════════════════════
# 错误分类结果
# ════════════════════════════════════════════════════════════════════

@dataclass
class ClassifiedError:
    error_type: str
    original_message: str
    fix_hint: str
    fix_code: str = ""
    priority: int = 5   # 1=最高（编译），5=最低（运行时断言值）


# ════════════════════════════════════════════════════════════════════
# 主分类器
# ════════════════════════════════════════════════════════════════════

class CompileErrorAnalyzer:
    """
    将原始错误信息分类并生成具体的、可注入Prompt的修复提示。
    """

    # ── 编译错误模式 ─────────────────────────────────────────────

    _COMPILE_PATTERNS: List[Tuple[str, str, str, str]] = [
        # (pattern, error_type, fix_hint, fix_code_template)

        # CE-1: private访问
        (
            r'(\w+)\s+在\s+(\w+)\s+中是\s+private\s+访问控制',
            CompileErrorType.PRIVATE_ACCESS,
            "Direct access to private member detected. Use Java Reflection instead.",
            """// Replace direct access with reflection:
Field f = {class}.class.getDeclaredField("{field}");
f.setAccessible(true);
Object val = f.get(instance);
// For private method: use getDeclaredMethod(...).setAccessible(true).invoke(...)"""
        ),

        # CE-2: 通用的 Builder 模式缺失 (针对旧版 Java 库常见的 API 差异)
        (
            r'找不到符号.*\n?.*符号:\s+类\s+(\w+)\.Builder|cannot find symbol.*\n?.*symbol:\s+class\s+(\w+)\.Builder',
            CompileErrorType.SYMBOL_NOT_FOUND,
            "The Builder nested class for {class} does not exist in this version. "
            "Check if the library uses static factory methods (e.g., {class}.newXxx()) "
            "or setter-chaining (e.g., {class}.DEFAULT.withXxx()).",
            """// The Builder pattern might not be available. 
// Try using factory methods or fluent 'with' methods:
{class} instance = {class}.DEFAULT.withProperty(value); 
// Or check the focal class context for the correct instantiation way."""
        ),

        # CE-2b: 通用的方法/字段找不到 (最常见)
        (
            r'找不到符号.*\n?.*符号:\s+(?:方法|变量|类)\s+(\w+)|cannot find symbol.*\n?.*symbol:\s+(?:method|variable|class)\s+(\w+)',
            CompileErrorType.SYMBOL_NOT_FOUND,
            "Symbol '{symbol}' not found. It does not exist in the current version of the library.",
            """// '{symbol}' is not available. 
// Please refer to the provided Focal Class context above to see all public APIs 
// available in this specific Defects4J version."""
        ),

        # CE-3: 继承final类
        (
            r'无法从最终(\w+)进行继承',
            CompileErrorType.EXTEND_FINAL,
            "Cannot extend final class. Use Mockito.spy() to wrap and override behavior.",
            """// Replace anonymous subclass with Mockito spy:
{ClassName} spy = Mockito.spy(new {ClassName}(args));
doThrow(new IOException("test")).when(spy).methodToFail();"""
        ),

        # CE-4: Closeable→Appendable
        (
            r'不兼容的类型.*Closeable.*Appendable|不兼容的类型.*Flushable.*Appendable',
            CompileErrorType.TYPE_INCOMPATIBLE,
            "Closeable/Flushable does not implement Appendable. "
            "CSVPrinter constructor requires Appendable.",
            """// Use a type that implements Appendable:
StringWriter out = new StringWriter();           // implements Appendable + Closeable
// OR: Appendable out = mock(Appendable.class);  // pure Appendable mock
new CSVPrinter(out, format);"""
        ),

        # CE-4b: 其他类型不兼容
        (
            r'不兼容的类型',
            CompileErrorType.TYPE_INCOMPATIBLE,
            "Type incompatibility. Check the exact types required by the constructor/method signature.",
            "// Verify the parameter type from the class context and use the correct type."
        ),

        # CE-5: 未报告IOException
        (
            r'未报告的异常错误\s*IOException',
            CompileErrorType.UNCHECKED_EXCEPTION,
            "IOException must be declared or caught. Add 'throws Exception' to the @Test method.",
            """// Add throws Exception to the test method:
@Test
void testMethod() throws Exception {
    // ... your test code
}"""
        ),

        # CE-5b: 未报告SQLException
        (
            r'未报告的异常错误\s*SQLException',
            CompileErrorType.UNCHECKED_EXCEPTION,
            "SQLException must be declared. Add 'throws Exception' to the @Test method.",
            """// Add throws Exception to the test method signature:
@Test
void testMethod() throws Exception {
    when(rs.next()).thenReturn(true);  // now allowed
}"""
        ),

        # CE-6: 方法引用不明确
        (
            r'对(\w+)的引用不明确',
            CompileErrorType.AMBIGUOUS_METHOD,
            "Ambiguous method call with null argument. Cast null to the specific overload type.",
            """// Cast null to disambiguate the overload:
printer.printRecords((Object[]) null);     // Object[] overload
printer.printRecords((ResultSet) null);    // ResultSet overload
// General pattern: method((SpecificType) null)"""
        ),

        # CE-7: assertThrows lambda参数错误
        (
            r'对于assertThrows.*\(e\)->',
            CompileErrorType.ASSERT_THROWS_LAMBDA,
            "assertThrows requires a zero-argument Executable lambda. Remove the 'e' parameter.",
            """// WRONG: assertThrows(IOException.class, e -> obj.method());
// RIGHT: assertThrows(IOException.class, () -> obj.method());"""
        ),

        # CE-8: 构造函数参数不匹配
        (
            r'无法将类\s+\w+中的构造器.*应用到给定类型',
            CompileErrorType.WRONG_CONSTRUCTOR_ARGS,
            "Constructor argument types do not match. "
            "Check the constructor signature in the provided class context.",
            "// Use only the argument types shown in the constructor signature above."
        ),

        # CE-9: 赋值给final变量
        (
            r'无法为最终变量(\w+)分配值',
            CompileErrorType.FINAL_VARIABLE_ASSIGN,
            "Cannot reassign final variable. Declare a new local variable instead.",
            """// WRONG: finalVar = newValue;
// RIGHT: SomeType newVar = newValue;
//   or:  declare the variable non-final in the first place"""
        ),

        # CE-10: String→long类型不匹配
        (
            r'不兼容的类型.*String.*long|不兼容的类型.*String.*StringBuilder',
            CompileErrorType.TYPE_MISMATCH,
            "String cannot be used where long/StringBuilder is expected.",
            """// For long: Long.parseLong(str)  or use a long literal directly
// For StringBuilder: new StringBuilder(str)"""
        ),
    ]

    # ── 运行时错误模式 ────────────────────────────────────────────

    _RUNTIME_PATTERNS: List[Tuple[str, str, str, str]] = [
        # RE-2: 异常类型不匹配
        (
            r'expected:.*StringIndexOutOfBoundsException.*but was:.*IndexOutOfBoundsException|'
            r'Unexpected exception type thrown',
            RuntimeErrorType.WRONG_EXCEPTION_TYPE,
            "Wrong exception subclass asserted. Use the parent class or the actual thrown type.",
            """// Replace StringIndexOutOfBoundsException with its parent:
assertThrows(IndexOutOfBoundsException.class, () -> ...);
// Or use the general parent: assertThrows(RuntimeException.class, () -> ...);"""
        ),

        # RE-3: 期望抛出异常但未抛出
        (
            r'Expected.*to be thrown.*but nothing was thrown',
            RuntimeErrorType.EXCEPTION_NOT_THROWN,
            "Expected exception was not thrown. "
            "Either fix the mock setup or remove the invalid assertThrows.",
            """// Option 1: Fix the mock to trigger the exception path
// Option 2: If the fixed version doesn't throw, remove assertThrows and add positive assertion:
// result = obj.method();
// assertNotNull(result);"""
        ),

        # RE-4: 字段不存在
        (
            r'java\.lang\.NoSuchFieldException:\s*(\w+)',
            RuntimeErrorType.NO_SUCH_FIELD,
            "Field name is wrong. The field does not exist with this name in the actual class.",
            """// Check the class source for the correct field name.
// Common mistakes: 'lineCounter' vs 'lineNumber', 'lastChar' vs 'lastRead'
// Use the exact field name from the focal class source above."""
        ),

        # RE-4b: 方法不存在
        (
            r'java\.lang\.NoSuchMethodException',
            RuntimeErrorType.NO_SUCH_METHOD,
            "Method name or signature is wrong in reflection call.",
            "// Check the exact method name and parameter types in the class source above."
        ),

        # RE-5: null参数
        (
            r"Parameter '(\w+)' must not be null|IllegalArgumentException.*null",
            RuntimeErrorType.NULL_ARGUMENT,
            "Null passed to parameter that requires non-null value.",
            """// Initialize the argument properly:
Reader reader = new StringReader("test content");
// Do NOT pass null where the method requires a real object."""
        ),

        # RE-1: 断言值错误（放最后，最通用）
        (
            r'expected:\s*<([^>]*)>\s*but was:\s*<([^>]*)>',
            RuntimeErrorType.WRONG_ASSERTION_VALUE,
            "Assertion expected value is wrong. Trace the focal method to find the correct value.",
            """// Common mistakes:
// - END_OF_STREAM = -2 (not -1) in ExtendedBufferedReader
// - UNDEFINED = -3 (not -1)
// - Character values: 'a'=97, 'b'=98, 'A'=65
// - Line counting may start at 0 or 1
// If unsure, use a WEAKER assertion: assertNotNull(result) or assertTrue(result >= 0)"""
        ),
    ]

    def classify_compile_errors(self, compile_errors: List[str]) -> List[ClassifiedError]:
        """将编译错误列表分类为结构化的 ClassifiedError 列表。"""
        results = []
        for raw_msg in compile_errors:
            classified = self._match_compile(raw_msg)
            results.append(classified)
        return results

    def classify_exec_errors(self, exec_errors: List[str]) -> List[ClassifiedError]:
        """将运行时错误列表分类。"""
        results = []
        seen_types = set()
        for raw_msg in exec_errors:
            classified = self._match_runtime(raw_msg)
            # 同类型错误只报告一次
            if classified.error_type not in seen_types:
                results.append(classified)
                seen_types.add(classified.error_type)
        return results

    def _match_compile(self, msg: str) -> ClassifiedError:
        for pattern, err_type, hint, code in self._COMPILE_PATTERNS:
            if re.search(pattern, msg, re.IGNORECASE | re.DOTALL):
                # 提取具体的符号名（用于模板替换）
                code = self._fill_template(code, msg)
                return ClassifiedError(
                    error_type=err_type,
                    original_message=msg.strip()[:200],
                    fix_hint=hint,
                    fix_code=code,
                    priority=1,
                )
        return ClassifiedError(
            error_type=CompileErrorType.UNKNOWN,
            original_message=msg.strip()[:200],
            fix_hint="Compile error. Read the full error message and fix accordingly.",
            fix_code="",
            priority=1,
        )

    def _match_runtime(self, msg: str) -> ClassifiedError:
        for pattern, err_type, hint, code in self._RUNTIME_PATTERNS:
            if re.search(pattern, msg, re.IGNORECASE | re.DOTALL):
                return ClassifiedError(
                    error_type=err_type,
                    original_message=msg.strip()[:300],
                    fix_hint=hint,
                    fix_code=code,
                    priority=3 if 'WRONG_ASSERTION' in err_type else 2,
                )
        return ClassifiedError(
            error_type=RuntimeErrorType.UNKNOWN,
            original_message=msg.strip()[:300],
            fix_hint="Runtime error. Read the error message and fix the test logic.",
            fix_code="",
            priority=4,
        )

    def _fill_template(self, template: str, error_msg: str) -> str:
        """用错误信息中提取的具体名称填充代码模板。"""
        
        # 1. 提取 Private 访问冲突 (支持双语)
        m_priv = re.search(r'(\w+).*(?:private|访问控制)', error_msg, re.I)
        if m_priv:
            # 尝试匹配类名，通常在 private 报错的后面
            m_cls = re.search(r'在\s+(\w+)\s+中|in\s+(\w+)', error_msg)
            cls_name = m_cls.group(1) or m_cls.group(2) if m_cls else "TargetClass"
            template = template.replace('{field}', m_priv.group(1)).replace('{class}', cls_name)

        # 2. 提取 Builder 类名
        m_builder = re.search(r'类\s+(\w+)\.Builder|class\s+(\w+)\.Builder', error_msg)
        if m_builder:
            cls_name = m_builder.group(1) or m_builder.group(2)
            template = template.replace('{class}', cls_name)

        # 3. 提取通用的缺失符号 (方法名/变量名)
        m_symbol = re.search(r'符号:\s+(?:方法|变量|类)\s+(\w+)|symbol:\s+(?:method|variable|class)\s+(\w+)', error_msg)
        if m_symbol:
            sym_name = m_symbol.group(1) or m_symbol.group(2)
            template = template.replace('{symbol}', sym_name)

        # 4. 提取 Final 类名 (支持双语)
        m_final = re.search(r'最终(\w+)|final\s+(\w+)', error_msg)
        if m_final:
            cls_name = m_final.group(1) or m_final.group(2)
            template = template.replace('{ClassName}', cls_name)

        return template

    def generate_fix_instructions(
        self,
        compile_errors: List[str],
        exec_errors: List[str],
        compile_ok: bool,
        exec_ok: bool,
    ) -> List[str]:
        """
        生成可直接注入到 Refiner prompt 的修复指令列表。
        优先处理编译错误，其次处理运行时错误。
        """
        instructions = []

        if not compile_ok and compile_errors:
            classified = self.classify_compile_errors(compile_errors)
            # 按错误类型分组，避免重复
            seen = set()
            for ce in classified:
                if ce.error_type in seen:
                    # 同类型只添加一次，但提及具体错误
                    for instr in instructions:
                        if ce.error_type in instr:
                            # 追加具体的错误名
                            break
                    continue
                seen.add(ce.error_type)

                instr = f"[{ce.error_type}] {ce.fix_hint}"
                if ce.fix_code:
                    instr += f"\nExample fix:\n{ce.fix_code}"
                instructions.append(instr)

        elif not exec_ok and exec_errors:
            classified = self.classify_exec_errors(exec_errors)
            for re_err in classified:
                instr = f"[{re_err.error_type}] {re_err.fix_hint}"
                if re_err.fix_code:
                    instr += f"\nExample fix:\n{re_err.fix_code}"
                instructions.append(instr)

        return instructions[:4]  # 最多4条，避免prompt过长


# ════════════════════════════════════════════════════════════════════
# 集成入口：增强 TestDiag 的指令生成
# ════════════════════════════════════════════════════════════════════

_analyzer = CompileErrorAnalyzer()


def enrich_diag_with_fix_hints(diag) -> List[str]:
    """
    从 TestDiag 对象生成额外的修复提示，供 Refiner 使用。

    用法（在 refine_agent.py 的 _build_refiner_messages 中调用）：
        extra_hints = enrich_diag_with_fix_hints(diag)
        # 将 extra_hints 追加到该 Test 的 instructions 中
    """
    return _analyzer.generate_fix_instructions(
        compile_errors=getattr(diag, 'compile_errors', []),
        exec_errors=getattr(diag, 'exec_errors', []),
        compile_ok=getattr(diag, 'compile_ok', True),
        exec_ok=getattr(diag, 'exec_ok', True),
    )


def get_error_summary(compile_errors: List[str], exec_errors: List[str]) -> str:
    """
    生成简洁的错误摘要文本，用于 suite_summary 生成。
    """
    if not compile_errors and not exec_errors:
        return ""

    parts = []
    if compile_errors:
        classified = _analyzer.classify_compile_errors(compile_errors)
        types = list(dict.fromkeys(ce.error_type for ce in classified))
        parts.append(f"Compile errors: {', '.join(types)}")

    if exec_errors:
        classified = _analyzer.classify_exec_errors(exec_errors)
        types = list(dict.fromkeys(re_e.error_type for re_e in classified))
        parts.append(f"Runtime errors: {', '.join(types)}")

    return "; ".join(parts)