"""
scoring.py  (v5 — priority redesign + focal-method coverage fix)
=================================================================

Issue priority order (revised):
  1. COMPILE_FAIL
  2. EXEC_FAIL / EXEC_TIMEOUT
  3. NOT_BUG_REVEALING   ← elevated above coverage
  4. LOW_LINE_COV / LOW_BRANCH_COV
  5. HIGH_REDUNDANCY

Rationale: Bug-revealing is the key research contribution; coverage will
naturally improve when bug-revealing tests are added, but not vice versa.
Redundancy is a "nice to have" and should not distract from correctness.

Coverage issue is ONLY raised when focal_line_coverage < threshold AND
the test actually executes the focal method (focal_line_total > 0).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# Coverage thresholds
_LINE_COV_THRESHOLD   = 0.70
_BRANCH_COV_THRESHOLD = 0.70
# Redundancy threshold
_REDUNDANCY_THRESHOLD = 0.70


# ════════════════════════════════════════════════════════════════════
# Test 级评分
# ════════════════════════════════════════════════════════════════════

@dataclass
class TestScore:
    """
    Single Test file multi-dimensional score.
    Issues are ordered by priority:
      COMPILE_FAIL > EXEC_FAIL/EXEC_TIMEOUT > NOT_BUG_REVEALING > LOW_LINE/BRANCH_COV > HIGH_REDUNDANCY
    """
    test_name: str

    compile_score: float = 0.0
    exec_score:    float = 0.0

    focal_line_coverage:   Optional[float] = None
    focal_branch_coverage: Optional[float] = None

    # NEW: store focal method line counts for richer feedback
    focal_line_covered: Optional[int] = None
    focal_line_total:   Optional[int] = None

    bug_reveal_score: Optional[bool] = None

    max_similarity: Optional[float] = None
    most_similar_to: Optional[str]  = None

    issues: List[str] = field(default_factory=list)
    # Priority-ordered possible values:
    #   COMPILE_FAIL | EXEC_FAIL | EXEC_TIMEOUT |
    #   NOT_BUG_REVEALING | LOW_LINE_COV | LOW_BRANCH_COV | HIGH_REDUNDANCY

    def to_dict(self) -> dict:
        return {
            "test_name":            self.test_name,
            "compile_score":        self.compile_score,
            "exec_score":           self.exec_score,
            "focal_line_coverage":  self.focal_line_coverage,
            "focal_branch_coverage":self.focal_branch_coverage,
            "focal_line_covered":   self.focal_line_covered,
            "focal_line_total":     self.focal_line_total,
            "bug_reveal_score":     self.bug_reveal_score,
            "max_similarity":       self.max_similarity,
            "most_similar_to":      self.most_similar_to,
            "issues":               self.issues,
        }


# ════════════════════════════════════════════════════════════════════
# Suite 级评分（N 个 Test 文件整体的多维度统计）
# ════════════════════════════════════════════════════════════════════

@dataclass
class SuiteScore:
    """
    Suite（针对同一 focal method 的 N 个 Test 文件集合）的多维度统计。
    每个维度独立呈现，无加权综合分。
    """
    n_tests: int = 0            # Suite 中 Test 文件总数

    # ── 维度 1：编译通过情况 ──────────────────────────────────────
    compile_pass_count: int   = 0
    compile_pass_rate:  float = 0.0

    # ── 维度 2：执行通过情况 ──────────────────────────────────────
    exec_pass_count: int   = 0
    exec_pass_rate:  float = 0.0

    # ── 维度 3：覆盖率统计（focal method） ───────────────────────
    # 保留每个 Test 的原始行覆盖率列表（不丢失细节）
    per_test_line_coverage:   List[Optional[float]] = field(default_factory=list)
    per_test_branch_coverage: List[Optional[float]] = field(default_factory=list)
    coverage_line_avg:   Optional[float] = None
    coverage_line_max:   Optional[float] = None
    coverage_line_min:   Optional[float] = None
    coverage_branch_avg: Optional[float] = None

    # ── 维度 4：Bug Revealing ────────────────────────────────────
    bug_reveal_count:   int   = 0     # compile_ok 且 bug_revealing=True 的数量
    bug_reveal_checked: int   = 0     # compile_ok 且检测过 bug_revealing 的数量
    bug_reveal_rate:    float = 0.0   # bug_reveal_count / bug_reveal_checked

    # ── 维度 5：Suite 内 Test 间相似度（冗余风险） ───────────────
    max_pairwise_similarity: Optional[float] = None   # 最高 pair 相似度
    # 高冗余 Test pair 列表（相似度 > 0.7）
    high_redundancy_pairs: List[Tuple[str, str, float]] = field(default_factory=list)

    # ── 问题汇总（按问题类型归类，指出哪些 Test 有问题）────────────
    # e.g. {"COMPILE_FAIL": ["Token_1_2Test"], "LOW_LINE_COV": ["Token_1_1Test", ...]}
    problem_tests: Dict[str, List[str]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "n_tests":           self.n_tests,
            "compile_pass_count": self.compile_pass_count,
            "compile_pass_rate":  _r(self.compile_pass_rate),
            "exec_pass_count":    self.exec_pass_count,
            "exec_pass_rate":     _r(self.exec_pass_rate),
            "per_test_line_coverage":   self.per_test_line_coverage,
            "per_test_branch_coverage": self.per_test_branch_coverage,
            "coverage_line_avg":   _r(self.coverage_line_avg),
            "coverage_line_max":   _r(self.coverage_line_max),
            "coverage_line_min":   _r(self.coverage_line_min),
            "coverage_branch_avg": _r(self.coverage_branch_avg),
            "bug_reveal_count":   self.bug_reveal_count,
            "bug_reveal_checked": self.bug_reveal_checked,
            "bug_reveal_rate":    _r(self.bug_reveal_rate),
            "max_pairwise_similarity": _r(self.max_pairwise_similarity),
            "high_redundancy_pairs": [
                {"test1": p[0], "test2": p[1], "similarity": round(p[2], 4)}
                for p in self.high_redundancy_pairs
            ],
            "problem_tests": self.problem_tests,
        }


def _r(v: Optional[float]) -> Optional[float]:
    return round(v, 4) if v is not None else None


# ════════════════════════════════════════════════════════════════════
# Issue priority helper
# ════════════════════════════════════════════════════════════════════

# Lower number = higher priority
_ISSUE_PRIORITY = {
    "COMPILE_FAIL":       0,
    "EXEC_FAIL":          1,
    "EXEC_TIMEOUT":       1,
    "NOT_BUG_REVEALING":  2,
    "LOW_LINE_COV":       3,
    "LOW_BRANCH_COV":     3,
    "HIGH_REDUNDANCY":    4,
}


def sort_issues_by_priority(issues: List[str]) -> List[str]:
    """Return issues sorted from highest priority (lowest number) to lowest."""
    return sorted(issues, key=lambda x: _ISSUE_PRIORITY.get(x, 99))


def highest_priority_issue(issues: List[str]) -> Optional[str]:
    if not issues:
        return None
    return min(issues, key=lambda x: _ISSUE_PRIORITY.get(x, 99))


def issues_at_priority_level(issues: List[str]) -> List[str]:
    """
    Return only the issues at the HIGHEST priority level present.
    e.g. if COMPILE_FAIL and LOW_LINE_COV both present, return only [COMPILE_FAIL].
    """
    if not issues:
        return []
    best = min(_ISSUE_PRIORITY.get(i, 99) for i in issues)
    return [i for i in issues if _ISSUE_PRIORITY.get(i, 99) == best]


# ════════════════════════════════════════════════════════════════════
# Compute functions
# ════════════════════════════════════════════════════════════════════

def compute_test_score(diag) -> TestScore:
    """
    Compute TestScore from TestDiag.

    Issue priority: COMPILE > EXEC > BUG_REVEALING > COVERAGE > REDUNDANCY

    Coverage issues are ONLY raised when:
      - exec passes
      - focal_line_total > 0  (the focal method was actually reached)
      - coverage is below threshold
    """
    compile_s = 1.0 if diag.compile_ok else 0.0
    exec_s    = 1.0 if diag.exec_ok    else 0.0

    line_cov   = (diag.focal_line_rate   / 100.0) if diag.focal_line_rate   is not None else None
    branch_cov = (diag.focal_branch_rate / 100.0) if diag.focal_branch_rate is not None else None

    # Focal method line counts (may be on diag if populated)
    focal_line_covered = getattr(diag, 'focal_line_covered', None)
    focal_line_total   = getattr(diag, 'focal_line_total',   None)

    issues: List[str] = []

    # ── Priority 0: Compile failure ──────────────────────────────
    if not diag.compile_ok:
        issues.append("COMPILE_FAIL")

    else:
        # ── Priority 1: Execution failure ────────────────────────
        if not diag.exec_ok:
            if diag.exec_timeout:
                issues.append("EXEC_TIMEOUT")
            else:
                issues.append("EXEC_FAIL")

        else:
            # Exec passed — check quality dimensions

            # ── Priority 2: Bug revealing ─────────────────────────
            if diag.bug_revealing is False:
                issues.append("NOT_BUG_REVEALING")

            # ── Priority 3: Coverage ──────────────────────────────
            # Only raise if focal method was actually reached (total > 0)
            focal_reached = (focal_line_total is not None and focal_line_total > 0) or \
                            (line_cov is not None)

            if focal_reached:
                if line_cov is not None and line_cov < _LINE_COV_THRESHOLD:
                    issues.append("LOW_LINE_COV")
                if branch_cov is not None and branch_cov < _BRANCH_COV_THRESHOLD:
                    issues.append("LOW_BRANCH_COV")

            # ── Priority 4: Redundancy ────────────────────────────
            if diag.redundancy_score is not None and diag.redundancy_score > _REDUNDANCY_THRESHOLD:
                issues.append("HIGH_REDUNDANCY")

    # Sort by priority
    issues = sort_issues_by_priority(issues)

    return TestScore(
        test_name             = diag.test_name,
        compile_score         = compile_s,
        exec_score            = exec_s,
        focal_line_coverage   = round(line_cov,   4) if line_cov   is not None else None,
        focal_branch_coverage = round(branch_cov, 4) if branch_cov is not None else None,
        focal_line_covered    = focal_line_covered,
        focal_line_total      = focal_line_total,
        bug_reveal_score      = diag.bug_revealing,
        max_similarity        = diag.redundancy_score,
        most_similar_to       = diag.most_similar_to,
        issues                = issues,
    )


def compute_suite_score(
    test_scores: Dict[str, "TestScore"],
    pairwise_sims: Optional[List[Tuple[str, str, float]]] = None,
) -> SuiteScore:
    """
    从所有 TestScore 计算 SuiteScore。

    Parameters
    ----------
    test_scores   : {test_name → TestScore}，key = Test 文件名（如 Token_1_1Test）
    pairwise_sims : 所有 pair 的相似度列表 [(tc1, tc2, score), ...]，
                    由相似度工具计算，用于 Suite 级冗余分析
    """
    if not test_scores:
        return SuiteScore()

    scores = list(test_scores.values())
    n = len(scores)

    # ── 维度 1：编译 ─────────────────────────────────────────────
    compile_pass = sum(1 for s in scores if s.compile_score > 0.5)

    # ── 维度 2：执行 ─────────────────────────────────────────────
    exec_pass = sum(1 for s in scores if s.exec_score > 0.5)

    # ── 维度 3：覆盖率 ────────────────────────────────────────────
    per_line   = [s.focal_line_coverage   for s in scores]
    per_branch = [s.focal_branch_coverage for s in scores]
    line_vals  = [v for v in per_line   if v is not None]
    branch_vals= [v for v in per_branch if v is not None]

    # ── 维度 4：Bug Revealing ────────────────────────────────────
    compile_ok_scores = [s for s in scores if s.compile_score > 0.5]
    br_checked = [s for s in compile_ok_scores if s.bug_reveal_score is not None]
    br_yes     = [s for s in br_checked        if s.bug_reveal_score is True]

    # ── 维度 5：相似度（Suite 内 pair 冗余）──────────────────────
    high_redund_pairs: List[Tuple[str, str, float]] = []
    max_pair_sim: Optional[float] = None
    if pairwise_sims:
        all_sims = sorted(pairwise_sims, key=lambda x: x[2], reverse=True)
        if all_sims:
            max_pair_sim = all_sims[0][2]
        high_redund_pairs = [(t1, t2, sim) for t1, t2, sim in all_sims if sim > 0.7]

    # Problem tests map (issues already sorted by priority in each TestScore)
    problem_tests: Dict[str, List[str]] = {}
    for s in scores:
        for issue in s.issues:
            problem_tests.setdefault(issue, []).append(s.test_name)

    return SuiteScore(
        n_tests             = n,
        compile_pass_count  = compile_pass,
        compile_pass_rate   = round(compile_pass / n, 4),
        exec_pass_count     = exec_pass,
        exec_pass_rate      = round(exec_pass / n, 4),
        per_test_line_coverage   = per_line,
        per_test_branch_coverage = per_branch,
        coverage_line_avg   = round(sum(line_vals)   / len(line_vals),   4) if line_vals   else None,
        coverage_line_max   = round(max(line_vals),  4) if line_vals   else None,
        coverage_line_min   = round(min(line_vals),  4) if line_vals   else None,
        coverage_branch_avg = round(sum(branch_vals) / len(branch_vals), 4) if branch_vals else None,
        bug_reveal_count    = len(br_yes),
        bug_reveal_checked  = len(br_checked),
        bug_reveal_rate     = round(len(br_yes) / len(br_checked), 4) if br_checked else 0.0,
        max_pairwise_similarity = round(max_pair_sim, 4) if max_pair_sim is not None else None,
        high_redundancy_pairs   = high_redund_pairs,
        problem_tests       = problem_tests,
    )