"""
scoring_ablation.py
====================
消融实验支持：通过配置文件控制各评估维度的开关。

消融实验设计：
  - Full Model:               4 个维度全开（编译执行 + 覆盖率 + Bug揭示 + 冗余度）
  - w/o Coverage Score:       去掉覆盖率维度，保留其余 3 个
  - w/o Bug-Revealing Score:  去掉 Bug 揭示维度，保留其余 3 个
  - w/o Redundancy Score:     去掉冗余度维度，保留其余 3 个
  - w/o Compile/Exec Score:   去掉编译执行维度，保留其余 3 个

"""
from __future__ import annotations

import os
import sys
import configparser
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from scoring import (
    TestScore, SuiteScore,
    compute_test_score, compute_suite_score,
    sort_issues_by_priority, issues_at_priority_level,
    _SIM_THRESHOLD, _REDUNDANCY_FLAG_BELOW,
)


# ════════════════════════════════════════════════════════════════════
# AblationConfig
# ════════════════════════════════════════════════════════════════════

@dataclass
class AblationConfig:
    """
    控制各评估维度是否启用的配置。

    Attributes
    ----------
    use_compile_exec : bool
        是否启用编译/执行维度（COMPILE_FAIL, EXEC_FAIL, EXEC_TIMEOUT）
        关闭后：所有 test 的 compile_score=1.0, exec_score=1.0（不产生这两类 issue）
    use_coverage : bool
        是否启用覆盖率维度（LOW_LINE_COV, LOW_BRANCH_COV）
        关闭后：覆盖率不影响 issue 列表，Refiner 不会生成覆盖率相关指令
    use_bug_revealing : bool
        是否启用 Bug Revealing 维度（NOT_BUG_REVEALING）
        关闭后：bug_revealing 不影响 issue 列表
    use_redundancy : bool
        是否启用冗余度维度（HIGH_REDUNDANCY）
        关闭后：redundancy_score 不影响 issue 列表，不会触发删除操作
    mode : str
        预设模式名称，方便日志记录
    """
    use_compile_exec:  bool = True
    use_coverage:      bool = True
    use_bug_revealing: bool = True
    use_redundancy:    bool = True
    mode: str = "full"

    _WC: float = 0.15
    _WE: float = 0.15
    _WV: float = 0.30
    _WB: float = 0.20
    _WR: float = 0.20

    def effective_weights(self) -> Dict[str, float]:
        raw = {
            "compile":    self._WC if self.use_compile_exec else 0.0,
            "exec":       self._WE if self.use_compile_exec else 0.0,
            "coverage":   self._WV if self.use_coverage    else 0.0,
            "bug":        self._WB if self.use_bug_revealing else 0.0,
            "redundancy": self._WR if self.use_redundancy  else 0.0,
        }
        total = sum(raw.values())
        if total <= 0:
            return {k: 1.0 / len(raw) for k in raw}
        return {k: v / total for k, v in raw.items()}

    @classmethod
    def from_mode(cls, mode: str) -> "AblationConfig":
        modes = {
            "full":             cls,
            "no_coverage":      lambda: cls(use_coverage=False, mode=mode),
            "no_bug_revealing": lambda: cls(use_bug_revealing=False, mode=mode),
            "no_redundancy":    lambda: cls(use_redundancy=False, mode=mode),
            "no_compile_exec":  lambda: cls(use_compile_exec=False, mode=mode),
        }
        if mode not in modes:
            raise ValueError(f"Unknown ablation mode: {mode!r}")
        return modes[mode]() if mode != "full" else cls(mode=mode)

    def __str__(self) -> str:
        flags = []
        if not self.use_compile_exec:  flags.append("NO_COMPILE_EXEC")
        if not self.use_coverage:      flags.append("NO_COVERAGE")
        if not self.use_bug_revealing: flags.append("NO_BUG_REVEALING")
        if not self.use_redundancy:    flags.append("NO_REDUNDANCY")
        suffix = ("(" + ", ".join(flags) + ")") if flags else "(Full Model)"
        return f"AblationConfig[mode={self.mode}] {suffix}"


# ════════════════════════════════════════════════════════════════════
# Read ablation config from config.ini
# ════════════════════════════════════════════════════════════════════

