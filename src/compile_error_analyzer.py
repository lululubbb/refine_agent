"""
compile_error_analyzer.py
==========================
编译错误分类器：将 diagnosis.log 中的编译/运行时错误自动分类，
并生成结构化的修复提示，注入到 Refiner 的 Prompt 中。
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
# 错误分类结果
# ════════════════════════════════════════════════════════════════════

@dataclass
class ClassifiedError:
    error_type: str
    original_message: str
    fix_hint: str
    fix_code: str = ""
    priority: int = 5


# ════════════════════════════════════════════════════════════════════
# 主分类器
# ════════════════════════════════════════════════════════════════════

class CompileErrorAnalyzer:
    """
    将原始错误信息分类并生成具体的修复提示。
    支持中英文双语 javac 输出。
    """

    # ── 编译错误模式（中英双语）────────────────────────────────────
    # 每条: (pattern, error_type, fix_hint, fix_code_template)

    _COMPILE_PATTERNS: List[Tuple[str, str, str, str]] = [

        # ── CE-1: private 访问（中文）──────────────────────────────
        (
            r'(\w+)\s+在\s+(\w+)\s+中是\s+private\s+访问控制',
            CompileErrorType.PRIVATE_ACCESS,
            "Direct access to private member. Use Java Reflection instead.",
            """// Replace direct access with reflection:
Field f = {class}.class.getDeclaredField("{field}");
f.setAccessible(true);
Object val = f.get(instance);
// For private method:
Method m = {class}.class.getDeclaredMethod("methodName", ArgType.class);
m.setAccessible(true);
m.invoke(instance, args);"""
        ),

        # ── CE-1: private 访问（英文）──────────────────────────────
        (
            r'(\w+) has private access in (\w+)',
            CompileErrorType.PRIVATE_ACCESS,
            "Direct access to private member. Use Java Reflection instead.",
            """// Replace direct access with reflection:
Field f = {class}.class.getDeclaredField("{field}");
f.setAccessible(true);
Object val = f.get(instance);"""
        ),

        # ── CE-1: private 方法访问（英文备用）──────────────────────
        (
            r'(\w+)\(.*?\)\s+has private access in (\w+)',
            CompileErrorType.PRIVATE_ACCESS,
            "Private method called directly. Use getDeclaredMethod + setAccessible.",
            """// Replace with reflection:
Method m = {class}.class.getDeclaredMethod("{field}", ParamType.class);
m.setAccessible(true);
m.invoke(instance, args);"""
        ),

        # ── CE-11: 泛型类型参数错误（中文）─────────────────────────
        (
            r'类型参数\S+不在类型变量\S+的范围内',
            CompileErrorType.GENERIC_TYPE_ERROR,
            "Generic type parameter is out of bounds. Use the correct bounded type.",
            """// Check the generic bounds of the class/method.
