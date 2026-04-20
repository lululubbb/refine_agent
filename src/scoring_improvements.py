"""
scoring_improvements.py  (v2)
==============================
修正覆盖率和Bug-revealing的协同优化逻辑。

核心理论：
  Bug-revealing 是覆盖率的充分不必要条件：
    - 覆盖了含bug的行 → 有可能 revealing（取决于断言）
    - 没覆盖含bug的行 → 一定不能 revealing（无论断言多精确）

  因此正确的优先级是：
    1. 覆盖率不足（<阈值）→ 优先做"分支覆盖"
       此时bug-revealing失败往往是"还没走到bug所在路径"导致的
    2. 覆盖率足够（≥阈值）+ bug-revealing失败 → 做"断言强化"
       此时测试已走到bug路径，只是断言不够精确

  这纠正了原 scoring.py 中 NOT_BUG_REVEALING(priority=2) >
  LOW_LINE_COV(priority=3) 的错误顺序。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# 覆盖率"足够"的阈值
_COV_SUFFICIENT_LINE   = 0.75
_COV_SUFFICIENT_BRANCH = 0.70


@dataclass
class CoupledScore:
    """
    覆盖率和Bug-revealing的联合分析。
    决定对该测试用哪种修复策略，避免两个目标相互干扰。
    """
    line_coverage:    Optional[float]   # 0-1，None表示未知
    branch_coverage:  Optional[float]   # 0-1，None表示未知
    is_bug_revealing: Optional[bool]    # None表示未检测
    redundancy_score: Optional[float]   # 1-sim，越高越冗余

    @property
    def line_sufficient(self) -> bool:
        if self.line_coverage is None:
            return True   # 未知时不强制做覆盖
        return self.line_coverage >= _COV_SUFFICIENT_LINE

    @property
    def branch_sufficient(self) -> bool:
        if self.branch_coverage is None:
            return True
        return self.branch_coverage >= _COV_SUFFICIENT_BRANCH

    @property
    def coverage_sufficient(self) -> bool:
        return self.line_sufficient and self.branch_sufficient

    @property
    def fix_strategy(self) -> str:
        """
        返回单一修复策略，避免多目标干扰。

        策略说明：
          branch_coverage   → 增加新测试覆盖特定分支，不要求精确断言
          assertion_hardening → 不增加新测试，强化现有断言的精确性
          diversify         → 删除冗余测试，用结构不同的测试替换
          none              → 无需处理
        """
        # 覆盖率不足时，优先做分支覆盖
        # 原因：覆盖率低时bug-revealing失败通常是因为没走到bug路径
        # 提升覆盖率能同时改善这两个指标
        if not self.coverage_sufficient:
            return "branch_coverage"

        # 覆盖率足够但bug-revealing失败 → 断言太宽松
        if self.is_bug_revealing is False:
            return "assertion_hardening"

        # 高冗余（sim > 0.7，即 redundancy_score < 0.3）
        if self.redundancy_score is not None and self.redundancy_score < 0.3:
            return "diversify"

        return "none"

    @property
    def fix_strategy_rationale(self) -> str:
        """给LLM的策略解释，写入prompt帮助LLM理解为什么这么做。"""
        if self.fix_strategy == "branch_coverage":
            lc = self.line_coverage
            lc_str = f"{lc*100:.0f}%" if lc is not None else "unknown"
            return (
                f"Line coverage is {lc_str} — the test does not reach all code paths "
                f"in the focal method. Fix priority: improve coverage first. "
                f"Reason: if the test cannot reach the code path containing the bug, "
                f"no assertion can reveal it. "
                f"Add tests that exercise the specific uncovered branches listed below. "
                f"Precise assertions are secondary at this stage."
            )
        if self.fix_strategy == "assertion_hardening":
            lc_str = f"{self.line_coverage*100:.0f}%" if self.line_coverage is not None else "good"
            return (
                f"Coverage is {lc_str} — the test reaches the focal method's logic. "
                f"The problem is that assertions are too weak to distinguish "
                f"buggy from fixed behavior. "
                f"Fix: replace `assertNotNull(result)` / `assertTrue(result != null)` "
                f"with `assertEquals(exactExpectedValue, result)`. "
                f"Compute the exact expected value by tracing the focal method manually. "
                f"DO NOT add new @Test methods — make existing assertions more precise."
            )
        if self.fix_strategy == "diversify":
            sim = 1.0 - (self.redundancy_score or 0)
            return (
                f"This test is structurally very similar to another test "
                f"(pairwise similarity ≈ {sim:.2f}). "
                f"Change it to target a different input category or code branch."
            )
        return ""

    def to_dict(self) -> dict:
        return {
            "line_coverage":        self.line_coverage,
            "branch_coverage":      self.branch_coverage,
            "is_bug_revealing":     self.is_bug_revealing,
            "redundancy_score":     self.redundancy_score,
            "fix_strategy":         self.fix_strategy,
            "coverage_sufficient":  self.coverage_sufficient,
        }


def compute_coupled_score(diag) -> CoupledScore:
    lr = getattr(diag, 'focal_line_rate', None)
    br = getattr(diag, 'focal_branch_rate', None)
    return CoupledScore(
        line_coverage    = (lr / 100.0) if lr is not None else None,
        branch_coverage  = (br / 100.0) if br is not None else None,
        is_bug_revealing = getattr(diag, 'bug_revealing', None),
        redundancy_score = getattr(diag, 'redundancy_score', None),
    )


class FixPriorityRouter:
    """
    为每个测试文件计算单一修复策略，严格避免 prompt 语义过载。

    原则：一个 Fix prompt 只解决一类问题。
    """

    def route(
        self,
        issues: List[str],
        diag=None,
        coupled_score: Optional[CoupledScore] = None,
    ) -> Tuple[str, List[str]]:
        """
        返回 (primary_strategy, relevant_issues_only)。
        """
        if not issues:
            return "none", []

        # 编译失败：最高优先，完全隔离其他信息
        if "COMPILE_FAIL" in issues:
            return "compile", ["COMPILE_FAIL"]

        # 执行失败：次高优先
        if "EXEC_FAIL" in issues or "EXEC_TIMEOUT" in issues:
            return "exec", [i for i in issues if i in ("EXEC_FAIL", "EXEC_TIMEOUT")]

        # 后续：用联合评分决定覆盖 vs 断言
        if coupled_score:
            strategy = coupled_score.fix_strategy
            if strategy == "branch_coverage":
                return "branch_coverage", [i for i in issues if "COV" in i]
            if strategy == "assertion_hardening":
                return "assertion_hardening", ["NOT_BUG_REVEALING"]
            if strategy == "diversify":
                return "diversify", ["HIGH_REDUNDANCY"]

        # 无联合评分时的回退逻辑（兼容旧代码路径）
        if "NOT_BUG_REVEALING" in issues:
            # 没有覆盖率数据时，默认先做断言强化
            lc = getattr(diag, 'focal_line_rate', None)
            if lc is not None and lc < _COV_SUFFICIENT_LINE * 100:
                # 覆盖率明显不足，优先覆盖
                return "branch_coverage", [i for i in issues if "COV" in i] or ["NOT_BUG_REVEALING"]
            return "assertion_hardening", ["NOT_BUG_REVEALING"]

        if any(i in issues for i in ("LOW_LINE_COV", "LOW_BRANCH_COV")):
            return "branch_coverage", [i for i in issues if "COV" in i]

        if "HIGH_REDUNDANCY" in issues:
            return "diversify", ["HIGH_REDUNDANCY"]

        return "none", []


class AdaptiveTestCountController:
    """动态决定允许的最大 @Test 方法数量。"""

    MAX_ABSOLUTE = 12

    def compute(
        self,
        current_count: int,
        strategy: str,
        missed_segment_count: int = 0,
    ) -> Tuple[int, str]:
        """返回 (max_allowed, rationale)。"""

        if strategy == "compile":
            return current_count, (
                f"CRITICAL: Keep exactly {current_count} @Test methods. "
                f"Do NOT add or remove any test methods. Only fix the compile error."
            )

        if strategy == "exec":
            return current_count, (
                f"Keep exactly {current_count} @Test methods. "
                f"Fix the runtime error without changing the test structure."
            )

        if strategy == "branch_coverage":
            # 每个未覆盖段最多1个新测试，上限3个
            additional = min(max(1, missed_segment_count), 3)
            max_count  = min(current_count + additional, self.MAX_ABSOLUTE)
            return max_count, (
                f"You may add up to {additional} new @Test method(s) "
                f"(current: {current_count}, new max: {max_count}). "
                f"Each new test MUST target a specific uncovered segment listed above. "
                f"Do not add tests for already-covered paths."
            )

        if strategy == "assertion_hardening":
            # 最多1个新测试，优先强化现有
            max_count = min(current_count + 1, self.MAX_ABSOLUTE)
            return max_count, (
                f"Prefer strengthening existing assertions. "
                f"Only add 1 new @Test if absolutely needed to distinguish buggy/fixed behavior "
                f"(current: {current_count}, max: {max_count})."
            )

        if strategy == "diversify":
            # 允许删减，不允许增加
            max_count = max(current_count - 1, 1)
            return max_count, (
                f"Target: ≤{max_count} @Test methods (currently {current_count}). "
                f"Remove the most redundant test and replace it with a structurally different one."
            )

        return current_count, f"Maintain {current_count} @Test methods."


def build_improved_fix_context(
    tc_name: str,
    current_code: str,
    diag,
    issues: List[str],
    instructions: List[str],
    focal_method_name: str,
    focal_method_source: str,
    class_name: str,
    project_dir: str,
    package_name: str = "",
) -> Dict:
    """
    构建改进的 Fix prompt 上下文字典，供 askGPT_refine.py 使用。
    """
    coupled  = compute_coupled_score(diag)
    router   = FixPriorityRouter()
    strategy, filtered_issues = router.route(issues, diag, coupled)

    current_test_count = len(re.findall(r'@Test\b', current_code))

    missed_segment_count = 0
    branch_hint_text     = ""

    if strategy == "branch_coverage":
        branch_hint_text, missed_segment_count = _extract_branch_hints(
            diag, project_dir, focal_method_name, class_name,
            focal_method_source, package_name,
        )

    controller  = AdaptiveTestCountController()
    max_tests, count_rationale = controller.compute(
        current_test_count, strategy, missed_segment_count
    )

    filtered_instructions = _filter_instructions(instructions, strategy)

    return {
        "fix_strategy":          strategy,
        "strategy_rationale":    coupled.fix_strategy_rationale,
        "branch_hint_text":      branch_hint_text,
        "max_test_methods":      max_tests,
        "count_rationale":       count_rationale,
        "filtered_issues":       filtered_issues,
        "filtered_instructions": filtered_instructions,

        # compile/exec 上下文（策略不匹配时为空，避免干扰）
        "compile_ok":    getattr(diag, 'compile_ok', True),
        "exec_ok":       getattr(diag, 'exec_ok', True),
        "compile_errors": list(getattr(diag, 'compile_errors', []))[:15]
                          if strategy == "compile" else [],
        "exec_errors":    list(getattr(diag, 'exec_errors', []))[:8]
                          if strategy == "exec" else [],

        # 覆盖率数据（只在 branch_coverage 策略时注入）
        "focal_line_rate":    getattr(diag, 'focal_line_rate', None)
                              if strategy == "branch_coverage" else None,
        "focal_branch_rate":  getattr(diag, 'focal_branch_rate', None)
                              if strategy == "branch_coverage" else None,
        "focal_line_covered": getattr(diag, 'focal_line_covered', None)
                              if strategy == "branch_coverage" else None,
        "focal_line_total":   getattr(diag, 'focal_line_total', None)
                              if strategy == "branch_coverage" else None,
    }


def _extract_branch_hints(
    diag,
    project_dir: str,
    focal_method_name: str,
    class_name: str,
    focal_method_source: str,
    package_name: str,
) -> Tuple[str, int]:
    """返回 (branch_hint_text, segment_count)。"""
    try:
        from branch_hint_extractor import find_jacoco_xml, BranchHintExtractor

        # 优先 per-test XML（只含该测试的执行轨迹，更精确）
        xml_path = getattr(diag, '_per_test_jacoco_xml', None)
        if not xml_path or not __import__('os').path.exists(xml_path):
            xml_path = find_jacoco_xml(project_dir)

        if not xml_path:
            # 回退到 TestDiag 中已有的 missed_methods 信息
            return _fallback_from_diag(diag), 0

        extractor = BranchHintExtractor()
        hints = extractor.extract(
            jacoco_xml_path=xml_path,
            focal_method_name=focal_method_name,
            class_name=class_name,
            focal_method_source=focal_method_source,
            package_name=package_name,
        )
        if hints and not hints.is_empty():
            return hints.to_prompt_text(), len(hints.uncovered_segments)
    except Exception:
        pass

    return _fallback_from_diag(diag), 0


def _fallback_from_diag(diag) -> str:
    """当 JaCoCo 数据不可用时，使用 TestDiag 中的 missed/partial 方法信息。"""
    missed  = getattr(diag, 'missed_methods', [])
    partial = getattr(diag, 'partial_methods', [])
    if not missed and not partial:
        return ""
    parts = ["## Coverage gaps (from execution analysis):"]
    if missed:
        parts.append("Completely uncovered paths:")
        parts.extend(f"  - {m}" for m in missed[:5])
    if partial:
        parts.append("Partially covered (missed branches):")
        parts.extend(f"  - {p}" for p in partial[:5])
    return "\n".join(parts)


def _filter_instructions(instructions: List[str], strategy: str) -> List[str]:
    keywords = {
        "compile":             ["compile", "error:", "cannot find", "private", "abstract",
                                "incompatible", "unreported", "ambiguous", "constructor"],
        "exec":                ["runtime", "exception", "assert", "expected", "but was",
                                "thrown", "null", "reflection", "timeout"],
        "branch_coverage":     ["coverage", "branch", "line", "path", "uncovered",
                                "case", "boundary", "condition", "null", "empty", "add"],
        "assertion_hardening": ["assert", "assertEquals", "exact", "precise",
                                "bug", "reveal", "boundary", "value", "strengthen"],
        "diversify":           ["redundan", "similar", "different", "structure", "rewrite"],
    }
    kws = keywords.get(strategy, [])
    if not kws:
        return instructions[:3]
    matched = [i for i in instructions if any(k in i.lower() for k in kws)]
    return (matched or instructions[:2])[:4]


def build_generation_branch_hints(
    focal_method_source: str,
    class_name: str,
    method_name: str,
) -> str:
    """Phase 1 生成时的静态分支提示（无需JaCoCo）。"""
    try:
        from branch_hint_extractor import BranchHintExtractor
        conds = BranchHintExtractor()._infer_conditions(focal_method_source)
        if not conds:
            return ""
        lines = [f"## Static hints for `{method_name}()` — include tests for these conditions:", ""]
        lines.extend(f"  - {c}" for c in conds[:6])
        return "\n".join(lines)
    except Exception:
        return ""