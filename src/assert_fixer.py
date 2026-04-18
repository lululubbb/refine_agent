"""
assert_fixer.py
===============
MutAP 风格的断言修复器。

核心思路（来自 MutAP 论文）：
  LLM 生成的断言预期值往往是错误的（hallucination）。
  通过真实运行被测方法（PUT），用实际输出替换错误的预期值。

流程：
  1. 解析 Java 测试文件，提取所有 assertEquals/assertTrue 等断言
  2. 用 javac + java 运行一个小型 harness 来获取每个断言的真实输出
  3. 如果真实输出与断言预期不符，替换预期值
  4. 如果运行报错（输入不合法），丢弃该断言
  5. 返回修复后的 Java 源码

重要设计决策：
  - 只修复 assertEquals(expected, actual) 类型的断言（有明确预期值）
  - 不修复 assertNotNull/assertTrue/assertThrows 等（这些不需要精确值）
  - 修复失败时保留原始断言（不丢弃整个测试方法）
  - 对私有字段直接访问产生的编译错误：将相关断言替换为 assertNotNull/非null检查
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import logging
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

HERE = os.path.dirname(os.path.abspath(__file__))

# 最大允许修复的断言数量（避免运行时间过长）
_MAX_ASSERTIONS_TO_FIX = 20
# 单次运行超时（秒）
_RUN_TIMEOUT = 10


# ════════════════════════════════════════════════════════════════════
# 断言解析
# ════════════════════════════════════════════════════════════════════

# 匹配 assertEquals(expected, actual) 或 assertEquals(message, expected, actual)
_ASSERT_EQUALS_PATTERN = re.compile(
    r'(assertEquals\s*\()'           # 方法调用开始
    r'([^;]+?)'                      # 参数（延迟匹配）
    r'(\s*\)\s*;)',                  # 结束
    re.DOTALL
)

# 匹配私有字段直接访问：obj.privateField（不是方法调用）
_PRIVATE_FIELD_ACCESS = re.compile(
    r'\b(\w+)\.([a-z]\w*)\b(?!\s*[\(\[])',  # 小写开头的字段访问
)


def _is_literal(s: str) -> bool:
    """判断字符串是否是字面量（数字、字符串、布尔值、null、char）"""
    s = s.strip()
    if s in ('true', 'false', 'null'):
        return True
    if re.match(r'^-?\d+(\.\d+)?[LlFfDd]?$', s):
        return True
    if s.startswith('"') and s.endswith('"'):
        return True
    if s.startswith("'") and s.endswith("'"):
        return True
    return False


def _split_assert_args(args_str: str) -> List[str]:
    """
    分割 assertEquals 的参数，正确处理嵌套括号。
    例：assertEquals("msg", foo(a, b), bar(c))  → ["\"msg\"", "foo(a, b)", "bar(c)"]
    """
    args = []
    depth = 0
    current = []
    for ch in args_str:
        if ch == '(':
            depth += 1
            current.append(ch)
        elif ch == ')':
            depth -= 1
            current.append(ch)
        elif ch == ',' and depth == 0:
            args.append(''.join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        args.append(''.join(current).strip())
    return args


# ════════════════════════════════════════════════════════════════════
# 私有字段访问检测与修复
# ════════════════════════════════════════════════════════════════════

def _fix_private_field_assertions(java_source: str, private_fields: List[str]) -> str:
    """
    将直接访问私有字段的 assertEquals 替换为 assertNotNull 或注释掉。
    这解决了"直接访问私有字段导致编译错误"的问题。
    """
    if not private_fields:
        return java_source

    lines = java_source.splitlines(keepends=True)
    result = []

    for line in lines:
        fixed_line = line
        # 检查这行是否包含 assertEquals 且访问了私有字段
        if 'assertEquals' in line:
            for field in private_fields:
                # 直接字段访问模式：obj.field 或 .field
                pattern = re.compile(rf'\.\s*{re.escape(field)}\s*[,\)]')
                if pattern.search(line):
                    # 提取缩进
                    indent = re.match(r'^(\s*)', line).group(1)
                    # 替换为注释（保留原始意图但不编译）
                    fixed_line = f"{indent}// [AssertFixer] Removed direct private field access: {line.strip()}\n"
                    logger.debug("[AssertFixer] Removed private field assertion: %s", line.strip())
                    break
        result.append(fixed_line)

    return ''.join(result)


# ════════════════════════════════════════════════════════════════════
# 核心修复逻辑
# ════════════════════════════════════════════════════════════════════

class AssertFixer:
    """
    MutAP 风格的断言修复器。
    通过编译运行被测类 + 测试方法来获取真实输出，修正错误断言。
    """

    def __init__(
        self,
        project_dir: str,
        junit_jar: str = "",
        mockito_jar: str = "",
        log4j_jar: str = "",
        timeout: int = _RUN_TIMEOUT,
    ):
        self.project_dir = project_dir
        self.junit_jar = junit_jar
        self.mockito_jar = mockito_jar
        self.log4j_jar = log4j_jar
        self.timeout = timeout

        # 构建 classpath
        import glob as _glob
        dep_jars = _glob.glob(os.path.join(project_dir, "**/*.jar"), recursive=True)
        build_dir = os.path.join(project_dir, "target", "classes")
        cp_parts = [build_dir] + dep_jars
        if junit_jar:
            cp_parts.extend(junit_jar.split(':'))
        if mockito_jar:
            cp_parts.extend(mockito_jar.split(':'))
        if log4j_jar:
            cp_parts.extend(log4j_jar.split(':'))
        self.classpath = ':'.join([p for p in cp_parts if p])

    def fix(
        self,
        java_source: str,
        class_name: str,
        package: str = "",
        private_fields: Optional[List[str]] = None,
    ) -> str:
        """
        修复 Java 测试源码中的错误断言。

        Parameters
        ----------
        java_source     : 原始 Java 测试源码
        class_name      : 测试类名（如 Token_1_1Test）
        package         : 包名（如 org.apache.commons.csv）
        private_fields  : 已知的私有字段名列表（用于移除直接访问）

        Returns
        -------
        修复后的 Java 源码
        """
        fixed = java_source

        # Step 1: 移除私有字段直接访问的断言
        if private_fields:
            fixed = _fix_private_field_assertions(fixed, private_fields)
            logger.info("[AssertFixer] Step 1: private field assertions removed")

        # Step 2: 修复 assertEquals 的错误预期值
        fixed = self._fix_assertEquals_values(fixed, class_name, package)

        return fixed

    def _fix_assertEquals_values(
        self, java_source: str, class_name: str, package: str
    ) -> str:
        """
        编译并运行测试，捕获 AssertionError 来识别错误断言，
        然后用真实值替换错误的预期值。

        策略：
        - 用 javac 编译测试文件
        - 如果编译失败，不做 assertEquals 修复（只做 Step 1 的私有字段清理）
        - 如果编译成功，用 JUnit 运行，解析 AssertionError 输出
        - 从 "expected:<X> but was:<Y>" 中提取真实值 Y，替换错误的预期值 X
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # 写入测试文件
            test_file = os.path.join(tmpdir, f"{class_name}.java")
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write(java_source)

            # 编译
            compile_ok, compile_err = self._compile(test_file, tmpdir)
            if not compile_ok:
                logger.debug("[AssertFixer] compile failed, skip assertEquals fix: %s",
                             compile_err[:200])
                return java_source  # 编译失败，不修复（保留原始，让 TestRunner 处理）

            # 运行测试
            full_class = f"{package}.{class_name}" if package else class_name
            run_output = self._run_tests(tmpdir, full_class)

            if not run_output:
                return java_source

            # 解析 AssertionError，提取 expected vs actual
            fixes = self._parse_assertion_errors(run_output)
            if not fixes:
                logger.info("[AssertFixer] No assertEquals errors found, all assertions correct")
                return java_source

            logger.info("[AssertFixer] Found %d assertEquals errors to fix", len(fixes))

            # 替换错误的预期值
            fixed = self._apply_fixes(java_source, fixes)
            return fixed

    def _compile(self, test_file: str, output_dir: str) -> Tuple[bool, str]:
        """编译单个测试文件"""
        cmd = [
            'javac',
            '-d', output_dir,
            '-cp', f"{output_dir}:{self.classpath}",
            test_file
        ]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            )
            return result.returncode == 0, result.stderr
        except Exception as e:
            return False, str(e)

    def _run_tests(self, class_dir: str, full_class_name: str) -> str:
        """运行测试，返回输出（含 AssertionError 信息）"""
        cmd = [
            'java',
            '-cp', f"{class_dir}:{self.classpath}",
            'org.junit.platform.console.ConsoleLauncher',
            '--disable-banner',
            '--disable-ansi-colors',
            '--details=verbose',
            '--select-class', full_class_name,
        ]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=self.timeout
            )
            return result.stdout + '\n' + result.stderr
        except subprocess.TimeoutExpired:
            return ""
        except Exception as e:
            logger.debug("[AssertFixer] run error: %s", e)
            return ""

    def _parse_assertion_errors(self, output: str) -> List[Tuple[str, str]]:
        """
        从 JUnit 输出中解析 AssertionError。
        返回 [(wrong_expected, actual_value), ...] 列表。

        JUnit 5 输出格式：
          expected: <3> but was: <4>
          ==> expected: <"hello"> but was: <"world">
        JUnit 4 格式：
          expected:<3> but was:<4>
        """
        fixes = []
        seen = set()

        # JUnit 5 格式
        pattern5 = re.compile(
            r'expected:\s*<([^>]*)>\s*but was:\s*<([^>]*)>',
            re.IGNORECASE
        )
        # JUnit 4 格式
        pattern4 = re.compile(
            r'expected:<([^>]*)> but was:<([^>]*)>',
            re.IGNORECASE
        )

        for pattern in [pattern5, pattern4]:
            for m in pattern.finditer(output):
                expected_val = m.group(1).strip()
                actual_val = m.group(2).strip()
                key = (expected_val, actual_val)
                if key not in seen and expected_val != actual_val:
                    seen.add(key)
                    fixes.append((expected_val, actual_val))

        return fixes[:_MAX_ASSERTIONS_TO_FIX]

    def _apply_fixes(
        self, java_source: str, fixes: List[Tuple[str, str]]
    ) -> str:
        """
        将错误的预期值替换为真实值。

        策略：
        - 只替换字面量形式的预期值（数字、字符串）
        - 如果 actual 是复杂表达式（无法安全嵌入），跳过
        - 替换时保持代码结构不变
        """
        result = java_source

        for wrong_expected, actual_val in fixes:
            # 跳过复杂的 actual 值（含空格或特殊字符，可能不安全）
            if not self._is_safe_replacement(actual_val):
                logger.debug("[AssertFixer] Skip complex actual value: %s", actual_val[:50])
                continue

            # 在 assertEquals 中查找并替换这个预期值
            result = self._replace_expected_in_assertEquals(
                result, wrong_expected, actual_val
            )

        return result

    def _is_safe_replacement(self, val: str) -> bool:
        """判断是否可以安全地将此值嵌入 Java 代码"""
        if not val:
            return False
        # 允许：数字、简单字符串、布尔值、null
        val = val.strip()
        if val in ('true', 'false', 'null'):
            return True
        if re.match(r'^-?\d+(\.\d+)?[LlFfDd]?$', val):
            return True
        # 字符串值（来自 toString()）- 用双引号包裹
        if not re.search(r'[{}()\[\]<>]', val):
            return True
        return False

    def _replace_expected_in_assertEquals(
        self, source: str, wrong: str, correct: str
    ) -> str:
        """
        在 assertEquals 调用中替换错误的预期值。
        谨慎替换：只替换明确是字面量预期值的位置。
        """
        lines = source.splitlines(keepends=True)
        result = []

        for line in lines:
            if 'assertEquals' not in line:
                result.append(line)
                continue

            # 检查这行是否包含错误的预期值
            # 构建可能的 Java 字面量形式
            wrong_forms = self._get_java_literal_forms(wrong)
            correct_form = self._to_java_literal(correct)

            replaced = False
            for wf in wrong_forms:
                # 在 assertEquals( 之后查找这个值
                pattern = re.compile(
                    r'(assertEquals\s*\(\s*)' + re.escape(wf) + r'(\s*,)',
                )
                if pattern.search(line):
                    new_line = pattern.sub(
                        r'\g<1>' + correct_form + r'\g<2>',
                        line, count=1
                    )
                    result.append(new_line)
                    replaced = True
                    logger.debug("[AssertFixer] Fixed: %s -> %s", wf, correct_form)
                    break

            if not replaced:
                result.append(line)

        return ''.join(result)

    def _get_java_literal_forms(self, val: str) -> List[str]:
        """返回一个值可能在 Java 代码中出现的所有字面量形式"""
        forms = [val]
        # 数字可能有 L/l 后缀
        if re.match(r'^-?\d+$', val):
            forms.extend([val + 'L', val + 'l', val + 'F', val + 'f'])
        # 字符串
        forms.append(f'"{val}"')
        return forms

    def _to_java_literal(self, val: str) -> str:
        """将运行时值转换为 Java 字面量"""
        val = val.strip()
        if val in ('true', 'false', 'null'):
            return val
        if re.match(r'^-?\d+(\.\d+)?[LlFfDd]?$', val):
            return val
        # 字符串值（带引号）
        if val.startswith('"') and val.endswith('"'):
            return val
        # 其他值作为字符串处理
        escaped = val.replace('\\', '\\\\').replace('"', '\\"')
        return f'"{escaped}"'


