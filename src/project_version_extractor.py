"""
project_version_extractor.py
============================
从 Maven pom.xml 中提取项目依赖版本信息，注入到 Generator/Refiner prompt，
解决 LLM 使用当前项目不存在的 API（如 CSVFormat.Builder）的问题。

核心功能：
  1. 解析 pom.xml 提取 JUnit/Mockito/项目自身版本
  2. 从 target/dependency/ 扫描实际可用的 JAR
  3. 生成版本约束文本注入 Prompt
  4. 缓存结果避免重复解析
"""
from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
from functools import lru_cache
from typing import Dict, List, Optional, Tuple


# ════════════════════════════════════════════════════════════════════
# 版本信息数据结构
# ════════════════════════════════════════════════════════════════════

class ProjectVersionInfo:
    """存储项目的版本约束和 API 可用性信息。"""

    def __init__(self):
        self.project_group_id: str = ""
        self.project_artifact_id: str = ""
        self.project_version: str = ""
        self.java_version: str = ""
        self.junit_version: str = ""
        self.mockito_version: str = ""
        self.dependencies: Dict[str, str] = {}      # {artifactId: version}
        self.available_jars: List[str] = []         # JAR文件名列表
        self.known_api_restrictions: List[str] = [] # 已知不可用API列表
        self.api_examples: Dict[str, str] = {}      # {wrongAPI: correctAPI}

    def to_prompt_text(self) -> str:
        """生成注入Prompt的版本约束文本。"""
        if not self.project_artifact_id and not self.dependencies:
            return ""

        lines = [
            "## Project Version Constraints — MUST FOLLOW",
            "",
            "You are generating tests for a specific project version. "
            "Only use APIs that exist in this exact version.",
            "",
        ]

        if self.project_artifact_id:
            ver = self.project_version or "unknown"
            lines.append(f"**Target Project**: `{self.project_artifact_id}` version `{ver}`")

        if self.java_version:
            lines.append(f"**Java Version**: {self.java_version}")
            if self.java_version.startswith(("1.7", "1.8", "7", "8")):
                lines.append(
                    "  → **No `var` keyword** (Java 10+), no text blocks (Java 13+), "
                    "no records (Java 16+)"
                )

        if self.junit_version:
            lines.append(f"**JUnit Version**: {self.junit_version}")
            if self.junit_version.startswith("4."):
                lines.append(
                    "  → Use `@Test` from `org.junit.Test`, "
                    "`Assert.*` NOT `Assertions.*`"
                )
            elif self.junit_version.startswith("5.") or "jupiter" in self.junit_version.lower():
                lines.append(
                    "  → Use `@Test` from `org.junit.jupiter.api.Test`, "
                    "`Assertions.*` from `org.junit.jupiter.api.Assertions`"
                )

        if self.mockito_version:
            lines.append(f"**Mockito Version**: {self.mockito_version}")

        if self.known_api_restrictions:
            lines.append("")
            lines.append("### ❌ APIs that DO NOT EXIST in this version:")
            for restriction in self.known_api_restrictions:
                lines.append(f"  - {restriction}")

        if self.api_examples:
            lines.append("")
            lines.append("### ✅ Correct API usage for this version:")
            for wrong, correct in self.api_examples.items():
                lines.append(f"  - Instead of `{wrong}`, use: `{correct}`")

        lines.append("")
        lines.append(
            "**CRITICAL**: Never use APIs not shown in the class context above. "
            "When in doubt, use the most basic/conservative API."
        )

        return "\n".join(lines)


# ════════════════════════════════════════════════════════════════════
# 版本提取器
# ════════════════════════════════════════════════════════════════════