def get_ablation_config() -> AblationConfig:
    """
    从 config/config.ini 的 [ablation] 节读取消融配置。
    如果 [ablation] 节不存在，返回 Full Model 配置。

    config.ini 格式示例：
        [ablation]
        mode = no_coverage
        # 也可以用布尔开关覆盖：
        # use_compile_exec = true
        # use_coverage = false
        # use_bug_revealing = true
        # use_redundancy = true
    """
    config = configparser.ConfigParser()
    ini_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "config", "config.ini")
    config.read(ini_path)
    if not config.has_section("ablation"):
        return AblationConfig(mode="full")
    sec = config["ablation"]
    mode = sec.get("mode", "full").strip()
    try:
        cfg = AblationConfig.from_mode(mode)
    except ValueError:
        cfg = AblationConfig(mode=mode)
    for attr in ("use_compile_exec", "use_coverage", "use_bug_revealing", "use_redundancy"):
        if sec.get(attr) is not None:
            setattr(cfg, attr, sec.getboolean(attr, True))
    return cfg


# ════════════════════════════════════════════════════════════════════
# Ablation-aware scoring
# ════════════════════════════════════════════════════════════════════

def compute_test_score_ablation(diag, cfg: Optional[AblationConfig] = None) -> TestScore:
    if cfg is None:
        cfg = AblationConfig()

    score = compute_test_score(diag)

    filtered = []
    for issue in score.issues:
        if issue in ("COMPILE_FAIL","EXEC_FAIL","EXEC_TIMEOUT") and not cfg.use_compile_exec:
            continue
        if issue in ("LOW_LINE_COV","LOW_BRANCH_COV") and not cfg.use_coverage:
            continue
        if issue == "NOT_BUG_REVEALING" and not cfg.use_bug_revealing:
            continue
        if issue == "HIGH_REDUNDANCY" and not cfg.use_redundancy:
            continue
        filtered.append(issue)

    score.issues = sort_issues_by_priority(filtered)

    if not cfg.use_compile_exec:
        score.compile_score = None
        score.exec_score    = None
    if not cfg.use_coverage:
        score.focal_line_coverage   = None
        score.focal_branch_coverage = None
        score.focal_line_covered    = None
        score.focal_line_total      = None
    if not cfg.use_bug_revealing:
        score.bug_reveal_score = None
    if not cfg.use_redundancy:
        score.max_similarity  = None
        score.most_similar_to = None

    return score


# ════════════════════════════════════════════════════════════════════
# Ablation-aware compute_suite_score
# ════════════════════════════════════════════════════════════════════

def compute_suite_score_ablation(
    test_scores: Dict[str, "TestScore"],
    pairwise_sims: Optional[List[Tuple[str, str, float]]] = None,
    cfg: Optional[AblationConfig] = None,
) -> SuiteScore:
    if cfg is None:
        cfg = AblationConfig()

    if not test_scores:
        empty_suite = SuiteScore()
        if not cfg.use_compile_exec:
            empty_suite.compile_pass_rate = None
            empty_suite.exec_pass_rate    = None
        if not cfg.use_coverage:
            empty_suite.coverage_line_avg = None
            empty_suite.coverage_line_max = None
            empty_suite.coverage_line_min = None
            empty_suite.coverage_branch_avg = None
        if not cfg.use_bug_revealing:
            empty_suite.bug_reveal_rate = None
        return empty_suite

    scores = list(test_scores.values())
    n = len(scores)

    compile_pass_count  = 0
    compile_pass_rate   = None
    if cfg.use_compile_exec:
        compile_pass_count = sum(
            1 for s in scores if s.compile_score is not None and s.compile_score > 0.5)
        compile_pass_rate = round(compile_pass_count / n, 4)

    exec_pass_count = 0
    exec_pass_rate  = None
    if cfg.use_compile_exec:
        exec_pass_count = sum(
            1 for s in scores if s.exec_score is not None and s.exec_score > 0.5)
        exec_pass_rate = round(exec_pass_count / n, 4)

    per_line_coverage   = None
    per_branch_coverage = None
    coverage_line_avg   = None
    coverage_line_max   = None
    coverage_line_min   = None
    coverage_branch_avg = None
    if cfg.use_coverage:
        per_line   = [s.focal_line_coverage   for s in scores]
        per_branch = [s.focal_branch_coverage for s in scores]
        lv = [v for v in per_line   if v is not None]
        bv = [v for v in per_branch if v is not None]
        cov_line_avg   = round(sum(lv)/len(lv), 4) if lv else None
        cov_line_max   = round(max(lv), 4)         if lv else None
        cov_line_min   = round(min(lv), 4)         if lv else None
        cov_branch_avg = round(sum(bv)/len(bv), 4) if bv else None

    br_count = br_checked = 0
    br_rate = 0.0
    if cfg.use_bug_revealing and cfg.use_compile_exec:
        ok_scores  = [s for s in scores if s.compile_score is not None and s.compile_score > 0.5]
        checked    = [s for s in ok_scores if s.bug_reveal_score is not None]
        yes        = [s for s in checked   if s.bug_reveal_score is True]
        br_count   = len(yes); br_checked = len(checked)
        br_rate    = round(len(yes)/len(checked), 4) if checked else 0.0

    high_redund_pairs = []
    max_pair_sim = None
    if cfg.use_redundancy and pairwise_sims:
        # pairwise_sims = (tc1, tc2, redundancy_score=1-sim)
        sim_pairs = [(t1, t2, 1.0-rs) for t1, t2, rs in pairwise_sims]
        sim_pairs_s = sorted(sim_pairs, key=lambda x: x[2], reverse=True)
        if sim_pairs_s:
            max_pair_sim = sim_pairs_s[0][2]
        high_redund_pairs = [(t1, t2, sim) for t1, t2, sim in sim_pairs_s
                             if sim > _SIM_THRESHOLD]

    problem_tests: Dict[str, List[str]] = {}
    for s in scores:
        for issue in s.issues:
            if issue in ("COMPILE_FAIL", "EXEC_FAIL", "EXEC_TIMEOUT") and not cfg.use_compile_exec:
                continue
            if issue in ("LOW_LINE_COV", "LOW_BRANCH_COV") and not cfg.use_coverage:
                continue
            if issue == "NOT_BUG_REVEALING" and not cfg.use_bug_revealing:
                continue
            if issue == "HIGH_REDUNDANCY" and not cfg.use_redundancy:
                continue
            problem_tests.setdefault(issue, []).append(s.test_name)

    return SuiteScore(
        n_tests             = n,
        compile_pass_count  = compile_pass_count or 0,
        compile_pass_rate   = compile_pass_rate,
        exec_pass_count     = exec_pass_count or 0,
        exec_pass_rate      = exec_pass_rate,
        per_test_line_coverage   = per_line,
        per_test_branch_coverage = per_branch,
        coverage_line_avg   = cov_line_avg,
        coverage_line_max   = cov_line_max,
        coverage_line_min   = cov_line_min,
        coverage_branch_avg = cov_branch_avg,
        bug_reveal_count    = br_count,
        bug_reveal_checked  = br_checked,
        bug_reveal_rate     = br_rate,
        max_pairwise_similarity = round(max_pair_sim, 4) if max_pair_sim is not None else None,
        high_redundancy_pairs   = high_redund_pairs,
        problem_tests       = problem_tests,
    )