// For example, if T extends Comparable<?>, use Comparable<?> not Object:
// WRONG: AVLTree<Object> tree = new AVLTree<>();
// RIGHT: AVLTree<Comparable<?>> tree = new AVLTree<>();
// For collections: use the actual element type from the focal class context."""
        ),

        # ── CE-11: 泛型类型参数错误（英文）─────────────────────────
        (
            r'type argument \S+ is not within bounds of type-variable \S+',
            CompileErrorType.GENERIC_TYPE_ERROR,
            "Generic type argument is not within bounds. Check the type parameter constraints.",
            """// Check the generic bounds and use the correct type.
// Example: if T extends Comparable<?>, don't use Object as the type argument."""
        ),

        # ── CE-2: Builder 不存在（中文）────────────────────────────
        (
            r'找不到符号.*\n?.*符号:\s+类\s+(\w+)\.Builder|cannot find symbol.*\n?.*symbol:\s+class\s+(\w+)\.Builder',
            CompileErrorType.SYMBOL_NOT_FOUND,
            "Builder nested class does not exist in this version. Use factory methods or with-chaining.",
            """// Use static factory + with-chaining instead:
{class} instance = {class}.DEFAULT.withProperty(value);"""
        ),

        # ── CE-2: 找不到符号（中文）────────────────────────────────
        (
            r'找不到符号\s*\n?\s*符号:\s+(?:方法|变量|类)\s+(\w+)',
            CompileErrorType.SYMBOL_NOT_FOUND,
            "Symbol not found. It does not exist in this version of the library.",
            """// Check the focal class context for available public APIs in this version."""
        ),

        # ── CE-2: cannot find symbol（英文）────────────────────────
        (
            r'cannot find symbol\s*\n?\s*symbol:\s+(?:method|variable|class)\s+(\w+)',
            CompileErrorType.SYMBOL_NOT_FOUND,
            "Symbol not found. Use only APIs shown in the provided class context.",
            """// Check the focal class context for the correct API name."""
        ),

        # ── CE-3: 继承final类（中文）────────────────────────────────
        (
            r'无法从最终(\w+)进行继承',
            CompileErrorType.EXTEND_FINAL,
            "Cannot extend final class. Use Mockito.spy() instead of anonymous subclass.",
            """// Replace anonymous subclass:
{ClassName} spy = Mockito.spy(new {ClassName}(args));
doThrow(new IOException()).when(spy).someMethod();"""
        ),

        # ── CE-3: 继承final类（英文）────────────────────────────────
        (
            r'cannot inherit from final (\w+)',
            CompileErrorType.EXTEND_FINAL,
            "Cannot extend final class. Use Mockito.spy() instead.",
            """// Use spy instead of anonymous subclass:
{ClassName} spy = Mockito.spy(new {ClassName}(args));"""
        ),

        # ── CE-4: Closeable→Appendable 类型不兼容（中文）─────────
        (
            r'不兼容的类型.*(?:Closeable|Flushable).*(?:Appendable|无法转换)',
            CompileErrorType.TYPE_INCOMPATIBLE,
            "Closeable/Flushable does not implement Appendable. Use StringWriter instead.",
            """// Use a type that implements Appendable:
StringWriter out = new StringWriter();  // implements Appendable + Closeable
new CSVPrinter(out, format);"""
        ),

        # ── CE-4: 类型不兼容（通用中文）───────────────────────────
        (
            r'不兼容的类型[：:]\s*(\S+)\s*(?:无法转换为|cannot be converted to)\s*(\S+)',
            CompileErrorType.TYPE_INCOMPATIBLE,
            "Type incompatibility. Check the expected type from the class context.",
            "// Verify the parameter type from the class context and use the correct type."
        ),

        # ── CE-4: incompatible types（英文）────────────────────────
        (
            r'incompatible types[:\s]+(\S+)\s+cannot be converted to\s+(\S+)',
            CompileErrorType.TYPE_INCOMPATIBLE,
            "Type incompatibility. Check the expected type.",
            "// Use the correct type as shown in the focal class context."
        ),

        # ── CE-5: 未报告 IOException（中文）────────────────────────
        (
            r'未报告的异常错误\s*(?:java\.io\.)?IOException',
            CompileErrorType.UNCHECKED_EXCEPTION,
            "IOException must be declared. Add 'throws Exception' to the @Test method.",
            """// Add throws Exception to the test method:
@Test
void testMethod() throws Exception { ... }"""
        ),

        # ── CE-5: unreported exception（英文）──────────────────────
        (
            r'unreported exception\s+(?:java\.io\.)?IOException',
            CompileErrorType.UNCHECKED_EXCEPTION,
            "IOException must be declared. Add 'throws Exception' to the @Test method.",
            """@Test
void testMethod() throws Exception { ... }"""
        ),

        # ── CE-5: 未报告 SQLException（中文/英文）──────────────────
        (
            r'未报告的异常错误\s*(?:java\.sql\.)?SQLException|unreported exception\s+(?:java\.sql\.)?SQLException',
            CompileErrorType.UNCHECKED_EXCEPTION,
            "SQLException must be declared. Add 'throws Exception' to the @Test method.",
            """@Test
void testMethod() throws Exception { ... }"""
        ),

        # ── CE-6: 引用不明确（中文）────────────────────────────────
        (
            r'对(\w+)的引用不明确',
            CompileErrorType.AMBIGUOUS_METHOD,
            "Ambiguous method call with null. Cast null to the specific overload type.",
            """// Cast null to disambiguate:
printer.printRecords((Object[]) null);
printer.printRecords((ResultSet) null);"""
        ),

        # ── CE-6: reference is ambiguous（英文）────────────────────
        (
            r'reference to (\w+) is ambiguous',
            CompileErrorType.AMBIGUOUS_METHOD,
            "Ambiguous method call. Cast the argument to the specific type.",
            """// Cast null to disambiguate the overload:
method((SpecificType) null);"""
        ),

        # ── CE-7: assertThrows lambda 参数错误─────────────────────
        (
            r'assertThrows.*\(e\)->|assertThrows.*lambda.*parameter',
            CompileErrorType.ASSERT_THROWS_LAMBDA,
            "assertThrows requires zero-argument lambda. Use '() ->' not 'e ->'.",
            """// WRONG: assertThrows(IOException.class, e -> obj.method());
// RIGHT: assertThrows(IOException.class, () -> obj.method());"""
        ),

        # ── CE-8: 构造函数参数不匹配（中文）────────────────────────
        (
            r'无法将类\s+\w+中的构造器.*应用到给定类型',
            CompileErrorType.WRONG_CONSTRUCTOR_ARGS,
            "Constructor argument types do not match the signature.",
            "// Check the constructor signature in the class context and match exactly."
        ),

        # ── CE-8: constructor mismatch（英文）──────────────────────
        (
            r'constructor \w+ in class \w+ cannot be applied to given types',
            CompileErrorType.WRONG_CONSTRUCTOR_ARGS,
            "Constructor arguments do not match. Check the exact signature.",
            "// Match constructor arguments exactly as shown in the focal class context."
        ),

        # ── CE-9: 赋值给final变量（中文）───────────────────────────
        (
            r'无法为最终变量(\w+)分配值',
            CompileErrorType.FINAL_VARIABLE_ASSIGN,
            "Cannot reassign final variable. Declare a new variable instead.",
            "// Declare a new variable instead of reassigning the final one."
        ),

        # ── CE-9: cannot assign to final（英文）────────────────────
        (
            r'cannot assign a value to final variable (\w+)',
            CompileErrorType.FINAL_VARIABLE_ASSIGN,
            "Cannot reassign final variable. Use a new variable.",
            "// Use: SomeType newVar = newValue; instead of reassigning final."
        ),

        # ── CE-10: String→long 类型不匹配（中文）──────────────────
        (
            r'不兼容的类型.*String.*long|不兼容的类型.*String.*StringBuilder',
            CompileErrorType.TYPE_MISMATCH,
            "String cannot be used where long/StringBuilder is expected.",
            """// For long: Long.parseLong(str)
// For StringBuilder: new StringBuilder(str)"""
        ),

        # ── CE-12: 访问控制（protected/package-private）────────────
        (
            r'(\w+)\s+在\s+(\w+)\s+中不是公共的.*无法从外部程序包中对其进行访问|'
            r'(\w+) is not public in (\w+); cannot be accessed from outside package',
            CompileErrorType.ACCESS_CONTROL,
            "Method/field is not public. Use reflection or test from same package.",
            """// Use reflection to access non-public members:
Method m = ClassName.class.getDeclaredMethod("methodName");
m.setAccessible(true);
m.invoke(instance);"""
        ),

        # ── CE-13: 抽象类未实现──────────────────────────────────────
        (
            r'(\w+)是抽象的.*无法实例化|(\w+) is abstract; cannot be instantiated',
            CompileErrorType.ABSTRACT_METHOD,
            "Cannot instantiate abstract class. Use a concrete subclass or mock.",
            """// Use mock or concrete subclass:
AbstractClass mock = mock(AbstractClass.class);
// OR find a concrete implementation in the focal class context."""
        ),
    ]

    # ── 运行时错误模式（不变）──────────────────────────────────────

    _RUNTIME_PATTERNS: List[Tuple[str, str, str, str]] = [
        (
            r'expected:.*StringIndexOutOfBoundsException.*but was:.*IndexOutOfBoundsException|'
            r'Unexpected exception type thrown',
            RuntimeErrorType.WRONG_EXCEPTION_TYPE,
            "Wrong exception subclass. Use the parent class in assertThrows.",
            """// Use the parent exception:
assertThrows(IndexOutOfBoundsException.class, () -> ...);
// Or: assertThrows(RuntimeException.class, () -> ...);"""
        ),
        (
            r'Expected.*to be thrown.*but nothing was thrown',
            RuntimeErrorType.EXCEPTION_NOT_THROWN,
            "Expected exception was not thrown. Fix mock setup or remove assertThrows.",
            """// Fix the mock to trigger the exception, or replace assertThrows with a positive assertion."""
        ),
        (
            r'java\.lang\.NoSuchFieldException:\s*(\w+)',
            RuntimeErrorType.NO_SUCH_FIELD,
            "Field name is wrong in reflection call. Check the exact field name.",
            "// Check the exact field name from the focal class source above."
        ),
        (
            r'java\.lang\.NoSuchMethodException',
            RuntimeErrorType.NO_SUCH_METHOD,
            "Method name or signature is wrong in reflection call.",
            "// Check the exact method name and parameter types."
        ),
        (
            r"Parameter '(\w+)' must not be null|IllegalArgumentException.*null",
            RuntimeErrorType.NULL_ARGUMENT,
            "Null passed where non-null is required. Initialize the argument properly.",
            """// Initialize properly:
Reader reader = new StringReader("test content");"""
        ),
        (
            r'expected:\s*<([^>]*)>\s*but was:\s*<([^>]*)>',
            RuntimeErrorType.WRONG_ASSERTION_VALUE,
            "Assertion expected value is wrong. Trace the focal method for the correct value.",
            """// Common fixes:
// - END_OF_STREAM = -2, UNDEFINED = -3 (not -1)
// - Use weaker assertion if unsure: assertNotNull(result) or assertTrue(result >= 0)"""
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
        for pattern, err_type, hint, code in self._COMPILE_PATTERNS:
            if re.search(pattern, msg, re.IGNORECASE | re.DOTALL):
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
        """用错误信息中提取的名称填充代码模板。"""
        # private 字段/方法名
        m_priv = re.search(
            r'(\w+)\s+在\s+(\w+)\s+中是\s+private|(\w+) has private access in (\w+)',
            error_msg, re.I)
        if m_priv:
            field_name = m_priv.group(1) or m_priv.group(3) or "fieldName"
            cls_name   = m_priv.group(2) or m_priv.group(4) or "TargetClass"
            template = template.replace('{field}', field_name).replace('{class}', cls_name)

        # Builder 类名
        m_builder = re.search(r'类\s+(\w+)\.Builder|class\s+(\w+)\.Builder', error_msg)
        if m_builder:
            cls_name = m_builder.group(1) or m_builder.group(2)
            template = template.replace('{class}', cls_name)

        # 缺失符号名
        m_symbol = re.search(
            r'符号:\s+(?:方法|变量|类)\s+(\w+)|symbol:\s+(?:method|variable|class)\s+(\w+)',
            error_msg)
        if m_symbol:
            sym = m_symbol.group(1) or m_symbol.group(2)
            template = template.replace('{symbol}', sym)

        # Final 类名
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
        生成可注入 Refiner prompt 的修复指令列表。
        关键修复：按错误类型去重，同类型只生成一条指令，避免重复。
        """
        instructions = []

        if not compile_ok and compile_errors:
            classified = self.classify_compile_errors(compile_errors)

            # ★ 关键修复：按错误类型去重，每种类型只生成一条指令
            seen_types: dict = {}  # {error_type: ClassifiedError}
            for ce in classified:
                if ce.error_type not in seen_types:
                    seen_types[ce.error_type] = ce
                # CE-XX 类型收集所有原始错误，但只生成一条指令

            for err_type, ce in seen_types.items():
                # 找出该类型的所有错误消息（用于更具体的描述）
                same_type_errors = [
                    c.original_message for c in classified
                    if c.error_type == err_type
                ]

                if err_type == CompileErrorType.UNKNOWN:
                    # CE-XX: 列出所有未识别错误，提示 LLM 自行判断
                    for raw_msg in same_type_errors[:2]:
                        instr = f"[CE-XX] Unrecognized compile error: {raw_msg[:150]}\nFix: Analyze the error message above and apply the appropriate fix."
                        instructions.append(instr)
                else:
                    # 已识别类型：生成一条带有类型标签的指令
                    # 如果有多条同类型错误，在指令中列举（最多2条）
                    if len(same_type_errors) > 1:
                        examples = "; ".join(
                            e[:80] for e in same_type_errors[:2]
                        )
                        instr = f"[{err_type}] {ce.fix_hint}\nErrors of this type: {examples}"
                    else:
                        instr = f"[{err_type}] {ce.fix_hint}"
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

        return instructions[:4]


# ════════════════════════════════════════════════════════════════════
# 集成入口
# ════════════════════════════════════════════════════════════════════

_analyzer = CompileErrorAnalyzer()


def enrich_diag_with_fix_hints(diag) -> List[str]:
    """从 TestDiag 对象生成额外的修复提示，供 Refiner 使用。"""
    return _analyzer.generate_fix_instructions(
        compile_errors=getattr(diag, 'compile_errors', []),
        exec_errors=getattr(diag, 'exec_errors', []),
        compile_ok=getattr(diag, 'compile_ok', True),
        exec_ok=getattr(diag, 'exec_ok', True),
    )


def get_error_summary(compile_errors: List[str], exec_errors: List[str]) -> str:
    """生成简洁的错误摘要文本。"""
    if not compile_errors and not exec_errors:
        return ""

    parts = []
    if compile_errors:
        classified = _analyzer.classify_compile_errors(compile_errors)
        # 去重后的类型列表
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