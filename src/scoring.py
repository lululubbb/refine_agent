"""
scoring.py  (v3 — 概念修正版)
==============================

概念定义（与用户需求完全对齐）
─────────────────────────────────────────────────────────────────
Test  = 一个 Java 测试文件，如 Token_1_1Test.java
        （里面可以含多个 @Test 方法，但评估粒度是文件级别）
Suite = 针对同一 focal method 生成的 test_number 个 Test 文件集合
        e.g. Token_1_1Test.java + Token_1_2Test.java + ... + Token_1_5Test.java
─────────────────────────────────────────────────────────────────

评分原则
─────────────────────────────────────────────────────────────────
1. 不需要加权综合分（final_score）——去掉
2. 每个维度独立打分，供 Refiner 分别分析
3. Test 级（针对单个 Test 文件）：
     - compile_score:   0/1，该 Test 文件是否能编译
     - exec_score:      0/1，该 Test 文件是否能执行无异常
     - coverage_score:  该 Test 文件对 focal method 的行/分支覆盖率（0~1）
     - bug_reveal_score:该 Test 文件是否能揭示 bug（0/1/None）
     - redundancy_score:该 Test 文件与 Suite 中其他 Test 的最高 AST 相似度（0~1）
4. Suite 级（针对 N 个 Test 文件整体）：
     - compile_pass_count / compile_pass_rate
     - exec_pass_count / exec_pass_rate
     - coverage_values:   每个 Test 的覆盖率列表（不聚合，保留细节）
     - coverage_avg / coverage_max / coverage_min
     - bug_reveal_count / bug_reveal_rate（只统计 exec_ok 的 Test）
     - max_pairwise_similarity: 所有 Test pair 中最高的相似度（整体冗余风险）
     - problem_tests: {issue_type: [test_names]}  按问题类型分类的 Test 列表
─────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ════════════════════════════════════════════════════════════════════
# Test 级评分（一个 Test 文件的各维度分数）
# ════════════════════════════════════════════════════════════════════

@dataclass
class TestScore:
    """
    单个 Test 文件（Token_1_{seq}Test.java）的多维度分数。
    无加权综合分，每个维度独立呈现给 Refiner。
    """
    test_name: str              # e.g. "Token_1_1Test"

    # ── 维度 1：编译 ─────────────────────────────────────────────
    compile_score: float = 0.0  # 0=编译失败，1=编译通过

    # ── 维度 2：执行 ─────────────────────────────────────────────
    exec_score: float = 0.0     # 0=运行失败/超时，1=运行通过

    # ── 维度 3：覆盖率（focal method） ───────────────────────────
    focal_line_coverage:   Optional[float] = None   # 0~1，行覆盖率
    focal_branch_coverage: Optional[float] = None   # 0~1，分支覆盖率
    # 注：coverage 保持原始值，不合并，让 Refiner 自行分析

    # ── 维度 4：Bug Revealing ────────────────────────────────────
    bug_reveal_score: Optional[bool] = None  # True/False/None(未检测)

    # ── 维度 5：相似度（与 Suite 内其他 Test 的最高相似度）────────
    max_similarity: Optional[float] = None   # 0~1，越高越冗余
    most_similar_to: Optional[str]  = None   # 最相似的 Test 文件名

    # ── 问题标签（脚本判定，供 Refiner 快速定位）─────────────────
    issues: List[str] = field(default_factory=list)
    # 可能的值：COMPILE_FAIL | EXEC_FAIL | EXEC_TIMEOUT |
    #           LOW_LINE_COV | LOW_BRANCH_COV | NOT_BUG_REVEALING | HIGH_REDUNDANCY

    def to_dict(self) -> dict:
        return {
            "test_name":            self.test_name,
            "compile_score":        self.compile_score,
            "exec_score":           self.exec_score,
            "focal_line_coverage":  self.focal_line_coverage,
            "focal_branch_coverage":self.focal_branch_coverage,
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
    compile_pass_rate:  float = 0.0    # 通过数 / 总数

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
    bug_reveal_count:   int   = 0     # exec_ok 且 bug_revealing=True 的数量
    bug_reveal_checked: int   = 0     # exec_ok 且检测过 bug_revealing 的数量
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
            # 维度 1
            "compile_pass_count": self.compile_pass_count,
            "compile_pass_rate":  round(self.compile_pass_rate, 4),
            # 维度 2
            "exec_pass_count":    self.exec_pass_count,
            "exec_pass_rate":     round(self.exec_pass_rate, 4),
            # 维度 3
            "per_test_line_coverage":   self.per_test_line_coverage,
            "per_test_branch_coverage": self.per_test_branch_coverage,
            "coverage_line_avg":   _r(self.coverage_line_avg),
            "coverage_line_max":   _r(self.coverage_line_max),
            "coverage_line_min":   _r(self.coverage_line_min),
            "coverage_branch_avg": _r(self.coverage_branch_avg),
            # 维度 4
            "bug_reveal_count":   self.bug_reveal_count,
            "bug_reveal_checked": self.bug_reveal_checked,
            "bug_reveal_rate":    round(self.bug_reveal_rate, 4),
            # 维度 5
            "max_pairwise_similarity": _r(self.max_pairwise_similarity),
            "high_redundancy_pairs": [
                {"test1": p[0], "test2": p[1], "similarity": round(p[2], 4)}
                for p in self.high_redundancy_pairs
            ],
            # 问题汇总
            "problem_tests": self.problem_tests,
        }


def _r(v: Optional[float]) -> Optional[float]:
    return round(v, 4) if v is not None else None


# ════════════════════════════════════════════════════════════════════
# 计算函数
# ════════════════════════════════════════════════════════════════════

def compute_test_score(diag) -> TestScore:
    """
    从 TestDiag（工具调用原始数据）计算 TestScore。
    diag 是 refine_agent.TestDiag 实例，代表一个 Test 文件的诊断结果。
    """
    compile_s = 1.0 if diag.compile_ok else 0.0
    exec_s    = 1.0 if diag.exec_ok    else 0.0

    # 覆盖率：保持原始 0~1 值（TestRunner 已从 JaCoCo 获取）
    line_cov   = (diag.focal_line_rate   / 100.0) if diag.focal_line_rate   is not None else None
    branch_cov = (diag.focal_branch_rate / 100.0) if diag.focal_branch_rate is not None else None

    # 问题标签
    issues: List[str] = []
    if not diag.compile_ok:
        issues.append("COMPILE_FAIL")
    else:
        if not diag.exec_ok:
            issues.append("EXEC_TIMEOUT" if diag.exec_timeout else "EXEC_FAIL")

    if diag.exec_ok:
        if line_cov is not None and line_cov < 0.5:
            issues.append("LOW_LINE_COV")
        if branch_cov is not None and branch_cov < 0.5:
            issues.append("LOW_BRANCH_COV")
        if diag.bug_revealing is False:
            issues.append("NOT_BUG_REVEALING")

    if diag.redundancy_score is not None and diag.redundancy_score > 0.7:
        issues.append("HIGH_REDUNDANCY")

    return TestScore(
        test_name             = diag.test_name,
        compile_score         = compile_s,
        exec_score            = exec_s,
        focal_line_coverage   = round(line_cov,   4) if line_cov   is not None else None,
        focal_branch_coverage = round(branch_cov, 4) if branch_cov is not None else None,
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
    exec_ok_scores = [s for s in scores if s.exec_score > 0.5]
    br_checked = [s for s in exec_ok_scores if s.bug_reveal_score is not None]
    br_yes     = [s for s in br_checked    if s.bug_reveal_score is True]

    # ── 维度 5：相似度（Suite 内 pair 冗余）──────────────────────
    high_redund_pairs: List[Tuple[str, str, float]] = []
    max_pair_sim: Optional[float] = None
    if pairwise_sims:
        all_sims = sorted(pairwise_sims, key=lambda x: x[2], reverse=True)
        if all_sims:
            max_pair_sim = all_sims[0][2]
        high_redund_pairs = [(t1, t2, sim) for t1, t2, sim in all_sims if sim > 0.7]

    # ── 问题汇总 ─────────────────────────────────────────────────
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