# ════════════════════════════════════════════════════════════════════
# Final score calculation (unchanged logic)
# ════════════════════════════════════════════════════════════════════

def compute_final_score_ablation(
    compile_score: float,
    exec_score: float,
    coverage_score,
    bug_revealing_score,
    redundancy_score,
    cfg: Optional[AblationConfig] = None,
) -> Tuple[float, float]:
    if cfg is None:
        cfg = AblationConfig()
    weights = cfg.effective_weights()
    sw, vw = [], 0.0
    if cfg.use_compile_exec:
        if isinstance(compile_score, (int, float)):
            sw.append(compile_score * weights["compile"])
            vw += weights["compile"]
        if isinstance(exec_score, (int, float)):
            sw.append(exec_score * weights["exec"])
            vw += weights["exec"]

    if cfg.use_coverage and isinstance(coverage_score, (int, float)):
        sw.append(coverage_score * weights["coverage"])
        vw += weights["coverage"]

    if cfg.use_bug_revealing and isinstance(bug_revealing_score, (int, float)):
        sw.append(bug_revealing_score * weights["bug"])
        vw += weights["bug"]

    if cfg.use_redundancy and isinstance(redundancy_score, (int, float)):
        rd = 1.0 - redundancy_score
        sw.append(rd * weights["redundancy"])
        vw += weights["redundancy"]

    fs = round(sum(sw) / vw, 6) if vw > 0 else 0.0
    return fs, round(vw, 4)


# ════════════════════════════════════════════════════════════════════
# Global singleton
# ════════════════════════════════════════════════════════════════════

_GLOBAL_ABLATION_CONFIG: Optional[AblationConfig] = None


def global_ablation_config() -> AblationConfig:
    global _GLOBAL_ABLATION_CONFIG
    if _GLOBAL_ABLATION_CONFIG is None:
        _GLOBAL_ABLATION_CONFIG = get_ablation_config()
        print(f"[AblationConfig] {_GLOBAL_ABLATION_CONFIG}", flush=True)
    return _GLOBAL_ABLATION_CONFIG


def reset_global_ablation_config(cfg: Optional[AblationConfig] = None):
    global _GLOBAL_ABLATION_CONFIG
    _GLOBAL_ABLATION_CONFIG = cfg