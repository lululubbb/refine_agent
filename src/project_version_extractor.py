"""
project_version_extractor.py  (v2 — Defects4J 全项目覆盖版)
=============================================================

修复内容：
  1. 规则库扩充：从 2 条扩展到覆盖全部主要 Defects4J 项目的约束
     （Csv, Cli, Codec, Collections, Compress, Gson, JacksonCore,
      JacksonDatabind, JacksonXml, Jsoup, JxPath, Lang, Math,
      Mockito, Time, Chart, Closure）
  2. 规则分为两类：
     a) artifact-level 规则：基于 pom.xml 的依赖版本
     b) project-name 规则：基于项目目录名直接推断（更可靠，不依赖 pom 解析）
  3. 新增 _infer_restrictions_from_project_name()：
     通过目录名（Csv_1_b → commons-csv）直接匹配规则，
     解决 pom.xml 解析失败或依赖信息缺失时的 fallback 问题
  4. to_prompt_text() 只输出有实际约束内容的版本信息，
     避免只有项目名和 JDK 版本的无价值输出
"""
from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple


# ════════════════════════════════════════════════════════════════════
# 版本信息数据结构
# ════════════════════════════════════════════════════════════════════

class ProjectVersionInfo:
    def __init__(self):
        self.project_group_id: str = ""
        self.project_artifact_id: str = ""
        self.project_version: str = ""
        self.java_version: str = ""
        self.junit_version: str = ""
        self.mockito_version: str = ""
        self.dependencies: Dict[str, str] = {}
        self.available_jars: List[str] = []
        self.known_api_restrictions: List[str] = []
        self.api_examples: Dict[str, str] = {}
        self.compilation_rules: List[str] = []   # ★ 新增：编译规则
        self.project_name_hint: str = ""          # ★ 新增：从目录名推断的项目名

    def has_useful_constraints(self) -> bool:
        """判断是否有真正有价值的约束（避免输出空洞的版本文本）。"""
        return bool(
            self.known_api_restrictions
            or self.api_examples
            or self.compilation_rules
            or (self.junit_version and self.junit_version.startswith('4.'))
        )

    def to_prompt_text(self) -> str:
        """
        只输出有增量价值的版本约束。
        如果没有有用的约束，返回空字符串（避免噪声）。
        """
        if not self.has_useful_constraints() and not self.project_artifact_id:
            return ""

        lines = [
            "## Project Version Constraints — MUST FOLLOW",
            "",
            "Only use APIs that exist in this exact project version.",
            "",
        ]

        if self.project_artifact_id:
            ver = self.project_version or "unknown"
            lines.append(f"**Target Project**: `{self.project_artifact_id}` v`{ver}`")

        if self.java_version:
            lines.append(f"**Java Version**: {self.java_version}")
            java_ver_num = _parse_version_num(self.java_version)
            if java_ver_num < (10,):
                lines.append(
                    "  → No `var` keyword, no text blocks, no records, no switch expressions"
                )

        # JUnit 版本（只有明确是 JUnit 4 时才输出，避免混淆）
        if self.junit_version:
            if self.junit_version.startswith('4.'):
                lines.append(f"**JUnit Version**: {self.junit_version} (JUnit 4)")
                lines.append(
                    "  → Use `@org.junit.Test`, `org.junit.Assert.*` (NOT `Assertions.*`)"
                )
                lines.append(
                    "  → Use `@Before`/`@After` (NOT `@BeforeEach`/`@AfterEach`)"
                )
                lines.append(
                    "  → Use `@RunWith(MockitoJUnitRunner.class)` (NOT `@ExtendWith`)"
                )
            else:
                lines.append(f"**JUnit Version**: {self.junit_version}")

        if self.mockito_version:
            lines.append(f"**Mockito Version**: {self.mockito_version}")
            mv = _parse_version_num(self.mockito_version)
            if mv < (4,):
                lines.append(
                    "  → Use `Mockito.mock()`, `Mockito.when()` — avoid newer `mockConstruction()`"
                )

        if self.known_api_restrictions:
            lines.append("")
            lines.append("### ❌ APIs that DO NOT EXIST in this version (will cause compile error):")
            for restriction in self.known_api_restrictions:
                lines.append(f"  - {restriction}")

        if self.api_examples:
            lines.append("")
            lines.append("### ✅ Correct API usage for this version:")
            for wrong, correct in self.api_examples.items():
                lines.append(f"  - Instead of `{wrong}`, use: `{correct}`")

        if self.compilation_rules:
            lines.append("")
            lines.append("### ⚠️ Version-specific compilation rules:")
            for rule in self.compilation_rules:
                lines.append(f"  - {rule}")

        if not self.has_useful_constraints():
            # 没有有用约束时不输出（只有项目名+JDK 对 LLM 无增量价值）
            return ""

        return "\n".join(lines)


