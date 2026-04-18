"""
scoring.py  (redundancy semantics clarification — Issue 2)

Redundancy terminology used throughout the codebase:
  - measure_similarity.py outputs:
      combined_similarity  ∈ [0,1]  (higher = more similar = more redundant)
      redundancy_score     = 1 - combined_similarity  (higher = more redundant)
  - bigSims.csv column 'redundancy_score' = 1 - similarity (higher = worse)
  - TestDiag.redundancy_score stores this value DIRECTLY (no re-inversion).
  - HIGH_REDUNDANCY is raised when redundancy_score > _REDUNDANCY_THRESHOLD
    (i.e. 1-similarity > 0.7, meaning similarity > 0.3 — rather similar).

    Wait — that threshold is inverted from what we want!
    If redundancy_score = 1 - similarity, then:
      redundancy_score > 0.7  ⟺  1-similarity > 0.7  ⟺  similarity < 0.3
    That means we flag as redundant when tests are DISSIMILAR — wrong!

    The correct check should be similarity > threshold, or equivalently
    redundancy_score < (1 - threshold).

    BUT — looking at measure_similarity.py's output again:
      w.writerow([..., f'{redundancy:.6f}'])
      where redundancy = 1.0 - comb_sim

    And bigSims.csv:
      w.writerow([..., f'{rec[3]:.6f}', f'{1.0-rec[3]:.6f}'])
      where rec[3] is comb_sim (similarity), so last col is 1-similarity = redundancy.

    So bigSims.csv column 'redundancy_score' = 1 - similarity.
    When this is stored in TestDiag.redundancy_score:
      HIGH value = high redundancy (bad) = tests are very similar
      LOW value  = low redundancy (good) = tests are diverse

    Therefore the threshold check redundancy_score > 0.7 means:
      1 - similarity > 0.7  ⟺  similarity < 0.3 → tests are DIVERSE → NOT redundant!

    This is the real bug. The fix: use (1 - redundancy_score) > threshold,
    i.e. similarity > threshold, i.e. redundancy_score < (1-threshold).

    Equivalently: flag HIGH_REDUNDANCY when redundancy_score < _SIM_THRESHOLD
    where _SIM_THRESHOLD is the similarity threshold (e.g. 0.7 → flag if sim > 0.7
    → redundancy_score < 0.3).

CORRECTED semantics:
  redundancy_score ∈ [0,1]  from bigSims.csv, = 1 - similarity
  similarity = 1 - redundancy_score
  HIGH_REDUNDANCY iff similarity > _SIM_THRESHOLD
               iff (1 - redundancy_score) > _SIM_THRESHOLD
               iff redundancy_score < (1 - _SIM_THRESHOLD)

Issue priority order:
  COMPILE_FAIL (0) > EXEC_FAIL/TIMEOUT (1) > NOT_BUG_REVEALING (2) >
  LOW_LINE/BRANCH_COV (3) > HIGH_REDUNDANCY (4)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# Coverage thresholds (applied to focal method line/branch rate in 0..1)
_LINE_COV_THRESHOLD   = 0.70
_BRANCH_COV_THRESHOLD = 0.70

# Similarity threshold: flag as HIGH_REDUNDANCY when similarity > this value.
# redundancy_score (from bigSims) = 1 - similarity, so the equivalent check is:
#   redundancy_score < (1 - _SIM_THRESHOLD)
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
    # (high value = more redundant = BAD)
    max_similarity:  Optional[float] = None   # kept as field name for compat
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
            # expose both for clarity
            "redundancy_score":     self.max_similarity,      # = 1-sim
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

    # max pairwise SIMILARITY (1 - redundancy_score) — higher = more redundant
    max_pairwise_similarity: Optional[float] = None
    high_redundancy_pairs: List[Tuple[str, str, float]] = field(default_factory=list)

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
    "LOW_LINE_COV":       3,
    "LOW_BRANCH_COV":     3,
    "HIGH_REDUNDANCY":    4,
}


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
# Compute functions
# ════════════════════════════════════════════════════════════════════

def compute_test_score(diag) -> TestScore:
    """
    Issue 2 fix: redundancy check uses CORRECTED threshold.
      diag.redundancy_score = 1 - similarity  (from bigSims)
      HIGH_REDUNDANCY iff similarity > _SIM_THRESHOLD
                      iff (1 - redundancy_score) > _SIM_THRESHOLD
                      iff redundancy_score < _REDUNDANCY_FLAG_BELOW
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

            # Priority 3: Coverage (only when focal method was actually reached)
            focal_reached = (
                (focal_line_total is not None and focal_line_total > 0) or
                line_cov is not None
            )
            if focal_reached:
                if line_cov is not None and line_cov < _LINE_COV_THRESHOLD:
                    issues.append("LOW_LINE_COV")
                if branch_cov is not None and branch_cov < _BRANCH_COV_THRESHOLD:
                    issues.append("LOW_BRANCH_COV")

            # Priority 4: Redundancy  — Issue 2 corrected check
            rs = diag.redundancy_score  # = 1 - similarity
            if rs is not None and rs < _REDUNDANCY_FLAG_BELOW:
                # similarity = 1 - rs > _SIM_THRESHOLD → redundant
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
        max_similarity        = diag.redundancy_score,  # stored as-is (1-sim)
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

    per_line   = [s.focal_line_coverage   for s in scores]
    per_branch = [s.focal_branch_coverage for s in scores]
    line_vals  = [v for v in per_line   if v is not None]
    branch_vals= [v for v in per_branch if v is not None]

    compile_ok_scores = [s for s in scores if s.compile_score > 0.5]
    br_checked = [s for s in compile_ok_scores if s.bug_reveal_score is not None]
    br_yes     = [s for s in br_checked        if s.bug_reveal_score is True]

    # pairwise_sims carries (tc1, tc2, redundancy_score) where
    # redundancy_score = 1 - similarity.  For suite-level display we want
    # to report SIMILARITY (1 - redundancy_score).
    high_redund_pairs: List[Tuple[str, str, float]] = []
    max_pair_sim: Optional[float] = None
    if pairwise_sims:
        # Convert redundancy_score → similarity for suite-level stats
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