class ProjectVersionExtractor:
    """从 Maven 项目中提取版本约束信息。"""

    # 已知的 API 限制规则：(artifactId_pattern, version_constraint, restrictions, examples)
    # version_constraint: lambda version_str -> bool (True 表示受限)
    _KNOWN_RESTRICTIONS = [
        # Apache Commons CSV
        (
            r"commons-csv",
            lambda v: _version_lt(v, "1.9"),
            [
                "CSVFormat.Builder (introduced in 1.9+)",
                "CSVFormat.builder() static method",
                "CSVFormat.Builder.setXxx() methods",
            ],
            {
                "new CSVFormat.Builder()": "CSVFormat.DEFAULT.withDelimiter(',').withQuote('\"')",
                "CSVFormat.builder().setDelimiter(',').build()": "CSVFormat.DEFAULT.withDelimiter(',')",
            }
        ),
        # JUnit 5 vs JUnit 4
        (
            r"junit-jupiter",
            lambda v: True,  # Always Jupiter
            [],
            {
                "Assert.assertEquals": "Assertions.assertEquals",
                "Assert.assertTrue": "Assertions.assertTrue",
                "@RunWith": "@ExtendWith",
            }
        ),
    ]

    def extract(self, project_dir: str) -> ProjectVersionInfo:
        """从项目目录提取版本信息（带缓存）。"""
        return _cached_extract(os.path.abspath(project_dir))

    def _do_extract(self, project_dir: str) -> ProjectVersionInfo:
        info = ProjectVersionInfo()
        pom_path = os.path.join(project_dir, "pom.xml")

        if not os.path.exists(pom_path):
            return info

        try:
            self._parse_pom(pom_path, info)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("pom.xml parse failed: %s", e)

        # 扫描实际可用的 JAR
        dep_dir = os.path.join(project_dir, "target", "dependency")
        if os.path.isdir(dep_dir):
            info.available_jars = [
                f for f in os.listdir(dep_dir) if f.endswith(".jar")
            ]
            self._infer_versions_from_jars(info)

        # 应用已知 API 限制
        self._apply_known_restrictions(info)

        return info

    def _parse_pom(self, pom_path: str, info: ProjectVersionInfo):
        """解析 pom.xml 提取版本信息。"""
        ns = {"m": "http://maven.apache.org/POM/4.0.0"}
        tree = ET.parse(pom_path)
        root = tree.getroot()

        def find(path):
            # 尝试有命名空间和无命名空间两种写法
            el = root.find(path, ns)
            if el is None:
                path_no_ns = re.sub(r'm:', '', path)
                el = root.find(path_no_ns)
            return el

        def text(path):
            el = find(path)
            return el.text.strip() if el is not None and el.text else ""

        info.project_group_id    = text("m:groupId")
        info.project_artifact_id = text("m:artifactId")
        info.project_version     = text("m:version")

        # Properties（变量替换）
        props: Dict[str, str] = {}
        props_el = find("m:properties")
        if props_el is not None:
            for child in props_el:
                tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if child.text:
                    props[tag] = child.text.strip()

        def resolve(v: str) -> str:
            if v and v.startswith("${"):
                key = v[2:-1]
                return props.get(key, v)
            return v

        # Java version
        for key in ("maven.compiler.source", "java.version", "maven.compiler.target"):
            if key in props:
                info.java_version = resolve(props[key])
                break

        # Dependencies
        for dep in root.findall(".//m:dependency", ns) + root.findall(".//dependency"):
            artifact_el = dep.find("m:artifactId", ns) or dep.find("artifactId")
            version_el  = dep.find("m:version",     ns) or dep.find("version")
            if artifact_el is not None and artifact_el.text:
                artifact = artifact_el.text.strip()
                version  = resolve(version_el.text.strip()) if version_el is not None and version_el.text else ""
                info.dependencies[artifact] = version

                # 特殊处理
                if "junit" in artifact.lower():
                    if not info.junit_version:
                        info.junit_version = version
                elif "mockito" in artifact.lower():
                    if not info.mockito_version:
                        info.mockito_version = version

    def _infer_versions_from_jars(self, info: ProjectVersionInfo):
        """从 JAR 文件名推断版本（补充 pom.xml 未声明的情况）。"""
        for jar in info.available_jars:
            # commons-csv-1.5.jar -> commons-csv: 1.5
            m = re.match(r"^([\w\-]+?)-([\d\.]+(?:\.\w+)?)\.jar$", jar)
            if m:
                artifact, version = m.group(1), m.group(2)
                if artifact not in info.dependencies:
                    info.dependencies[artifact] = version

            # 从 JAR 名推断 JUnit 版本
            if "junit-jupiter" in jar or "junit-5" in jar:
                if not info.junit_version:
                    m = re.search(r"junit[^\-]*-([\d\.]+)", jar)
                    info.junit_version = m.group(1) if m else "5.x"
            elif re.search(r"junit-4\.|junit-platform", jar):
                if not info.junit_version:
                    info.junit_version = "4.x"

    def _apply_known_restrictions(self, info: ProjectVersionInfo):
        """根据已知规则生成 API 限制信息。"""
        for artifact_pattern, version_check, restrictions, examples in self._KNOWN_RESTRICTIONS:
            for dep_name, dep_version in info.dependencies.items():
                if re.search(artifact_pattern, dep_name, re.IGNORECASE):
                    try:
                        if version_check(dep_version):
                            info.known_api_restrictions.extend(restrictions)
                            info.api_examples.update(examples)
                    except Exception:
                        pass


# ════════════════════════════════════════════════════════════════════
# 版本比较工具
# ════════════════════════════════════════════════════════════════════

def _version_lt(version_str: str, target: str) -> bool:
    """判断 version_str < target（简单数字比较）。"""
    if not version_str or version_str.startswith("${"):
        return True  # 无法确定时保守处理
    try:
        def parse(v):
            return tuple(int(x) for x in re.split(r"[.\-]", v) if x.isdigit())
        return parse(version_str) < parse(target)
    except Exception:
        return False


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
    """获取项目版本信息（外部调用入口）。"""
    return _cached_extract(os.path.abspath(project_dir))


def get_version_prompt_text(project_dir: str) -> str:
    """获取可注入 Prompt 的版本约束文本。"""
    info = get_version_info(project_dir)
    return info.to_prompt_text()