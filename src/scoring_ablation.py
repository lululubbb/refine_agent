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
    sort_issues_by_priority,
)


# ════════════════════════════════════════════════════════════════════
# AblationConfig (unchanged from original)
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
        """
        从预设模式名称创建配置。

        Parameters
        ----------
        mode : str
            "full"                完整模型（所有维度开启）
            "no_coverage"         w/o Coverage Score
            "no_bug_revealing"    w/o Bug-Revealing Score
            "no_redundancy"       w/o Redundancy Score
            "no_compile_exec"     w/o Compile/Exec Score
        """
        if mode == "full":
            return cls(mode=mode)
        elif mode == "no_coverage":
            return cls(use_coverage=False, mode=mode)
        elif mode == "no_bug_revealing":
            return cls(use_bug_revealing=False, mode=mode)
        elif mode == "no_redundancy":
            return cls(use_redundancy=False, mode=mode)
        elif mode == "no_compile_exec":
            return cls(use_compile_exec=False, mode=mode)
        else:
            raise ValueError(f"Unknown ablation mode: {mode!r}")

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
    ini_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "config", "config.ini"
    )
    config.read(ini_path)

    if not config.has_section("ablation"):
        return AblationConfig(mode="full")

    sec = config["ablation"]
    mode = sec.get("mode", "full").strip()

    try:
        cfg = AblationConfig.from_mode(mode)
    except ValueError:
        cfg = AblationConfig(mode=mode)

    if sec.get("use_compile_exec") is not None:
        cfg.use_compile_exec = sec.getboolean("use_compile_exec", True)
    if sec.get("use_coverage") is not None:
        cfg.use_coverage = sec.getboolean("use_coverage", True)
    if sec.get("use_bug_revealing") is not None:
        cfg.use_bug_revealing = sec.getboolean("use_bug_revealing", True)
    if sec.get("use_redundancy") is not None:
        cfg.use_redundancy = sec.getboolean("use_redundancy", True)

    return cfg


# ════════════════════════════════════════════════════════════════════
# Ablation-aware compute_test_score
# ════════════════════════════════════════════════════════════════════

def compute_test_score_ablation(diag, cfg: Optional[AblationConfig] = None) -> TestScore:
    """
    消融版 compute_test_score：根据 AblationConfig 过滤 issues。

    先调用原始 compute_test_score 获取完整的 TestScore，
    再根据消融配置过滤掉不需要的 issues，同时将对应的 score 字段置为 None（而非满分）。
    
    这样做的好处：
    1. 完全不考虑被关闭维度的数据
    2. 避免在统计时混淆（None 值会被合理跳过）
    3. 使消融更加彻底

    Parameters
    ----------
    diag    : TestDiag 对象
    cfg     : AblationConfig（None 时使用 Full Model）

    Returns
    -------
    TestScore（消融后）
    """
    if cfg is None:
        cfg = AblationConfig()

    score = compute_test_score(diag)

    # Filter issues according to ablation config, preserving priority order
    filtered_issues = []
    for issue in score.issues:
        if issue in ("COMPILE_FAIL", "EXEC_FAIL", "EXEC_TIMEOUT") and not cfg.use_compile_exec:
            continue
        if issue in ("LOW_LINE_COV", "LOW_BRANCH_COV") and not cfg.use_coverage:
            continue
        if issue == "NOT_BUG_REVEALING" and not cfg.use_bug_revealing:
            continue
        if issue == "HIGH_REDUNDANCY" and not cfg.use_redundancy:
            continue
        filtered_issues.append(issue)

    score.issues = sort_issues_by_priority(filtered_issues)

    # Null out disabled dimension fields
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
    """
    消融版 compute_suite_score：根据 AblationConfig 调整统计维度。
    
    关键改进：当关闭某维度时，不仅过滤 issues，还要在统计中完全忽略该维度。
    例如在 no_compile_exec 模式下，不呈现编译/执行通过率，而是显示 N/A。

    Parameters
    ----------
    test_scores   : {test_name → TestScore}（已经是消融后的 TestScore）
    pairwise_sims : 所有 pair 的相似度列表
    cfg           : AblationConfig

    Returns
    -------
    SuiteScore（消融后）
    """
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
        line_vals  = [v for v in per_line   if v is not None]
        branch_vals= [v for v in per_branch if v is not None]
        per_line_coverage   = per_line
        per_branch_coverage = per_branch
        coverage_line_avg   = round(sum(line_vals)   / len(line_vals),   4) if line_vals   else None
        coverage_line_max   = round(max(line_vals),  4) if line_vals   else None
        coverage_line_min   = round(min(line_vals),  4) if line_vals   else None
        coverage_branch_avg = round(sum(branch_vals) / len(branch_vals), 4) if branch_vals else None

    bug_reveal_count   = 0
    bug_reveal_checked = 0
    bug_reveal_rate    = 0.0
    if cfg.use_bug_revealing and cfg.use_compile_exec:
        compile_ok_scores = [s for s in scores if s.compile_score is not None and s.compile_score > 0.5]
        br_checked = [s for s in compile_ok_scores if s.bug_reveal_score is not None]
        br_yes     = [s for s in br_checked        if s.bug_reveal_score is True]
        bug_reveal_count   = len(br_yes)
        bug_reveal_checked = len(br_checked)
        bug_reveal_rate    = round(len(br_yes) / len(br_checked), 4) if br_checked else 0.0

    high_redund_pairs: List[Tuple[str, str, float]] = []
    max_pair_sim: Optional[float] = None
    if cfg.use_redundancy and pairwise_sims:
        all_sims = sorted(pairwise_sims, key=lambda x: x[2], reverse=True)
        if all_sims:
            max_pair_sim = all_sims[0][2]
        high_redund_pairs = [(t1, t2, sim) for t1, t2, sim in all_sims if sim > 0.7]

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
        compile_pass_count  = compile_pass_count,
        compile_pass_rate   = compile_pass_rate,
        exec_pass_count     = exec_pass_count,
        exec_pass_rate      = exec_pass_rate,
        per_test_line_coverage   = per_line_coverage,
        per_test_branch_coverage = per_branch_coverage,
        coverage_line_avg   = coverage_line_avg,
        coverage_line_max   = coverage_line_max,
        coverage_line_min   = coverage_line_min,
        coverage_branch_avg = coverage_branch_avg,
        bug_reveal_count    = bug_reveal_count,
        bug_reveal_checked  = bug_reveal_checked,
        bug_reveal_rate     = bug_reveal_rate,
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
    """
    计算消融后的 final_score。

    Parameters
    ----------
    compile_score, exec_score : float
    coverage_score            : float (0~1) or '' (not available)
    bug_revealing_score       : float (0 or 1) or '' (not available)
    redundancy_score          : float (0~1, 相似度) or '' (not available)
    cfg                       : AblationConfig

    Returns
    -------
    (final_score: float, valid_weight_pct: float)
        valid_weight_pct 表示有效维度的权重占比
    """
    if cfg is None:
        cfg = AblationConfig()

    weights = cfg.effective_weights()
    sw = []
    vw = 0.0

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