# ════════════════════════════════════════════════════════════════════
# Defects4J 项目知识库
# ════════════════════════════════════════════════════════════════════
#
# 格式：project_prefix → {
#   "restrictions": [...],  # 不存在的 API
#   "examples": {wrong: correct},  # 正确写法示例
#   "rules": [...],  # 编译规则
# }
#
# 数据来源：Defects4J 文档 + 各项目历史版本 changelog

_D4J_PROJECT_RULES: Dict[str, dict] = {

    # ── Apache Commons CSV ──────────────────────────────────────────
    "csv": {
        "restrictions": [
            "CSVFormat.Builder (introduced in 1.9+; Defects4J Csv uses 1.5 or earlier)",
            "CSVFormat.builder() static method",
            "CSVFormat.Builder.setDelimiter()/setQuote()/setEscape() etc.",
            "CSVRecord.toMap() (not available in early versions)",
        ],
        "examples": {
            "CSVFormat.builder().setDelimiter(',').build()":
                "CSVFormat.DEFAULT.withDelimiter(',')",
            "CSVFormat.Builder":
                "CSVFormat.DEFAULT.withXxx() chaining (e.g., .withDelimiter(',').withQuote('\"'))",
            "CSVFormat.DEFAULT.builder()":
                "CSVFormat.DEFAULT.withDelimiter(',').withQuote('\"')",
        },
        "rules": [
            "CSVFormat is configured via chained withXxx() methods, NOT a Builder pattern",
            "CSVParser.parse(File, Charset, CSVFormat) — check exact parameter order from context",
        ],
    },

    # ── Apache Commons CLI ──────────────────────────────────────────
    "cli": {
        "restrictions": [
            "Option.builder() (Builder pattern not in Defects4J Cli versions)",
            "Options.getOption(String) with long option name may not exist in early versions",
        ],
        "examples": {
            "Option.builder('f').longOpt('file').build()":
                "OptionBuilder.withLongOpt(\"file\").create('f')",
            "new Option(\"f\", \"file\", true, \"desc\")":
                "new Option(\"f\", \"file\", true, \"desc\") — check constructor signature",
        },
        "rules": [
            "Use OptionBuilder (static factory) for option creation in older versions",
            "CommandLine.getOptionValue() returns null (not Optional) when absent",
        ],
    },

    # ── Apache Commons Codec ────────────────────────────────────────
    "codec": {
        "restrictions": [
            "Base64.encodeBase64URLSafeString() may not exist in early versions",
        ],
        "examples": {},
        "rules": [
            "Base64.encodeBase64(byte[]) returns byte[], not String — use new String(result)",
            "DigestUtils methods take byte[] or String, not InputStream in early versions",
        ],
    },

    # ── Apache Commons Collections ──────────────────────────────────
    "collections": {
        "restrictions": [
            "org.apache.commons.collections4 package (Defects4J uses collections3 for bugs 1-20)",
        ],
        "examples": {
            "import org.apache.commons.collections4.*":
                "import org.apache.commons.collections.* (for bugs 1-20)",
        },
        "rules": [
            "Check whether the project uses collections3 (org.apache.commons.collections) "
            "or collections4 (org.apache.commons.collections4) from the imports in the focal class",
        ],
    },

    # ── Apache Commons Compress ─────────────────────────────────────
    "compress": {
        "restrictions": [],
        "examples": {},
        "rules": [
            "TarArchiveEntry constructor signatures vary by version — check focal class context",
            "ZipArchiveOutputStream requires explicit close() — test resource cleanup",
            "ArchiveStreamFactory.createArchiveInputStream() throws ArchiveException, not IOException",
        ],
    },

    # ── Google Gson ─────────────────────────────────────────────────
    "gson": {
        "restrictions": [
            "GsonBuilder.setStrictness() (added in 2.11+)",
            "JsonReader.setStrictness() (added in 2.11+)",
        ],
        "examples": {
            "gson.setStrictness(Strictness.LENIENT)":
                "gson.setLenient(true)",
            "reader.setStrictness(Strictness.STRICT)":
                "reader.setLenient(false)",
        },
        "rules": [
            "Use setLenient(boolean) instead of setStrictness(Strictness) in Defects4J Gson versions",
            "JsonParser.parse() is deprecated in newer Gson — check which version is used",
        ],
    },

    # ── FasterXML Jackson Core ───────────────────────────────────────
    "jacksoncore": {
        "restrictions": [
            "StreamReadConstraints / StreamWriteConstraints (added in 2.15+)",
        ],
        "examples": {},
        "rules": [
            "JsonFactory.createParser() vs JsonFactory.createJsonParser() — check version",
            "JsonToken enum values: START_OBJECT, END_OBJECT, FIELD_NAME, VALUE_STRING etc.",
            "JsonParser.nextToken() returns null at end of input (not throws exception)",
        ],
    },

    # ── FasterXML Jackson Databind ───────────────────────────────────
    "jacksondatabind": {
        "restrictions": [
            "ObjectMapper.readerForUpdating() may not exist in early versions",
            "JsonTypeInfo.Id.DEDUCTION (added in 2.12+)",
        ],
        "examples": {},
        "rules": [
            "ObjectMapper is thread-safe for read operations; avoid creating per-test instances unnecessarily",
            "TypeReference<T> must be created as anonymous subclass: new TypeReference<List<String>>(){}",
            "DeserializationFeature and SerializationFeature are separate enums",
        ],
    },

    # ── Jsoup ───────────────────────────────────────────────────────
    "jsoup": {
        "restrictions": [
            "Connection.newRequest() (added in 1.14+)",
        ],
        "examples": {},
        "rules": [
            "Jsoup.parse() returns Document; Document extends Element",
            "Element.select() uses CSS selectors, returns Elements (List subclass)",
            "Elements.first() returns null (not Optional) when empty",
            "Document.outputSettings().charset() for encoding configuration",
        ],
    },

    # ── Apache Commons JXPath ────────────────────────────────────────
    "jxpath": {
        "restrictions": [],
        "examples": {},
        "rules": [
            "JXPathContext.newContext(Object) for creating context",
            "JXPathContext.getValue(String) throws JXPathNotFoundException when path not found",
            "Use JXPathContext.selectNodes() for multiple results (returns List)",
        ],
    },

    # ── Apache Commons Lang ──────────────────────────────────────────
    "lang": {
        "restrictions": [
            "org.apache.commons.lang3.* package (Defects4J Lang 40-65 uses lang2: org.apache.commons.lang.*)",
        ],
        "examples": {
            "import org.apache.commons.lang3.*":
                "Check focal class — bugs 40-65 use org.apache.commons.lang (lang2), "
                "bugs 1-39 use org.apache.commons.lang3",
        },
        "rules": [
            "CRITICAL: Check the import in the focal class to determine lang2 vs lang3",
            "StringUtils methods return empty string (not null) for null input in lang3",
            "NumberUtils.createNumber() throws NumberFormatException for invalid input",
        ],
    },

    # ── Apache Commons Math ──────────────────────────────────────────
    "math": {
        "restrictions": [
            "org.apache.commons.math3.* (Defects4J Math 99-106 uses math2: org.apache.commons.math.*)",
            "FastMath class (added in math3; use Math in math2)",
        ],
        "examples": {
            "import org.apache.commons.math3.*":
                "Check focal class — bugs 99-106 use org.apache.commons.math (math2), "
                "bugs 1-98 use org.apache.commons.math3",
        },
        "rules": [
            "CRITICAL: Check the import in the focal class to determine math2 vs math3",
            "MathArithmeticException extends ArithmeticException (math3) or MathException (math2)",
            "Complex.NaN check: use Double.isNaN(c.getReal()) not c.equals(Complex.NaN)",
            "Fraction operations throw FractionConversionException or MathArithmeticException",
            "ODE integrators: FirstOrderDifferentialEquations interface for defining ODEs",
        ],
    },

    # ── Mockito ──────────────────────────────────────────────────────
    "mockito": {
        "restrictions": [
            "Mockito.mockConstruction() (added in Mockito 4+; Defects4J Mockito uses 1.x-3.x)",
            "Mockito.mockStatic() (added in Mockito 3.4+)",
            "@Mock with strictness parameter (newer API)",
        ],
        "examples": {
            "Mockito.mockConstruction(Foo.class)":
                "Not available; use PowerMock or refactor to inject dependency",
        },
        "rules": [
            "Defects4J Mockito versions: check pom.xml, typically 1.9.x or 2.x",
            "MockitoAnnotations.initMocks(this) in @Before (not openMocks() which is newer)",
            "Mockito.verify() default is times(1) — be explicit for clarity",
            "InOrder for ordered verification: InOrder inOrder = inOrder(mock1, mock2)",
        ],
    },

    # ── Joda-Time ───────────────────────────────────────────────────
    "time": {
        "restrictions": [
            "Java 8 java.time API (LocalDate, ZonedDateTime etc.) — not available in Java 6/7 projects",
        ],
        "examples": {
            "LocalDate.now()": "new LocalDate() or LocalDate.now() (Joda-Time, not java.time)",
            "java.time.LocalDate": "org.joda.time.LocalDate",
        },
        "rules": [
            "CRITICAL: Use org.joda.time.* classes, NOT java.time.* (Java 8 API)",
            "DateTime is mutable in Joda-Time (unlike java.time which is immutable)",
            "DateTimeZone.UTC for UTC timezone (not ZoneOffset.UTC)",
            "Period vs Duration: Period for calendar-based, Duration for exact milliseconds",
        ],
    },

    # ── JFreeChart ───────────────────────────────────────────────────
    "chart": {
        "restrictions": [],
        "examples": {},
        "rules": [
            "ChartFactory methods are static — no need to instantiate",
            "Most Chart objects use DefaultXxxDataset for test data",
            "JFreeChart uses AWT types — avoid headless environment issues with mock/headless setup",
            "XYSeries.add() accepts Number, double, or (double, double)",
        ],
    },

    # ── Google Closure Compiler ──────────────────────────────────────
    "closure": {
        "restrictions": [
            "ES6+ features in test code may not compile with Java 6 target",
        ],
        "examples": {},
        "rules": [
            "Compiler class is the main entry; use CompilerOptions for configuration",
            "JSSourceFile / SourceFile for creating test input files",
            "CompilerOptions must be configured before Compiler.compile()",
            "AbstractCommandLineRunner for testing CLI behavior",
            "Node (Rhino AST) has type-checked children — use Node.getType() for verification",
        ],
    },
}

