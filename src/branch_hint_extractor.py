"""
branch_hint_extractor.py  (v2 — 精确方法级行号版)
===================================================

修复了 v1 的核心缺陷：JaCoCo XML 中 <sourcefile> 包含整个类的所有行，
<method> 节点只有覆盖率汇总没有行列表，两者无法直接关联。

解决方案：三步法
  Step 1: 从 <method name="focal"> 节点获取方法起始行号 (line 属性)
  Step 2: 从 focal method 源码字符串计算方法的行数 → 得到结束行号
  Step 3: 只从 <sourcefile> 中提取 [start_line, end_line] 范围内的行数据

这样就能精确提取 focal method 的未覆盖行，不混入其他方法的数据。
"""
from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class UncoveredSegment:
    start_line: int
    end_line: int
    missed_branches: int = 0
    covered_branches: int = 0
    source_snippets: List[str] = field(default_factory=list)

    @property
    def is_branch_point(self) -> bool:
        return self.missed_branches > 0

    @property
    def line_range(self) -> str:
        if self.start_line == self.end_line:
            return f"line {self.start_line}"
        return f"lines {self.start_line}-{self.end_line}"


@dataclass
class BranchHints:
    focal_method_name: str
    class_name: str
    method_start_line: int
    method_end_line: int
    total_method_lines: int
    missed_lines: int
    covered_lines: int
    total_branches: int
    covered_branches: int
    missed_branches: int
    uncovered_segments: List[UncoveredSegment] = field(default_factory=list)
    inferred_conditions: List[str] = field(default_factory=list)
    extraction_confidence: str = "high"

    @property
    def line_coverage_pct(self) -> float:
        total = self.missed_lines + self.covered_lines
        return (self.covered_lines / total * 100) if total else 0.0

    @property
    def branch_coverage_pct(self) -> float:
        return (self.covered_branches / self.total_branches * 100) if self.total_branches else 0.0

    def is_empty(self) -> bool:
        return self.missed_lines == 0 and not self.inferred_conditions

    def to_prompt_text(self, max_segments: int = 6) -> str:
        if self.is_empty():
            return ""

        conf_note = "" if self.extraction_confidence == "high" else f" (confidence: {self.extraction_confidence})"
        range_note = ""
        if self.method_start_line > 0:
            range_note = f" (file lines {self.method_start_line}-{self.method_end_line})"

        lines_out = [
            f"## Uncovered code in `{self.focal_method_name}()`{range_note}{conf_note}",
            "",
            f"Line coverage: {self.line_coverage_pct:.0f}%  "
            f"({self.covered_lines}/{self.covered_lines + self.missed_lines} executable lines covered)",
        ]

        if self.total_branches > 0:
            lines_out.append(
                f"Branch coverage: {self.branch_coverage_pct:.0f}%  "
                f"({self.covered_branches}/{self.total_branches} branches taken)"
            )

        if self.uncovered_segments:
            lines_out.append("")
            lines_out.append("### Specific uncovered segments (write @Test for each):")

            segments = sorted(
                self.uncovered_segments,
                key=lambda s: (s.missed_branches, s.end_line - s.start_line),
                reverse=True,
            )[:max_segments]

            for i, seg in enumerate(segments, 1):
                branch_note = ""
                if seg.missed_branches > 0:
                    total_br = seg.missed_branches + seg.covered_branches
                    branch_note = f"  ← BRANCH: {seg.missed_branches}/{total_br} branches not taken"
                lines_out.append(f"  {i}. **{seg.line_range}**{branch_note}")
                for snippet in seg.source_snippets[:3]:
                    s = snippet.strip()
                    if s and not s.startswith('//') and not s.startswith('*'):
                        lines_out.append(f"     `{s[:100]}`")

        if self.inferred_conditions:
            lines_out.append("")
            lines_out.append("### Test conditions inferred from control flow:")
            for cond in self.inferred_conditions[:6]:
                lines_out.append(f"  - {cond}")

        lines_out.append("")
        lines_out.append(
            "**Required**: Each new `@Test` must exercise at least one uncovered segment. "
            "Target BRANCH segments first."
        )

        return "\n".join(lines_out)


