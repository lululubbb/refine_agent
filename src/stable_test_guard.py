"""
stable_test_guard.py

"""
from __future__ import annotations

import copy
import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Dict, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class TestStability:
    """记录单个test文件的稳定性状态。"""
    test_name: str
    is_compile_stable: bool = False  # 当前轮compile pass
    is_exec_stable: bool = False     # 当前轮exec pass
    stable_since_round: int = 0      # 从第几轮开始稳定
    test_method_names: Set[str] = field(default_factory=set)  # 稳定时的@Test方法名集合
    source_snapshot: str = ""        # 稳定时的源码快照（用于回滚）

    @property
    def is_stable(self) -> bool:
        return self.is_compile_stable and self.is_exec_stable

    @property
    def needs_enhancement_only(self) -> bool:
        """稳定的test只需要增强，不需要结构性修改。"""
        return self.is_stable


class StableTestGuard:
    """
    跨轮次追踪test稳定性，保护稳定test不被退步。

    在 focal_method_pipeline 中实例化，跨所有round共享。
    """

    def __init__(self):
        self._stability: Dict[str, TestStability] = {}

    def update_after_round(
        self,
        round_num: int,
        test_diags: dict,
        current_codes: Dict[str, str],
    ):
        """
        每轮 RefineAgent 运行完后更新稳定性状态。
        """
        for tc_name, diag in test_diags.items():
            if tc_name not in self._stability:
                self._stability[tc_name] = TestStability(test_name=tc_name)

            st = self._stability[tc_name]
            compile_ok = getattr(diag, 'compile_ok', False)
            exec_ok    = getattr(diag, 'exec_ok', False)

            was_stable = st.is_stable

            st.is_compile_stable = compile_ok
            st.is_exec_stable    = exec_ok

            if st.is_stable and not was_stable:
                # 刚变稳定：记录快照
                st.stable_since_round = round_num
                if tc_name in current_codes:
                    st.source_snapshot = current_codes[tc_name]
                    st.test_method_names = _extract_test_method_names(current_codes[tc_name])
                logger.info(
                    "[StableGuard] %s became STABLE at round %d (%d @Test methods)",
                    tc_name, round_num, len(st.test_method_names)
                )
            elif st.is_stable and was_stable:
                # 保持稳定：更新快照到最新
                if tc_name in current_codes:
                    st.source_snapshot = current_codes[tc_name]
                    st.test_method_names = _extract_test_method_names(current_codes[tc_name])

    def guard_after_fix(
        self,
        tc_name: str,
        new_code: str,
        tc_dir: str,
    ) -> Tuple[str, bool]:
        """
        fix完成后，检查稳定test是否被退步（@Test方法被减少或删除）。

        返回 (最终代码, 是否发生了回滚)
        """
        st = self._stability.get(tc_name)
        if st is None or not st.is_stable or not st.source_snapshot:
            return new_code, False

        new_method_names = _extract_test_method_names(new_code)
        lost_methods = st.test_method_names - new_method_names

        if lost_methods:
            logger.warning(
                "[StableGuard] %s ROLLBACK: lost @Test methods %s after fix, reverting",
                tc_name, lost_methods
            )
            # 回滚到稳定快照
            tc_path = os.path.join(tc_dir, f"{tc_name}.java")
            with open(tc_path, "w", encoding="utf-8") as f:
                f.write(st.source_snapshot)
            return st.source_snapshot, True

        return new_code, False

    def get_stability(self, tc_name: str) -> Optional[TestStability]:
        return self._stability.get(tc_name)

    def get_stable_tests(self) -> Set[str]:
        return {n for n, s in self._stability.items() if s.is_stable}

    def get_unstable_tests(self) -> Set[str]:
        return {n for n, s in self._stability.items() if not s.is_stable}

    def summary(self) -> str:
        stable = self.get_stable_tests()
        unstable = self.get_unstable_tests()
        return f"stable={len(stable)} unstable={len(unstable)} total={len(self._stability)}"


def _extract_test_method_names(java_source: str) -> Set[str]:
    """提取Java源码中所有@Test方法名。"""
    names = set()
    lines = java_source.splitlines()
    for i, line in enumerate(lines):
        if '@Test' in line or '@org.junit.Test' in line or '@org.junit.jupiter.api.Test' in line:
            # 向后找方法声明
            for j in range(i + 1, min(i + 5, len(lines))):
                m = re.search(r'\bvoid\s+(\w+)\s*\(', lines[j])
                if m:
                    names.add(m.group(1))
                    break
    return names