# 项目前缀到知识库 key 的映射（目录名前缀 → 规则 key）
_PROJECT_PREFIX_MAP: Dict[str, str] = {
    "csv":            "csv",
    "cli":            "cli",
    "codec":          "codec",
    "collections":    "collections",
    "compress":       "compress",
    "gson":           "gson",
    "jacksoncore":    "jacksoncore",
    "jacksondatabind": "jacksondatabind",
    "jacksonxml":     "jacksondatabind",  # 共享大部分规则
    "jsoup":          "jsoup",
    "jxpath":         "jxpath",
    "lang":           "lang",
    "math":           "math",
    "mockito":        "mockito",
    "time":           "time",
    "chart":          "chart",
    "closure":        "closure",
}


# ════════════════════════════════════════════════════════════════════
# 版本提取器
# ════════════════════════════════════════════════════════════════════

class ProjectVersionExtractor:

    def extract(self, project_dir: str) -> ProjectVersionInfo:
        return _cached_extract(os.path.abspath(project_dir))

    def _do_extract(self, project_dir: str) -> ProjectVersionInfo:
        info = ProjectVersionInfo()

        # ── 步骤1：从目录名直接推断项目类型（最可靠）────────────────
        dir_name = os.path.basename(project_dir.rstrip('/'))
        self._infer_restrictions_from_project_name(dir_name, info)

        # ── 步骤2：解析 pom.xml 获取精确版本 ─────────────────────────
        pom_path = os.path.join(project_dir, "pom.xml")
        if os.path.exists(pom_path):
            try:
                self._parse_pom(pom_path, info)
            except Exception as e:
                pass  # pom 解析失败不影响步骤1的结果

        # ── 步骤3：扫描 JAR 补充版本信息 ─────────────────────────────
        dep_dir = os.path.join(project_dir, "target", "dependency")
        if os.path.isdir(dep_dir):
            info.available_jars = [f for f in os.listdir(dep_dir) if f.endswith(".jar")]
            self._infer_versions_from_jars(info)

        # ── 步骤4：基于精确版本应用 artifact-level 规则（覆盖步骤1）──
        self._apply_artifact_rules(info)

        return info

    def _infer_restrictions_from_project_name(self, dir_name: str, info: ProjectVersionInfo):
        """
        从目录名直接推断项目类型并应用规则。
        这是最可靠的方式，不依赖 pom 解析。
        目录名格式：Csv_1_b, Math_32_f, JacksonDatabind_12_b 等
        """
        name_lower = dir_name.lower()

        # 去掉版本号和 _b/_f 后缀
        # Csv_1_b → csv, JacksonDatabind_12_f → jacksondatabind
        clean = re.sub(r'_\d+.*$', '', name_lower)
        info.project_name_hint = clean

        # 在映射表中查找
        rule_key = _PROJECT_PREFIX_MAP.get(clean)
        if not rule_key:
            # 尝试前缀匹配（处理 jacksonxml 等）
            for prefix, key in _PROJECT_PREFIX_MAP.items():
                if clean.startswith(prefix) or prefix.startswith(clean):
                    rule_key = key
                    break

        if rule_key and rule_key in _D4J_PROJECT_RULES:
            rules = _D4J_PROJECT_RULES[rule_key]
            info.known_api_restrictions.extend(rules.get("restrictions", []))
            info.api_examples.update(rules.get("examples", {}))
            info.compilation_rules.extend(rules.get("rules", []))

    def _parse_pom(self, pom_path: str, info: ProjectVersionInfo):
        ns = {"m": "http://maven.apache.org/POM/4.0.0"}
        tree = ET.parse(pom_path)
        root = tree.getroot()

        def find_text(path):
            for prefix in ['', 'm:']:
                parts = path.split('/')
                prefixed = '/'.join(f'{prefix}{p}' if prefix else p for p in parts)
                el = root.find(prefixed, ns) if prefix else root.find(path)
                if el is not None and el.text:
                    return el.text.strip()
            return ""

        info.project_group_id    = find_text("m:groupId") or find_text("groupId")
        info.project_artifact_id = find_text("m:artifactId") or find_text("artifactId")
        info.project_version     = find_text("m:version") or find_text("version")

        # Properties（变量替换）
        props: Dict[str, str] = {}
        for props_el in [root.find("m:properties", ns), root.find("properties")]:
            if props_el is not None:
                for child in props_el:
                    tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                    if child.text:
                        props[tag] = child.text.strip()

        def resolve(v: str) -> str:
            if v and v.startswith("${"):
                return props.get(v[2:-1], v)
            return v

        # Java version
        for key in ("maven.compiler.source", "java.version", "maven.compiler.target"):
            if key in props:
                info.java_version = resolve(props[key])
                break

        # Dependencies
        for ns_prefix in ["m:", ""]:
            for dep in root.findall(f".//{ns_prefix}dependency", ns if ns_prefix else {}):
                artifact_el = dep.find(f"{ns_prefix}artifactId", ns if ns_prefix else {})
                version_el  = dep.find(f"{ns_prefix}version",    ns if ns_prefix else {})
                if artifact_el is not None and artifact_el.text:
                    artifact = artifact_el.text.strip()
                    version  = resolve(version_el.text.strip()) if version_el is not None and version_el.text else ""
                    info.dependencies[artifact] = version
                    if "junit" in artifact.lower() and not info.junit_version:
                        info.junit_version = version
                    elif "mockito" in artifact.lower() and not info.mockito_version:
                        info.mockito_version = version

    def _infer_versions_from_jars(self, info: ProjectVersionInfo):
        for jar in info.available_jars:
            m = re.match(r"^([\w\-]+?)-([\d\.]+(?:\.\w+)?)\.jar$", jar)
            if m:
                artifact, version = m.group(1), m.group(2)
                if artifact not in info.dependencies:
                    info.dependencies[artifact] = version
            if "junit-jupiter" in jar or "junit-5" in jar:
                if not info.junit_version:
                    m = re.search(r"junit[^\-]*-([\d\.]+)", jar)
                    info.junit_version = m.group(1) if m else "5.x"
            elif re.search(r"junit-4\.", jar):
                if not info.junit_version:
                    info.junit_version = "4.x"

    def _apply_artifact_rules(self, info: ProjectVersionInfo):
        """
        基于 pom.xml 中的精确依赖版本应用规则。
        比目录名推断更精确，可以覆盖步骤1的结果。
        """
        for dep_name, dep_version in info.dependencies.items():
            dep_lower = dep_name.lower()

            # commons-csv：Builder 模式在 1.9 引入
            if 'commons-csv' in dep_lower:
                if _version_lt(dep_version, "1.9"):
                    # 确保规则已加入（步骤1可能已经加了）
                    restriction = "CSVFormat.Builder (introduced in 1.9+)"
                    if not any("CSVFormat.Builder" in r for r in info.known_api_restrictions):
                        info.known_api_restrictions.insert(0, restriction)
                    example_key = "CSVFormat.builder().setDelimiter(',').build()"
                    if example_key not in info.api_examples:
                        info.api_examples[example_key] = "CSVFormat.DEFAULT.withDelimiter(',')"

            # Joda-Time
            elif 'joda-time' in dep_lower or 'joda' in dep_lower:
                if not any("joda" in r.lower() for r in info.compilation_rules):
                    info.compilation_rules.append(
                        "Use org.joda.time.* classes, NOT java.time.* (Java 8 API)"
                    )