class BranchHintExtractor:
    """
    三步法精确提取 focal method 的 JaCoCo 未覆盖行信息。
    """

    def extract(
        self,
        jacoco_xml_path: str,
        focal_method_name: str,
        class_name: str,
        focal_method_source: str,
        package_name: str = "",
    ) -> Optional[BranchHints]:

        if not focal_method_source or not focal_method_source.strip():
            return None

        xml_result = self._parse_xml(jacoco_xml_path, focal_method_name, class_name)
        if xml_result is None:
            return None

        method_start_line, all_line_data = xml_result

        if method_start_line <= 0:
            return self._fallback_source_only(focal_method_name, class_name, focal_method_source)

        # Step 2: 计算方法行范围
        method_line_count = len(focal_method_source.splitlines())
        method_end_line   = method_start_line + method_line_count - 1

        # Step 3: 只取方法范围内的行
        focal_line_data = {
            ln: data
            for ln, data in all_line_data.items()
            if method_start_line <= ln <= method_end_line
        }

        if not focal_line_data:
            return self._build_fully_uncovered(
                focal_method_name, class_name, focal_method_source,
                method_start_line, method_end_line,
            )

        source_line_map = {
            method_start_line + i: line
            for i, line in enumerate(focal_method_source.splitlines())
        }

        missed_lines     = sum(1 for ci, mi, cb, mb in focal_line_data.values() if ci == 0 and mi > 0)
        covered_lines    = sum(1 for ci, mi, cb, mb in focal_line_data.values() if ci > 0)
        total_branches   = sum(cb + mb for ci, mi, cb, mb in focal_line_data.values())
        covered_branches = sum(cb for ci, mi, cb, mb in focal_line_data.values())
        missed_branches  = sum(mb for ci, mi, cb, mb in focal_line_data.values())

        uncovered_segments  = self._build_segments(focal_line_data, source_line_map)
        inferred_conditions = self._infer_conditions(focal_method_source)

        return BranchHints(
            focal_method_name=focal_method_name,
            class_name=class_name,
            method_start_line=method_start_line,
            method_end_line=method_end_line,
            total_method_lines=method_line_count,
            missed_lines=missed_lines,
            covered_lines=covered_lines,
            total_branches=total_branches,
            covered_branches=covered_branches,
            missed_branches=missed_branches,
            uncovered_segments=uncovered_segments,
            inferred_conditions=inferred_conditions,
            extraction_confidence="high",
        )

    def _parse_xml(
        self,
        xml_path: str,
        focal_method_name: str,
        class_name: str,
    ) -> Optional[Tuple[int, Dict[int, Tuple[int, int, int, int]]]]:
        """
        返回 (method_start_line, {line_nr: (ci, mi, cb, mb)})
        ci=covered instructions, mi=missed, cb=covered branches, mb=missed branches
        """
        try:
            with open(xml_path, 'r', encoding='utf-8', errors='replace') as f:
                raw = f.read()
            start = raw.find('<report')
            if start >= 0:
                raw = raw[start:]
            raw = re.sub(r'<!DOCTYPE[^>]*>', '', raw)
            root = ET.fromstring(raw)
        except Exception:
            return None

        simple_class = class_name.split('.')[-1].split('$')[0]
        method_start_line = 0
        source_filename   = ""

        # Step 1a: 找 class 元素中的 focal method 起始行
        for class_elem in root.findall('.//class'):
            cname = class_elem.get('name', '')
            if cname.split('/')[-1].split('$')[0] != simple_class:
                continue

            sf = class_elem.get('sourcefilename', '')
            if sf:
                source_filename = sf

            for method_elem in class_elem.findall('method'):
                mname = method_elem.get('name', '')
                mline = int(method_elem.get('line', 0))
                is_constructor = (mname == '<init>' and focal_method_name == simple_class)
                if mname == focal_method_name or is_constructor:
                    method_start_line = mline
                    break

            if method_start_line > 0:
                break

        # Step 1b: 读取对应 sourcefile 的所有行数据
        all_line_data: Dict[int, Tuple[int, int, int, int]] = {}
        for sf_elem in root.findall('.//sourcefile'):
            sf_name = sf_elem.get('name', '')
            if source_filename and sf_name != source_filename:
                continue
            for line_elem in sf_elem.findall('line'):
                nr = int(line_elem.get('nr', 0))
                if nr <= 0:
                    continue
                ci = int(line_elem.get('ci', 0))
                mi = int(line_elem.get('mi', 0))
                cb = int(line_elem.get('cb', 0))
                mb = int(line_elem.get('mb', 0))
                all_line_data[nr] = (ci, mi, cb, mb)
            if all_line_data:
                break

        return method_start_line, all_line_data

    def _build_segments(
        self,
        line_data: Dict[int, Tuple],
        source_line_map: Dict[int, str],
    ) -> List[UncoveredSegment]:
        uncovered = sorted(
            ln for ln, (ci, mi, cb, mb) in line_data.items()
            if ci == 0 and mi > 0
        )
        if not uncovered:
            return []

        segments = []
        i = 0
        while i < len(uncovered):
            start = uncovered[i]
            end   = start
            while i + 1 < len(uncovered) and uncovered[i + 1] <= end + 3:
                i += 1
                end = uncovered[i]

            missed_br  = sum(line_data[ln][3] for ln in range(start, end + 1) if ln in line_data)
            covered_br = sum(line_data[ln][2] for ln in range(start, end + 1) if ln in line_data)

            snippets = []
            for ln in range(start, min(end + 1, start + 5)):
                code = source_line_map.get(ln, '').strip()
                if code and not code.startswith('//') and not code.startswith('*'):
                    snippets.append(code)

            segments.append(UncoveredSegment(
                start_line=start, end_line=end,
                missed_branches=missed_br, covered_branches=covered_br,
                source_snippets=snippets,
            ))
            i += 1

        return sorted(segments, key=lambda s: s.missed_branches, reverse=True)

    def _fallback_source_only(self, name, cls, source):
        conds = self._infer_conditions(source)
        if not conds:
            return None
        return BranchHints(
            focal_method_name=name, class_name=cls,
            method_start_line=0, method_end_line=0,
            total_method_lines=len(source.splitlines()),
            missed_lines=0, covered_lines=0,
            total_branches=0, covered_branches=0, missed_branches=0,
            uncovered_segments=[], inferred_conditions=conds,
            extraction_confidence="low",
        )

    def _build_fully_uncovered(self, name, cls, source, start, end):
        conds    = self._infer_conditions(source)
        snippets = [l.strip() for l in source.splitlines()[:5] if l.strip() and not l.strip().startswith('//')]
        seg = UncoveredSegment(start_line=start, end_line=end,
                               missed_branches=0, covered_branches=0,
                               source_snippets=snippets)
        return BranchHints(
            focal_method_name=name, class_name=cls,
            method_start_line=start, method_end_line=end,
            total_method_lines=end - start + 1,
            missed_lines=end - start + 1, covered_lines=0,
            total_branches=0, covered_branches=0, missed_branches=0,
            uncovered_segments=[seg], inferred_conditions=conds,
            extraction_confidence="medium",
        )

    def _infer_conditions(self, source: str) -> List[str]:
        if not source:
            return []
        conds = []
        for m in re.finditer(r'if\s*\(\s*(\w+)\s*==\s*null', source):
            conds.append(f"Test with `{m.group(1)} = null` to trigger null-check branch")
        for m in re.finditer(r'if\s*\(\s*(\w+)\s*(<|<=)\s*0', source):
            conds.append(f"Test `{m.group(1)} = 0` and `{m.group(1)} = -1` (triggers `{m.group(1)} {m.group(2)} 0`)")
        for m in re.finditer(r'(\w+)\.isEmpty\(\)', source):
            conds.append(f"Test with empty `{m.group(1)}` (triggers isEmpty() branch)")
        for m in re.finditer(r'throw\s+new\s+(\w+Exception)\s*\(', source):
            conds.append(f"assertThrows({m.group(1)}.class, ...) when throw condition is met")
        if re.search(r'return\s+-1\b|return\s+EOF\b', source):
            conds.append("Test reading past end-of-data: method should return -1 or EOF sentinel")
        if re.search(r'\bfor\s*\(|\bwhile\s*\(', source):
            conds.append("Test with 0-iteration input AND multi-iteration input")
        if re.search(r'isClosed\(\)|this\.closed\b', source):
            conds.append("Test calling method on closed object (should throw IOException)")
        return list(dict.fromkeys(conds))[:8]


_extractor = BranchHintExtractor()


def extract_branch_hints(
    jacoco_xml_path: str,
    focal_method_name: str,
    class_name: str,
    focal_method_source: str,
    package_name: str = "",
) -> str:
    try:
        hints = _extractor.extract(
            jacoco_xml_path=jacoco_xml_path,
            focal_method_name=focal_method_name,
            class_name=class_name,
            focal_method_source=focal_method_source,
            package_name=package_name,
        )
        if hints and not hints.is_empty():
            return hints.to_prompt_text()
    except Exception:
        pass
    return ""


def find_jacoco_xml(project_dir: str) -> Optional[str]:
    import glob
    candidates = [os.path.join(project_dir, 'target', 'site', 'jacoco', 'jacoco.xml')]
    candidates += sorted(
        glob.glob(os.path.join(project_dir, '**/jacoco.xml'), recursive=True),
        key=os.path.getmtime, reverse=True,
    )
    return next((p for p in candidates if os.path.exists(p) and os.path.getsize(p) > 100), None)