# ════════════════════════════════════════════════════════════════════
# 简化入口：从文件信息快速创建并运行
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
    一站式断言修复入口。
    在 LLM 生成测试代码之后、进入 TestRunner 评估之前调用。

    Parameters
    ----------
    java_source    : LLM 生成的 Java 测试源码
    class_name     : 测试类名
    package        : 包名
    project_dir    : 被测项目目录（含编译好的 target/classes）
    junit_jar      : JUnit JAR 路径（冒号分隔）
    private_fields : 已知私有字段列表

    Returns
    -------
    修复后的 Java 源码（编译/运行失败时返回原始源码）
    """
    if not project_dir or not os.path.isdir(project_dir):
        logger.debug("[AssertFixer] project_dir not found, skip: %s", project_dir)
        return java_source

    # 检查 target/classes 是否存在（被测类已编译）
    classes_dir = os.path.join(project_dir, "target", "classes")
    if not os.path.isdir(classes_dir):
        logger.debug("[AssertFixer] target/classes not found, skip")
        return java_source

    try:
        fixer = AssertFixer(
            project_dir=project_dir,
            junit_jar=junit_jar,
            mockito_jar=mockito_jar,
            log4j_jar=log4j_jar,
        )
        fixed = fixer.fix(
            java_source=java_source,
            class_name=class_name,
            package=package,
            private_fields=private_fields,
        )

        if fixed != java_source:
            logger.info("[AssertFixer] Assertions fixed for %s", class_name)
        else:
            logger.info("[AssertFixer] No changes needed for %s", class_name)

        return fixed

    except Exception as e:
        logger.warning("[AssertFixer] Fix failed for %s: %s", class_name, e)
        return java_source  # 失败时返回原始代码，不影响主流程