# ════════════════════════════════════════════════════════════════════
# 缓存机制
# ════════════════════════════════════════════════════════════════════

_cache: Dict[str, ProjectVersionInfo] = {}
_extractor_instance = ProjectVersionExtractor()


def _cached_extract(project_dir: str) -> ProjectVersionInfo:
    if project_dir not in _cache:
        _cache[project_dir] = _extractor_instance._do_extract(project_dir)
    return _cache[project_dir]


def get_version_info(project_dir: str) -> ProjectVersionInfo:
    return _cached_extract(os.path.abspath(project_dir))


def get_version_prompt_text(project_dir: str) -> str:
    info = get_version_info(project_dir)
    return info.to_prompt_text()


# ════════════════════════════════════════════════════════════════════
# 工具函数
# ════════════════════════════════════════════════════════════════════

def _version_lt(version_str: str, target: str) -> bool:
    if not version_str or version_str.startswith("${"):
        return True
    try:
        def parse(v):
            return tuple(int(x) for x in re.split(r"[.\-]", v) if x.isdigit())
        return parse(version_str) < parse(target)
    except Exception:
        return False


def _parse_version_num(version_str: str) -> tuple:
    try:
        nums = [int(x) for x in re.split(r'[.\-]', version_str) if x.isdigit()]
        return tuple(nums) if nums else (0,)
    except Exception:
        return (0,)