"""
llm_stats_tracker.py
====================
统一的 LLM 调用统计追踪器，与 HITS baseline 的 LLMStatsTracker 保持完全一致：

  - 仅统计 LLM API 调用本身的 wall-clock 时间（不含 TestRunner、相似度计算等工具链耗时）
  - 分别记录 prompt_tokens / completion_tokens（与 HITS 字段命名一致）
  - 支持按 role（generator / refiner）分类统计
  - 支持按 phase（phase1 / round_N）分组统计
  - token 来自每次 API 响应的 usage.prompt_tokens / usage.completion_tokens
  - time  为每次 chat() 调用的 t_end - t_start（requests.post 前后），
    即纯 HTTP 往返时间，不含任何本地处理逻辑
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ════════════════════════════════════════════════════════════════════
# 单次调用记录
# ════════════════════════════════════════════════════════════════════

@dataclass
class LLMCallRecord:
    """记录单次 LLM API 调用的统计数据（与 HITS LLMStatsTracker 字段对齐）。"""
    role: str                   # "generator" | "refiner"
    phase: str                  # "phase1" | "round_1" | "round_2" | ...
    prompt_tokens: int          # usage.prompt_tokens
    completion_tokens: int      # usage.completion_tokens
    elapsed_seconds: float      # LLM API wall-clock time（纯 HTTP 往返）

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


# ════════════════════════════════════════════════════════════════════
# LLMStatsTracker（主类，对齐 HITS baseline）
# ════════════════════════════════════════════════════════════════════

class LLMStatsTracker:
    """
    与 HITS baseline LLMStatsTracker 完全一致的统计追踪器。

    用法：
        tracker = LLMStatsTracker()

        # 每次 LLM 调用后记录
        tracker.record("generator", "phase1", llm_result)
        tracker.record("refiner", "round_1", llm_result)

        # 导出为与 HITS 完全相同的字典结构
        stats = tracker.to_dict()
    """

    def __init__(self):
        self._records: List[LLMCallRecord] = []

    def record(self, role: str, phase: str, llm_result) -> None:
        """
        记录一次 LLM 调用。

        Parameters
        ----------
        role       : "generator" | "refiner"
        phase      : "phase1" | "round_1" | "round_2" | ...
        llm_result : LLMCallResult 实例（含 prompt_tokens, completion_tokens, elapsed_seconds）
        """
        if llm_result is None:
            return
        self._records.append(LLMCallRecord(
            role              = role,
            phase             = phase,
            prompt_tokens     = llm_result.prompt_tokens,
            completion_tokens = llm_result.completion_tokens,
            elapsed_seconds   = llm_result.elapsed_seconds,
        ))

    # ── 聚合查询 ─────────────────────────────────────────────────────

    def _filter(self, role: Optional[str] = None,
                phase: Optional[str] = None) -> List[LLMCallRecord]:
        recs = self._records
        if role:
            recs = [r for r in recs if r.role == role]
        if phase:
            recs = [r for r in recs if r.phase == phase]
        return recs

    def prompt_tokens(self, role: Optional[str] = None,
                      phase: Optional[str] = None) -> int:
        return sum(r.prompt_tokens for r in self._filter(role, phase))

    def completion_tokens(self, role: Optional[str] = None,
                          phase: Optional[str] = None) -> int:
        return sum(r.completion_tokens for r in self._filter(role, phase))

    def total_tokens(self, role: Optional[str] = None,
                     phase: Optional[str] = None) -> int:
        return sum(r.total_tokens for r in self._filter(role, phase))

    def elapsed_seconds(self, role: Optional[str] = None,
                        phase: Optional[str] = None) -> float:
        """仅统计 LLM API 调用时间（不含工具链）。"""
        return sum(r.elapsed_seconds for r in self._filter(role, phase))

    def call_count(self, role: Optional[str] = None,
                   phase: Optional[str] = None) -> int:
        return len(self._filter(role, phase))

    # ── 导出（与 HITS 字段完全一致）─────────────────────────────────

    def to_dict(self) -> dict:
        """
        导出为与 HITS baseline token_stats.json 完全相同的结构：

        {
          "generator": {
            "prompt_tokens": ..., "completion_tokens": ..., "total_tokens": ...,
            "llm_elapsed_seconds": ..., "call_count": ...
          },
          "refiner": { ... },
          "all_total": {
            "prompt_tokens": ..., "completion_tokens": ..., "total_tokens": ...,
            "llm_elapsed_seconds": ...
          },
          "rounds": {
            "phase1":   { "generator": {...}, "refiner": {...}, "round_total_tokens": ... },
            "round_1":  { "generator": {...}, "refiner": {...}, "round_total_tokens": ... },
            ...
          }
        }

        注意：
          - llm_elapsed_seconds 是纯 LLM API 调用时间，不含 TestRunner/相似度等工具链耗时
          - 这与 HITS LLMStatsTracker 的统计口径完全一致
        """
        # 所有已出现的 phase
        phases = sorted(set(r.phase for r in self._records),
                        key=lambda p: (0 if p == "phase1" else int(p.split("_")[1])))

        def _role_summary(role: str, phase: Optional[str] = None) -> dict:
            return {
                "prompt_tokens":      self.prompt_tokens(role, phase),
                "completion_tokens":  self.completion_tokens(role, phase),
                "total_tokens":       self.total_tokens(role, phase),
                "llm_elapsed_seconds": round(self.elapsed_seconds(role, phase), 3),
                "call_count":         self.call_count(role, phase),
            }

        rounds: Dict[str, dict] = {}
        for ph in phases:
            gen_s = _role_summary("generator", ph)
            ref_s = _role_summary("refiner",   ph)
            rounds[ph] = {
                "generator":          gen_s,
                "refiner":            ref_s,
                "round_total_tokens": gen_s["total_tokens"] + ref_s["total_tokens"],
                "round_llm_elapsed_seconds": round(
                    gen_s["llm_elapsed_seconds"] + ref_s["llm_elapsed_seconds"], 3),
            }

        gen_all = _role_summary("generator")
        ref_all = _role_summary("refiner")

        return {
            "generator": gen_all,
            "refiner":   ref_all,
            "all_total": {
                "prompt_tokens":       gen_all["prompt_tokens"]      + ref_all["prompt_tokens"],
                "completion_tokens":   gen_all["completion_tokens"]  + ref_all["completion_tokens"],
                "total_tokens":        gen_all["total_tokens"]        + ref_all["total_tokens"],
                "llm_elapsed_seconds": round(
                    gen_all["llm_elapsed_seconds"] + ref_all["llm_elapsed_seconds"], 3),
            },
            "rounds": rounds,
        }

    def reset(self) -> None:
        self._records.clear()