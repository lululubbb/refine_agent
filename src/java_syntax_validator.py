"""
java_syntax_validator.py
========================
Rule-based Validator：在调用 LLM 生成/修复测试之前，
用正则表达式快速检查 Java 源码中的常见语法问题。

设计原则：
  - 轻量、快速（无需 JVM 或 javalang）
  - 只检测"高置信度"的错误，避免误报
  - 返回结构化的诊断信息，便于注入 prompt 或日志记录
  - 作为 javalang.parse.parse() 之前的廉价前置过滤器

检测规则（CE = Compile Error 类别）：
  R-01  括号不匹配  { } ( ) [ ]
  R-02  缺少 package 声明（当代码含 import 时）
  R-03  缺少 class 声明
  R-04  缺少必要 import（JUnit5 / Mockito 常见类未 import）
  R-05  直接访问 private 成员（obj.privateField 模式）
  R-06  使用了 CSVFormat.Builder（已知旧版不存在的 API）
  R-07  assertThrows 使用了带参 lambda（e -> 而非 () ->）
  R-08  继承 final 类（匿名子类模式）
  R-09  缺少 throws Exception（含 checked exception 调用但方法未声明）
  R-10  空测试体（@Test 方法体内无任何语句）
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ════════════════════════════════════════════════════════════════════
# 诊断结果结构
# ════════════════════════════════════════════════════════════════════

@dataclass
class ValidationIssue:
    rule_id: str          # e.g. "R-01"
    severity: str         # "error" | "warning"
    message: str          # 人类可读的描述
    line_hint: int = -1   # 大致行号（-1 = 未知）
    fix_hint: str = ""    # 给 LLM 的简短修复提示

    def __str__(self) -> str:
        loc = f" (line ~{self.line_hint})" if self.line_hint > 0 else ""
        return f"[{self.rule_id}]{loc} {self.message}"


@dataclass
class ValidationResult:
    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    error_count: int = 0
    warning_count: int = 0

    def summary(self) -> str:
        if self.is_valid:
            return "OK (no issues found)"
        parts = []
        if self.error_count:
            parts.append(f"{self.error_count} error(s)")
        if self.warning_count:
            parts.append(f"{self.warning_count} warning(s)")
        return "INVALID: " + ", ".join(parts)

    def to_prompt_text(self, max_issues: int = 5) -> str:
        """生成可直接注入 LLM prompt 的问题摘要。"""
        if self.is_valid:
            return ""
        lines = ["## Pre-validation Issues (fix these FIRST before other changes):"]
        for issue in self.issues[:max_issues]:
            lines.append(f"  [{issue.rule_id}] {issue.message}")
            if issue.fix_hint:
                lines.append(f"    → Fix: {issue.fix_hint}")
        if len(self.issues) > max_issues:
            lines.append(f"  ... and {len(self.issues) - max_issues} more issues")
        return "\n".join(lines)


# ════════════════════════════════════════════════════════════════════
# 主验证器
# ════════════════════════════════════════════════════════════════════

class JavaSyntaxValidator:
    """
    对 Java 测试源码进行规则检查。

    用法：
        validator = JavaSyntaxValidator()
        result = validator.validate(java_source)
        if not result.is_valid:
            print(result.to_prompt_text())
    """

    # ── 已知的 checked exception 方法调用模式 ────────────────────────
    _CHECKED_EXC_PATTERNS = [
        re.compile(r'\bIOException\b'),
        re.compile(r'\bSQLException\b'),
        re.compile(r'\bParseException\b'),
        re.compile(r'\bCloneNotSupportedException\b'),
        re.compile(r'throws\s+\w*Exception'),
        # 常见会抛 IOException 的方法
        re.compile(r'\b(?:read|write|close|flush|parse|open|connect)\s*\('),
    ]

    # ── 常见需要 import 的 JUnit5/Mockito 类 ─────────────────────────
    _REQUIRED_IMPORTS = {
        r'\bAssertions\.': 'org.junit.jupiter.api.Assertions',
        r'\bassertEquals\b': 'org.junit.jupiter.api.Assertions (static import)',
        r'\bassertTrue\b':   'org.junit.jupiter.api.Assertions (static import)',
        r'\bassertFalse\b':  'org.junit.jupiter.api.Assertions (static import)',
        r'\bassertThrows\b': 'org.junit.jupiter.api.Assertions (static import)',
        r'\bassertNotNull\b':'org.junit.jupiter.api.Assertions (static import)',
        r'\b@Test\b':        'org.junit.jupiter.api.Test',
        r'\bmock\s*\(':      'org.mockito.Mockito (static import)',
        r'\bwhen\s*\(':      'org.mockito.Mockito (static import)',
        r'\bverify\s*\(':    'org.mockito.Mockito (static import)',
        r'\bMockitoAnnotations\b': 'org.mockito.MockitoAnnotations',
    }

    # ── 已知旧版不存在的 API ──────────────────────────────────────────
    _BANNED_APIS = [
        (re.compile(r'CSVFormat\.Builder'),
         "CSVFormat.Builder does not exist in Defects4J Csv versions. "
         "Use CSVFormat.DEFAULT.withXxx() chaining instead.",
         "CSVFormat.DEFAULT.withDelimiter(',').withQuote('\"')"),

        (re.compile(r'CSVFormat\.builder\s*\(\s*\)'),
         "CSVFormat.builder() does not exist. Use static factory methods.",
         "CSVFormat.DEFAULT"),
    ]

    def validate(self, source: str, strict: bool = False) -> ValidationResult:
        """
        对 Java 源码执行所有规则检查。

        Parameters
        ----------
        source : str
            Java 源码字符串
        strict : bool
            True 时将 warning 也计入 is_valid=False 的判定

        Returns
        -------
        ValidationResult
        """
        issues: List[ValidationIssue] = []

        issues.extend(self._check_bracket_balance(source))
        issues.extend(self._check_class_declaration(source))
        issues.extend(self._check_missing_imports(source))
        issues.extend(self._check_banned_apis(source))
        issues.extend(self._check_assert_throws_lambda(source))
        issues.extend(self._check_anonymous_final_subclass(source))
        issues.extend(self._check_empty_test_bodies(source))
        issues.extend(self._check_private_field_access(source))
        # R-09 is heuristic-only, emit as warning
        issues.extend(self._check_missing_throws(source))

        errors   = [i for i in issues if i.severity == "error"]
        warnings = [i for i in issues if i.severity == "warning"]

        is_valid = (len(errors) == 0) and (not strict or len(warnings) == 0)

        result = ValidationResult(
            is_valid=is_valid,
            issues=issues,
            error_count=len(errors),
            warning_count=len(warnings),
        )
        return result

    # ────────────────────────────────────────────────────────────────
    # R-01: 括号平衡检查
    # ────────────────────────────────────────────────────────────────

    def _check_bracket_balance(self, source: str) -> List[ValidationIssue]:
        issues = []
        # 去掉字符串字面量和注释，避免误报
        cleaned = self._strip_strings_and_comments(source)

        for open_b, close_b, name in [
            ('{', '}', 'curly brace'),
            ('(', ')', 'parenthesis'),
            ('[', ']', 'square bracket'),
        ]:
            count = cleaned.count(open_b) - cleaned.count(close_b)
            if count != 0:
                direction = "unclosed" if count > 0 else "extra closing"
                issues.append(ValidationIssue(
                    rule_id="R-01",
                    severity="error",
                    message=f"Unbalanced {name}: {abs(count)} {direction} '{open_b if count > 0 else close_b}'",
                    fix_hint=f"Check that every '{open_b}' has a matching '{close_b}'",
                ))
        return issues

    # ────────────────────────────────────────────────────────────────
    # R-03: class 声明检查
    # ────────────────────────────────────────────────────────────────

    def _check_class_declaration(self, source: str) -> List[ValidationIssue]:
        issues = []
        if not re.search(r'\bclass\s+\w+', source):
            issues.append(ValidationIssue(
                rule_id="R-03",
                severity="error",
                message="No class declaration found in the source code.",
                fix_hint="Ensure the output is a complete Java class starting with 'public class XxxTest {'",
            ))
        return issues

    # ────────────────────────────────────────────────────────────────
    # R-04: 缺少 import
    # ────────────────────────────────────────────────────────────────

    def _check_missing_imports(self, source: str) -> List[ValidationIssue]:
        issues = []
        # 提取已有 import 行
        existing_imports = set()
        for line in source.splitlines():
            stripped = line.strip()
            if stripped.startswith("import "):
                existing_imports.add(stripped)

        cleaned_no_imports = re.sub(r'^\s*import\s+.*;\s*$', '', source, flags=re.MULTILINE)

        for pattern_str, required_import in self._REQUIRED_IMPORTS.items():
            if re.search(pattern_str, cleaned_no_imports):
                # 检查 import 是否已存在（模糊匹配）
                import_class = required_import.split(" ")[0]  # 取第一个词（去掉括号说明）
                import_parts = import_class.split(".")
                if import_parts:
                    short_class = import_parts[-1]
                    already_imported = any(
                        short_class in imp or import_class.replace(".", "/") in imp.replace(".", "/")
                        for imp in existing_imports
                    )
                    if not already_imported and import_class not in ("static import",):
                        issues.append(ValidationIssue(
                            rule_id="R-04",
                            severity="warning",
                            message=f"Possibly missing import for `{short_class}` (expected: `import {import_class};`)",
                            fix_hint=f"Add: import {import_class};",
                        ))
        return issues

    # ────────────────────────────────────────────────────────────────
    # R-06: 已知旧版不存在的 API
    # ────────────────────────────────────────────────────────────────

    def _check_banned_apis(self, source: str) -> List[ValidationIssue]:
        issues = []
        cleaned = self._strip_strings_and_comments(source)
        for pattern, message, fix in self._BANNED_APIS:
            m = pattern.search(cleaned)
            if m:
                line_num = cleaned[:m.start()].count('\n') + 1
                issues.append(ValidationIssue(
                    rule_id="R-06",
                    severity="error",
                    message=message,
                    line_hint=line_num,
                    fix_hint=f"Replace with: {fix}",
                ))
        return issues

    # ────────────────────────────────────────────────────────────────
    # R-07: assertThrows 带参 lambda
    # ────────────────────────────────────────────────────────────────

    def _check_assert_throws_lambda(self, source: str) -> List[ValidationIssue]:
        issues = []
        # 匹配 assertThrows(..., e -> ...) 或 assertThrows(..., (e) -> ...)
        pattern = re.compile(
            r'assertThrows\s*\([^,]+,\s*(?:\(\s*\w+\s*\)|\w+)\s*->',
            re.DOTALL
        )
        cleaned = self._strip_strings_and_comments(source)
        for m in pattern.finditer(cleaned):
            line_num = cleaned[:m.start()].count('\n') + 1
            issues.append(ValidationIssue(
                rule_id="R-07",
                severity="error",
                message="assertThrows() lambda must be zero-argument: use `() ->` not `e ->`",
                line_hint=line_num,
                fix_hint="Change `e -> method()` to `() -> method()`",
            ))
        return issues

    # ────────────────────────────────────────────────────────────────
    # R-08: 继承 final 类（匿名子类）
    # ────────────────────────────────────────────────────────────────

    def _check_anonymous_final_subclass(self, source: str) -> List[ValidationIssue]:
        issues = []
        # 检测 new SomeClass(...) { ... } 匿名子类模式，但排除 Runnable/Thread 等合理情况
        # 这里只检测常见被测类的子类化（如果类名含 CSV/Record/Parser）
        pattern = re.compile(
            r'new\s+((?:CSV|Lexer|Token|Printer|Parser|Reader|Writer)\w*)\s*\([^)]*\)\s*\{',
            re.IGNORECASE
        )
        cleaned = self._strip_strings_and_comments(source)
        for m in pattern.finditer(cleaned):
            class_name = m.group(1)
            line_num = cleaned[:m.start()].count('\n') + 1
            issues.append(ValidationIssue(
                rule_id="R-08",
                severity="warning",
                message=f"Anonymous subclass of `{class_name}` detected. "
                        f"If this class is final, this will cause a compile error.",
                line_hint=line_num,
                fix_hint=f"If `{class_name}` is final, use Mockito.spy(new {class_name}(...)) instead.",
            ))
        return issues

    # ────────────────────────────────────────────────────────────────
    # R-09: 缺少 throws Exception
    # ────────────────────────────────────────────────────────────────

    def _check_missing_throws(self, source: str) -> List[ValidationIssue]:
        """
        启发式检查：@Test 方法体内含有可能抛 checked exception 的调用，
        但方法签名没有 throws 声明。
        """
        issues = []
        # 找所有 @Test 方法
        test_method_pattern = re.compile(
            r'@Test\s+(?:[\w@\s]*?\s+)?void\s+(\w+)\s*\(\s*\)\s*(?:throws\s+[\w,\s]+)?\{',
            re.MULTILINE
        )
        for m in test_method_pattern.finditer(source):
            method_name = m.group(1)
            has_throws = 'throws' in m.group(0)
            if has_throws:
                continue
            # 检查方法体（粗略截取到下一个 @Test 或类结束）
            body_start = m.end()
            # 找到方法体的结束括号
            body_end = self._find_closing_brace(source, body_start - 1)
            method_body = source[body_start:body_end] if body_end > body_start else ""

            has_checked = any(
                p.search(method_body) for p in self._CHECKED_EXC_PATTERNS
            )
            if has_checked:
                line_num = source[:m.start()].count('\n') + 1
                issues.append(ValidationIssue(
                    rule_id="R-09",
                    severity="warning",
                    message=f"Test method `{method_name}()` may use checked exceptions "
                            f"but does not declare `throws Exception`.",
                    line_hint=line_num,
                    fix_hint=f"Change signature to: `void {method_name}() throws Exception {{`",
                ))
        return issues

    # ────────────────────────────────────────────────────────────────
    # R-10: 空测试体
    # ────────────────────────────────────────────────────────────────

    def _check_empty_test_bodies(self, source: str) -> List[ValidationIssue]:
        issues = []
        # 匹配 @Test ... void xxx() ... { } 或 { /* 只有注释 */ }
        pattern = re.compile(
            r'@Test\s+(?:[\w@\s]*?\s+)?void\s+(\w+)\s*\([^)]*\)\s*(?:throws\s+[\w,\s]+)?\{([^}]*)\}',
            re.MULTILINE | re.DOTALL
        )
        for m in pattern.finditer(source):
            method_name = m.group(1)
            body = m.group(2)
            # 去掉空白和注释后是否为空
            cleaned_body = re.sub(r'//[^\n]*', '', body)
            cleaned_body = re.sub(r'/\*.*?\*/', '', cleaned_body, flags=re.DOTALL)
            cleaned_body = cleaned_body.strip()
            if not cleaned_body:
                line_num = source[:m.start()].count('\n') + 1
                issues.append(ValidationIssue(
                    rule_id="R-10",
                    severity="warning",
                    message=f"Test method `{method_name}()` has an empty body — no assertions.",
                    line_hint=line_num,
                    fix_hint="Add at least one assertion or method call to make this test meaningful.",
                ))
        return issues

    # ────────────────────────────────────────────────────────────────
    # R-05: 直接访问 private 字段（启发式）
    # ────────────────────────────────────────────────────────────────

    def _check_private_field_access(self, source: str) -> List[ValidationIssue]:
        """
        启发式：检测 obj.fieldName 的访问模式，
        其中 fieldName 为典型的 private 字段名（小写开头、非公开方法）。
        仅在字段名出现在文档中的常见 private 字段列表时警告。
        """
        issues = []
        # 常见被私有字段直接访问的模式（不含括号 → 非方法调用）
        # 例如 reader.lastChar, parser.lineNumber
        known_private_fields = [
            'lastChar', 'lastRead', 'lineCounter', 'lineNumber',
            'charIndex', 'pos', 'buf', 'buffer', 'closed',
        ]
        cleaned = self._strip_strings_and_comments(source)
        for field in known_private_fields:
            # 匹配 someVar.fieldName（不跟括号）
            pattern = re.compile(rf'\w+\.{re.escape(field)}(?!\s*\()')
            m = pattern.search(cleaned)
            if m:
                line_num = cleaned[:m.start()].count('\n') + 1
                issues.append(ValidationIssue(
                    rule_id="R-05",
                    severity="warning",
                    message=f"Possible direct access to private field `{field}` via `{m.group()}`.",
                    line_hint=line_num,
                    fix_hint=f"Use reflection: Field f = ClassName.class.getDeclaredField(\"{field}\"); "
                             f"f.setAccessible(true); Object val = f.get(instance);",
                ))
        return issues

    # ────────────────────────────────────────────────────────────────
    # 工具函数
    # ────────────────────────────────────────────────────────────────

    @staticmethod
    def _strip_strings_and_comments(source: str) -> str:
        """
        去掉 Java 字符串字面量（"..."）、字符字面量（'.'）和注释（// ... 和 /* ... */），
        以避免括号平衡、API 检测等规则误报。
        """
        result = []
        i = 0
        n = len(source)
        while i < n:
            # 块注释
            if source[i:i+2] == '/*':
                end = source.find('*/', i + 2)
                if end == -1:
                    # 未闭合的块注释：用空格替换到末尾
                    result.append(' ' * (n - i))
                    break
                result.append(' ' * (end + 2 - i))
                i = end + 2
            # 行注释
            elif source[i:i+2] == '//':
                end = source.find('\n', i + 2)
                if end == -1:
                    result.append(' ' * (n - i))
                    break
                result.append(' ' * (end - i))
                i = end
            # 字符串字面量
            elif source[i] == '"':
                j = i + 1
                while j < n:
                    if source[j] == '\\':
                        j += 2
                        continue
                    if source[j] == '"':
                        j += 1
                        break
                    j += 1
                result.append('"' + ' ' * (j - i - 2) + '"')
                i = j
            # 字符字面量
            elif source[i] == "'":
                j = i + 1
                while j < n:
                    if source[j] == '\\':
                        j += 2
                        continue
                    if source[j] == "'":
                        j += 1
                        break
                    j += 1
                result.append("'" + ' ' * max(0, j - i - 2) + "'")
                i = j
            else:
                result.append(source[i])
                i += 1
        return ''.join(result)

    @staticmethod
    def _find_closing_brace(source: str, open_pos: int) -> int:
        """从 open_pos（应为 '{' 的位置）找到对应的 '}'，返回其位置+1。"""
        depth = 0
        i = open_pos
        n = len(source)
        while i < n:
            if source[i] == '{':
                depth += 1
            elif source[i] == '}':
                depth -= 1
                if depth == 0:
                    return i + 1
            i += 1
        return n  # 未找到匹配，返回末尾


# ════════════════════════════════════════════════════════════════════
# 便捷函数（供外部直接调用）
# ════════════════════════════════════════════════════════════════════

_default_validator = JavaSyntaxValidator()


def validate_java(source: str, strict: bool = False) -> ValidationResult:
    """快速验证 Java 源码，返回 ValidationResult。"""
    return _default_validator.validate(source, strict=strict)


def get_validation_prompt_text(source: str, max_issues: int = 4) -> str:
    """
    验证 Java 源码并返回可注入 LLM prompt 的问题文本。
    若无问题则返回空字符串。
    """
    result = validate_java(source)
    if result.is_valid:
        return ""
    return result.to_prompt_text(max_issues=max_issues)


def has_critical_errors(source: str) -> bool:
    """快速判断是否存在会导致编译失败的关键错误（仅检测 error 级别）。"""
    result = validate_java(source)
    return result.error_count > 0