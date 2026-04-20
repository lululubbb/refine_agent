"""
scoring.py  (v3 — simplified)

Key changes:
  - Coverage threshold raised to 0.80 (80%)
  - LOW_COVERAGE issue raised when line_cov < 0.80 OR branch_cov < 0.80
    (previously only branch; now handles focal methods with no branches via line)
  - If branch data is N/A (None), only line coverage is checked
  - If line data is N/A (None), only branch coverage is checked
  - Removed HIGH_REDUNDANCY from per-test scoring (still tracked at suite level)

Issue priority order:
  COMPILE_FAIL (0) > EXEC_FAIL/TIMEOUT (1) > NOT_BUG_REVEALING (2) > LOW_COVERAGE (3) > HIGH_REDUNDANCY (4)

Redundancy terminology:
  redundancy_score from bigSims.csv = 1 - similarity  (higher = more redundant)
  HIGH_REDUNDANCY iff similarity > _SIM_THRESHOLD
               iff (1 - redundancy_score) > _SIM_THRESHOLD
               iff redundancy_score < _REDUNDANCY_FLAG_BELOW
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# Coverage threshold — 80% for both line and branch
_LINE_COV_THRESHOLD   = 0.80
_BRANCH_COV_THRESHOLD = 0.80

# Similarity threshold: flag as HIGH_REDUNDANCY when similarity > this value.
_SIM_THRESHOLD        = 0.70
_REDUNDANCY_FLAG_BELOW = 1.0 - _SIM_THRESHOLD   # = 0.30


# ════════════════════════════════════════════════════════════════════
# TestScore
# ════════════════════════════════════════════════════════════════════

@dataclass
class TestScore:
    test_name: str

    compile_score: float = 0.0
    exec_score:    float = 0.0

    focal_line_coverage:   Optional[float] = None
    focal_branch_coverage: Optional[float] = None
    focal_line_covered:    Optional[int]   = None
    focal_line_total:      Optional[int]   = None

    bug_reveal_score: Optional[bool] = None

    # redundancy_score stored from bigSims = 1 - similarity
    max_similarity:  Optional[float] = None
    most_similar_to: Optional[str]   = None

    issues: List[str] = field(default_factory=list)

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
            "redundancy_score":     self.max_similarity,
            "similarity":           round(1.0 - self.max_similarity, 4)
                                    if self.max_similarity is not None else None,
            "most_similar_to":      self.most_similar_to,
            "issues":               self.issues,
        }


# ════════════════════════════════════════════════════════════════════
# SuiteScore
# ════════════════════════════════════════════════════════════════════

@dataclass
class SuiteScore:
    n_tests: int = 0

    compile_pass_count: int   = 0
    compile_pass_rate:  float = 0.0
    exec_pass_count:    int   = 0
    exec_pass_rate:     float = 0.0

    per_test_line_coverage:   List[Optional[float]] = field(default_factory=list)
    per_test_branch_coverage: List[Optional[float]] = field(default_factory=list)
    coverage_line_avg:   Optional[float] = None
    coverage_line_max:   Optional[float] = None
    coverage_line_min:   Optional[float] = None
    coverage_branch_avg: Optional[float] = None

    bug_reveal_count:   int   = 0
    bug_reveal_checked: int   = 0
    bug_reveal_rate:    float = 0.0

    max_pairwise_similarity: Optional[float] = None
    high_redundancy_pairs: List[Tuple[str, str, float]] = field(default_factory=list)

    problem_tests: Dict[str, List[str]] = field(default_factory=dict)

    # Suite-level flag: are ALL tests compile-passing?
    all_compile_pass: bool = False

    def to_dict(self) -> dict:
        return {
            "n_tests":           self.n_tests,
            "compile_pass_count": self.compile_pass_count,
            "compile_pass_rate":  _r(self.compile_pass_rate),
            "exec_pass_count":    self.exec_pass_count,
            "exec_pass_rate":     _r(self.exec_pass_rate),
            "all_compile_pass":   self.all_compile_pass,
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


def _r(v):
    return round(v, 4) if v is not None else None


# ════════════════════════════════════════════════════════════════════
# Priority helpers
# ════════════════════════════════════════════════════════════════════

_ISSUE_PRIORITY = {
    "COMPILE_FAIL":       0,
    "EXEC_FAIL":          1,
    "EXEC_TIMEOUT":       1,
    "NOT_BUG_REVEALING":  2,
    "LOW_COVERAGE":       3,
    "HIGH_REDUNDANCY":    4,
}

# Keep legacy names for backward compat
_ISSUE_PRIORITY["LOW_LINE_COV"]   = 3
_ISSUE_PRIORITY["LOW_BRANCH_COV"] = 3


def sort_issues_by_priority(issues: List[str]) -> List[str]:
    return sorted(issues, key=lambda x: _ISSUE_PRIORITY.get(x, 99))


def highest_priority_issue(issues: List[str]) -> Optional[str]:
    if not issues:
        return None
    return min(issues, key=lambda x: _ISSUE_PRIORITY.get(x, 99))


def issues_at_priority_level(issues: List[str]) -> List[str]:
    """Return only the issues at the highest priority level present."""
    if not issues:
        return []
    best = min(_ISSUE_PRIORITY.get(i, 99) for i in issues)
    return [i for i in issues if _ISSUE_PRIORITY.get(i, 99) == best]


# ════════════════════════════════════════════════════════════════════
# Coverage issue detection helper
# ════════════════════════════════════════════════════════════════════

def _has_coverage_issue(line_cov: Optional[float], branch_cov: Optional[float]) -> bool:
    """
    Returns True if there is a coverage issue.

    Logic:
    - If line coverage is available and below threshold → issue
    - If branch coverage is available and below threshold → issue
    - If BOTH are None (no data at all) → no issue flagged (can't tell)
    - If only one is available, only that one is checked

    This handles focal methods with no branches (branch=N/A): in that case
    only line coverage is checked, preventing false-negative "all N/A = no issue".
    """
    has_line   = line_cov is not None
    has_branch = branch_cov is not None

    if not has_line and not has_branch:
        return False  # no coverage data available

    line_fail   = has_line   and line_cov   < _LINE_COV_THRESHOLD
    branch_fail = has_branch and branch_cov < _BRANCH_COV_THRESHOLD

    return line_fail or branch_fail


# ════════════════════════════════════════════════════════════════════
# Compute functions
# ════════════════════════════════════════════════════════════════════

def compute_test_score(diag) -> TestScore:
    """
    Compute per-test score.

    Coverage issue: raised when line OR branch coverage < 80%,
    so that simple focal methods (no branches → branch=N/A) are still
    correctly evaluated via line coverage alone.
    """
    compile_s = 1.0 if diag.compile_ok else 0.0
    exec_s    = 1.0 if diag.exec_ok    else 0.0

    line_cov   = (diag.focal_line_rate   / 100.0) if diag.focal_line_rate   is not None else None
    branch_cov = (diag.focal_branch_rate / 100.0) if diag.focal_branch_rate is not None else None

    focal_line_covered = getattr(diag, 'focal_line_covered', None)
    focal_line_total   = getattr(diag, 'focal_line_total',   None)

    issues: List[str] = []

    if not diag.compile_ok:
        issues.append("COMPILE_FAIL")
    else:
        if not diag.exec_ok:
            issues.append("EXEC_TIMEOUT" if diag.exec_timeout else "EXEC_FAIL")
        else:
            # Priority 2: Bug revealing
            if diag.bug_revealing is False:
                issues.append("NOT_BUG_REVEALING")

            # Priority 3: Coverage — line OR branch below 80%
            focal_reached = (
                (focal_line_total is not None and focal_line_total > 0) or
                line_cov is not None or branch_cov is not None
            )
            if focal_reached and _has_coverage_issue(line_cov, branch_cov):
                issues.append("LOW_COVERAGE")

            # Priority 4: Redundancy
            rs = diag.redundancy_score  # = 1 - similarity
            if rs is not None and rs < _REDUNDANCY_FLAG_BELOW:
                issues.append("HIGH_REDUNDANCY")

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
    if not test_scores:
        return SuiteScore()

    scores = list(test_scores.values())
    n = len(scores)

    compile_pass = sum(1 for s in scores if s.compile_score > 0.5)
    exec_pass    = sum(1 for s in scores if s.exec_score    > 0.5)
    all_compile  = (compile_pass == n)

    per_line   = [s.focal_line_coverage   for s in scores]
    per_branch = [s.focal_branch_coverage for s in scores]
    line_vals  = [v for v in per_line   if v is not None]
    branch_vals= [v for v in per_branch if v is not None]

    compile_ok_scores = [s for s in scores if s.compile_score > 0.5]
    br_checked = [s for s in compile_ok_scores if s.bug_reveal_score is not None]
    br_yes     = [s for s in br_checked        if s.bug_reveal_score is True]

    high_redund_pairs: List[Tuple[str, str, float]] = []
    max_pair_sim: Optional[float] = None
    if pairwise_sims:
        sim_pairs = [(t1, t2, 1.0 - rs) for t1, t2, rs in pairwise_sims]
        sim_pairs_sorted = sorted(sim_pairs, key=lambda x: x[2], reverse=True)
        if sim_pairs_sorted:
            max_pair_sim = sim_pairs_sorted[0][2]
        high_redund_pairs = [(t1, t2, sim) for t1, t2, sim in sim_pairs_sorted
                             if sim > _SIM_THRESHOLD]

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
        all_compile_pass    = all_compile,
        per_test_line_coverage   = per_line,
        per_test_branch_coverage = per_branch,
        coverage_line_avg   = round(sum(line_vals) / len(line_vals), 4)   if line_vals   else None,
        coverage_line_max   = round(max(line_vals), 4)                     if line_vals   else None,
        coverage_line_min   = round(min(line_vals), 4)                     if line_vals   else None,
        coverage_branch_avg = round(sum(branch_vals) / len(branch_vals), 4) if branch_vals else None,
        bug_reveal_count    = len(br_yes),
        bug_reveal_checked  = len(br_checked),
        bug_reveal_rate     = round(len(br_yes) / len(br_checked), 4) if br_checked else 0.0,
        max_pairwise_similarity = round(max_pair_sim, 4) if max_pair_sim is not None else None,
        high_redundancy_pairs   = high_redund_pairs,
        problem_tests       = problem_tests,
    )