"""
java_syntax_validator.py  (v2 — 动态规则版)
============================================

修复：
  R-01（括号平衡）：
    - 旧版：原始字符计数，与 javalang/编译器重叠，去掉
    - 新版：只检测 assertThrows/assertAll 中常见的 lambda 括号失配
      （这是 LLM 频繁犯的特定错误，比通用括号计数更有价值）

  R-05（private 字段）：
    - 旧版：硬编码 ['lastChar', 'lastRead', 'lineCounter', ...] 固定列表，只对特定类有效
    - 新版：从 focal class 上下文动态提取 private 字段名，适用所有项目

  R-08（继承 final 类）：
    - 旧版：正则只匹配 CSV/Lexer/Token/Parser/Reader/Writer 等前缀
    - 新版：从 focal class 上下文动态提取已知 final 类名，
      同时保留通用的 `new XxxClass(...) {` 匿名子类检测

  其他改进：
    - 新增 R-11：反射方法名字符串硬编码检测（常见错误：字段名拼错）
    - validate() 新增 focal_class_context 参数，支持动态规则
    - 去掉与 javalang 重叠的 R-01，改为更有针对性的 lambda 检查
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Set


# ════════════════════════════════════════════════════════════════════
# 诊断结果结构
# ════════════════════════════════════════════════════════════════════

@dataclass
class ValidationIssue:
    rule_id: str
    severity: str         # "error" | "warning"
    message: str
    line_hint: int = -1
    fix_hint: str = ""

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
# 上下文提取工具
# ════════════════════════════════════════════════════════════════════

def extract_private_fields_from_context(focal_class_context: str) -> Set[str]:
    """
    从 focal class 上下文（d1/d3 的 information/full_fm 字段）中
    动态提取 private 字段名，用于 R-05 规则。

    匹配模式：
      private [static] [final] Type fieldName;
      private [static] [final] Type fieldName = ...;
    """
    field_names: Set[str] = set()
    if not focal_class_context:
        return field_names

    pattern = re.compile(
        r'\bprivate\b[^;{]*?\b(\w+)\s*(?:=\s*[^;]+)?;',
        re.MULTILINE
    )
    for m in pattern.finditer(focal_class_context):
        candidate = m.group(1).strip()
        # 过滤掉关键字和类型名（大写开头的是类型，不是字段名）
        if (candidate and
                not candidate[0].isupper() and
                candidate not in {'this', 'super', 'void', 'null', 'true', 'false',
                                   'int', 'long', 'double', 'float', 'boolean',
                                   'byte', 'char', 'short', 'final', 'static'}):
            field_names.add(candidate)
    return field_names


def extract_final_classes_from_context(focal_class_context: str) -> Set[str]:
    """
    从 focal class 上下文中动态提取 final 类名，用于 R-08 规则。
    匹配：public final class Xxx
    """
    final_classes: Set[str] = set()
    if not focal_class_context:
        return final_classes

    for m in re.finditer(r'\bfinal\s+class\s+(\w+)', focal_class_context):
        final_classes.add(m.group(1))
    return final_classes


def extract_class_name_from_context(focal_class_context: str) -> str:
    """从上下文中提取被测类名（用于构造函数匹配）。"""
    if not focal_class_context:
        return ""
    m = re.search(r'\bclass\s+(\w+)', focal_class_context)
    return m.group(1) if m else ""


# ════════════════════════════════════════════════════════════════════
# 主验证器
# ════════════════════════════════════════════════════════════════════

class JavaSyntaxValidator:
    """
    对 Java 测试源码进行规则检查。
    支持通过 focal_class_context 传入上下文，实现动态规则。
    """

    # ── 已知的 checked exception 方法调用模式 ────────────────────────
    _CHECKED_EXC_PATTERNS = [
        re.compile(r'\bIOException\b'),
        re.compile(r'\bSQLException\b'),
        re.compile(r'\bParseException\b'),
        re.compile(r'\bCloneNotSupportedException\b'),
        re.compile(r'throws\s+\w*Exception'),
        re.compile(r'\b(?:read|write|close|flush|parse|open|connect)\s*\('),
    ]

    # ── 已知旧版不存在的 API（保留静态部分，动态部分从上下文提取）───────
    _BANNED_APIS = [
        (re.compile(r'CSVFormat\.Builder'),
         "CSVFormat.Builder does not exist in Defects4J Csv versions. "
         "Use CSVFormat.DEFAULT.withXxx() chaining instead.",
         "CSVFormat.DEFAULT.withDelimiter(',').withQuote('\"')"),

        (re.compile(r'CSVFormat\.builder\s*\(\s*\)'),
         "CSVFormat.builder() does not exist. Use static factory methods.",
         "CSVFormat.DEFAULT"),
    ]

    def validate(
        self,
        source: str,
        strict: bool = False,
        focal_class_context: str = "",    # ★ 新增：传入上下文以启用动态规则
    ) -> ValidationResult:
        """
        对 Java 源码执行所有规则检查。

        Parameters
        ----------
        source               : Java 源码字符串
        strict               : True 时 warning 也影响 is_valid
        focal_class_context  : focal class 的源码上下文（d1 information 或 d3 full_fm）
                               传入后启用动态 R-05/R-08 规则
        """
        issues: List[ValidationIssue] = []

        # ── 动态提取上下文信息 ────────────────────────────────────────
        private_fields: Set[str] = set()
        final_classes: Set[str] = set()
        if focal_class_context:
            private_fields = extract_private_fields_from_context(focal_class_context)
            final_classes  = extract_final_classes_from_context(focal_class_context)

        # ── 规则检查 ──────────────────────────────────────────────────
        # R-01 已删除（与 javalang 重叠），改为 R-01b（lambda 括号检查）
        issues.extend(self._check_lambda_bracket_mismatch(source))
        issues.extend(self._check_class_declaration(source))
        issues.extend(self._check_banned_apis(source))
        issues.extend(self._check_assert_throws_lambda(source))
        issues.extend(self._check_anonymous_subclass(source, final_classes))
        issues.extend(self._check_missing_throws(source))
        issues.extend(self._check_empty_test_bodies(source))
        issues.extend(self._check_private_field_access_dynamic(source, private_fields))
        issues.extend(self._check_reflection_field_names(source, private_fields))

        errors   = [i for i in issues if i.severity == "error"]
        warnings = [i for i in issues if i.severity == "warning"]

        is_valid = (len(errors) == 0) and (not strict or len(warnings) == 0)
        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            error_count=len(errors),
            warning_count=len(warnings),
        )

    # ────────────────────────────────────────────────────────────────
    # R-01b: Lambda 括号失配（assertThrows/assertAll 专项检查）
    # 替代旧的通用括号计数（与编译器重叠）
    # ────────────────────────────────────────────────────────────────

    def _check_lambda_bracket_mismatch(self, source: str) -> List[ValidationIssue]:
        """
        检测 assertThrows/assertAll 中常见的 lambda 语法错误。
        这是 LLM 频繁犯的错误：
          assertThrows(Foo.class, () -> {
              obj.method();
          );  ← 少了一个 }
        """
        issues = []
        cleaned = self._strip_strings_and_comments(source)

        # 找所有 assertThrows/assertAll/assertDoesNotThrow 调用
        pattern = re.compile(
            r'\bassert(?:Throws|All|DoesNotThrow)\s*\(',
            re.IGNORECASE
        )
        for m in pattern.finditer(cleaned):
            # 找到 lambda 体的 { ... }，检查是否平衡
            start = m.end()
            depth_paren = 1
            depth_brace = 0
            in_lambda = False
            i = start
            while i < len(cleaned) and depth_paren > 0:
                c = cleaned[i]
                if c == '(':
                    depth_paren += 1
                elif c == ')':
                    depth_paren -= 1
                elif c == '{':
                    depth_brace += 1
                    in_lambda = True
                elif c == '}':
                    depth_brace -= 1
                i += 1
            if in_lambda and depth_brace != 0:
                line_num = source[:m.start()].count('\n') + 1
                issues.append(ValidationIssue(
                    rule_id="R-01b",
                    severity="error",
                    message=f"Unbalanced braces inside {m.group().strip('(')} lambda body "
                            f"(depth={depth_brace:+d})",
                    line_hint=line_num,
                    fix_hint="Check that lambda body `() -> { ... }` has matching braces",
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
                fix_hint="Ensure the output is a complete Java class: `public class XxxTest {`",
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
    # R-08: 继承 final 类（动态版）
    # ────────────────────────────────────────────────────────────────

    def _check_anonymous_subclass(
        self, source: str, final_classes: Set[str]
    ) -> List[ValidationIssue]:
        """
        动态版：从上下文提取 final 类名，检测是否被匿名子类化。
        同时保留静态的通用检测（任何 new XxxClass(...) { 匿名子类）。
        """
        issues = []
        cleaned = self._strip_strings_and_comments(source)

        # ── 动态检查：上下文中已知的 final 类 ────────────────────────
        for class_name in final_classes:
            pattern = re.compile(
                rf'new\s+{re.escape(class_name)}\s*\([^)]*\)\s*\{{',
                re.DOTALL
            )
            m = pattern.search(cleaned)
            if m:
                line_num = cleaned[:m.start()].count('\n') + 1
                issues.append(ValidationIssue(
                    rule_id="R-08",
                    severity="error",
                    message=f"`{class_name}` is a final class and cannot be subclassed.",
                    line_hint=line_num,
                    fix_hint=f"Use Mockito.spy(new {class_name}(...)) instead of anonymous subclass",
                ))

        # ── 静态检查：通用匿名子类检测（warning 级别）─────────────────
        # 检测所有 new XxxClass(...) { 模式（不只是已知 final 类）
        general_pattern = re.compile(
            r'new\s+([A-Z]\w+)\s*\([^)]*\)\s*\{',
            re.DOTALL
        )
        known_anon_bases = {'Runnable', 'Callable', 'Thread', 'Comparator',
                             'ActionListener', 'Serializable'}
        for m in general_pattern.finditer(cleaned):
            class_name = m.group(1)
            # 跳过已知合法的匿名子类基类 和 已在动态检查中报过的
            if class_name in known_anon_bases or class_name in final_classes:
                continue
            line_num = cleaned[:m.start()].count('\n') + 1
            issues.append(ValidationIssue(
                rule_id="R-08",
                severity="warning",
                message=f"Anonymous subclass of `{class_name}` detected. "
                        f"If `{class_name}` is final or mocked, this will fail.",
                line_hint=line_num,
                fix_hint=f"If `{class_name}` is final: use Mockito.spy(new {class_name}(...))",
            ))

        return issues

    # ────────────────────────────────────────────────────────────────
    # R-05: private 字段直接访问（动态版）
    # ────────────────────────────────────────────────────────────────

    def _check_private_field_access_dynamic(
        self, source: str, private_fields: Set[str]
    ) -> List[ValidationIssue]:
        """
        动态版：基于从上下文提取的 private 字段名，
        检测是否有直接访问（obj.fieldName，不跟括号）。
        """
        issues = []
        if not private_fields:
            return issues

        cleaned = self._strip_strings_and_comments(source)

        for field_name in private_fields:
            # 匹配 someVar.fieldName（不跟括号 → 不是方法调用）
            pattern = re.compile(
                rf'\b\w+\.{re.escape(field_name)}\s*(?![(\w])'
            )
            m = pattern.search(cleaned)
            if m:
                line_num = cleaned[:m.start()].count('\n') + 1
                issues.append(ValidationIssue(
                    rule_id="R-05",
                    severity="warning",
                    message=f"Possible direct access to private field `{field_name}` "
                            f"via `{m.group().strip()}`.",
                    line_hint=line_num,
                    fix_hint=(
                        f"Use reflection: "
                        f"Field f = ClassName.class.getDeclaredField(\"{field_name}\"); "
                        f"f.setAccessible(true); Object val = f.get(instance);"
                    ),
                ))

        return issues

    # ────────────────────────────────────────────────────────────────
    # R-11: 反射字段名字符串可能拼错（新增）
    # ────────────────────────────────────────────────────────────────

    def _check_reflection_field_names(
        self, source: str, private_fields: Set[str]
    ) -> List[ValidationIssue]:
        """
        检测 getDeclaredField("xxx") 中的字段名是否在已知字段列表中。
        如果传入了 private_fields，则检查字符串是否与已知字段名匹配。
        """
        issues = []
        if not private_fields:
            return issues

        cleaned = self._strip_strings_and_comments(source)

        # 找所有 getDeclaredField("xxx") 或 getDeclaredMethod("xxx") 调用
        for m in re.finditer(r'getDeclaredField\s*\(\s*"(\w+)"\s*\)', source):
            field_name = m.group(1)
            if field_name not in private_fields:
                # 尝试找最相似的字段名
                similar = _find_similar(field_name, private_fields)
                line_num = source[:m.start()].count('\n') + 1
                hint = (f"Available private fields: {sorted(private_fields)[:8]}"
                        + (f"; did you mean `{similar}`?" if similar else ""))
                issues.append(ValidationIssue(
                    rule_id="R-11",
                    severity="warning",
                    message=f"getDeclaredField(\"{field_name}\") — "
                            f"field `{field_name}` not found in known private fields.",
                    line_hint=line_num,
                    fix_hint=hint,
                ))

        return issues

    # ────────────────────────────────────────────────────────────────
    # R-09: 缺少 throws Exception
    # ────────────────────────────────────────────────────────────────

    def _check_missing_throws(self, source: str) -> List[ValidationIssue]:
        issues = []
        test_method_pattern = re.compile(
            r'@Test\s+(?:[\w@\s]*?\s+)?void\s+(\w+)\s*\(\s*\)\s*(?:throws\s+[\w,\s]+)?\{',
            re.MULTILINE
        )
        for m in test_method_pattern.finditer(source):
            method_name = m.group(1)
            has_throws = 'throws' in m.group(0)
            if has_throws:
                continue
            body_start = m.end()
            body_end = self._find_closing_brace(source, body_start - 1)
            method_body = source[body_start:body_end] if body_end > body_start else ""
            has_checked = any(p.search(method_body) for p in self._CHECKED_EXC_PATTERNS)
            if has_checked:
                line_num = source[:m.start()].count('\n') + 1
                issues.append(ValidationIssue(
                    rule_id="R-09",
                    severity="warning",
                    message=f"Test method `{method_name}()` may use checked exceptions "
                            f"but does not declare `throws Exception`.",
                    line_hint=line_num,
                    fix_hint=f"Change to: `void {method_name}() throws Exception {{`",
                ))
        return issues

    # ────────────────────────────────────────────────────────────────
    # R-10: 空测试体
    # ────────────────────────────────────────────────────────────────

    def _check_empty_test_bodies(self, source: str) -> List[ValidationIssue]:
        issues = []
        pattern = re.compile(
            r'@Test\s+(?:[\w@\s]*?\s+)?void\s+(\w+)\s*\([^)]*\)\s*(?:throws\s+[\w,\s]+)?\{([^}]*)\}',
            re.MULTILINE | re.DOTALL
        )
        for m in pattern.finditer(source):
            method_name = m.group(1)
            body = m.group(2)
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
                    fix_hint="Add at least one assertion to make this test meaningful.",
                ))
        return issues

    # ────────────────────────────────────────────────────────────────
    # 工具函数
    # ────────────────────────────────────────────────────────────────

    @staticmethod
    def _strip_strings_and_comments(source: str) -> str:
        result = []
        i = 0
        n = len(source)
        while i < n:
            if source[i:i+2] == '/*':
                end = source.find('*/', i + 2)
                if end == -1:
                    result.append(' ' * (n - i))
                    break
                result.append(' ' * (end + 2 - i))
                i = end + 2
            elif source[i:i+2] == '//':
                end = source.find('\n', i + 2)
                if end == -1:
                    result.append(' ' * (n - i))
                    break
                result.append(' ' * (end - i))
                i = end
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
        return n


# ════════════════════════════════════════════════════════════════════
# 相似字符串查找（用于 R-11 的字段名建议）
# ════════════════════════════════════════════════════════════════════

def _find_similar(name: str, candidates: Set[str], threshold: int = 2) -> Optional[str]:
    """找与 name 编辑距离最小的候选（简单 Levenshtein 近似）。"""
    best, best_dist = None, float('inf')
    for c in candidates:
        dist = _edit_distance(name.lower(), c.lower())
        if dist < best_dist:
            best, best_dist = c, dist
    return best if best_dist <= threshold else None


def _edit_distance(s1: str, s2: str) -> int:
    if len(s1) > len(s2):
        s1, s2 = s2, s1
    prev = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr = [i + 1]
        for j, c2 in enumerate(s2):
            curr.append(min(prev[j + 1] + 1, curr[j] + 1,
                            prev[j] + (0 if c1 == c2 else 1)))
        prev = curr
    return prev[len(s2)]


# ════════════════════════════════════════════════════════════════════
# 便捷函数（供外部直接调用）
# ════════════════════════════════════════════════════════════════════

_default_validator = JavaSyntaxValidator()


def validate_java(
    source: str,
    strict: bool = False,
    focal_class_context: str = "",
) -> ValidationResult:
    """快速验证 Java 源码，返回 ValidationResult。"""
    return _default_validator.validate(
        source, strict=strict, focal_class_context=focal_class_context
    )


def get_validation_prompt_text(
    source: str,
    max_issues: int = 4,
    focal_class_context: str = "",
) -> str:
    result = validate_java(source, focal_class_context=focal_class_context)
    if result.is_valid:
        return ""
    return result.to_prompt_text(max_issues=max_issues)


def has_critical_errors(source: str, focal_class_context: str = "") -> bool:
    result = validate_java(source, focal_class_context=focal_class_context)
    return result.error_count > 0