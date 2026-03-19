"""
scope_test_refine.py
====================
替换 ChatUniTest 的 scope_test.py。
接口与 scope_test.py 完全相同，唯一区别是：
  - 调用 askGPT_refine.start_whole_process（Suite 级 Refine pipeline）
  - 不再调用 askGPT.start_whole_process（单个 Test fix）

目录结构（与 ChatUniTest 完全一致）：
  results_batch/<proj>/scope_test%YYYYMMDDHHMMSS%/
    record.txt
    global_stats.json
    1%Csv_1_b%Token%reset%d3/    ← 每个 focal method
      test_cases/                ← ★ 最终 .java（TestRunner 读取此处）
        Token_1_1Test.java
      1/                         ← test_num=1 的迭代记录
        1_GEN_0.json
        2_SUITE_0.java
        3_tool_diag_1.json
        4_REFINE_1.json
        5_GEN_1.json
        6_SUITE_1.java
        time_stats.json
        token_stats.json
"""
import datetime
import os
import re
import sys

from colorama import Fore, Style, init

# ── sys.path ────────────────────────────────────────────────────────
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from tools import (
    result_dir, project_dir, dataset_dir,
    remove_single_test_output_dirs, get_project_abspath,
    find_result_in_projects,
)
from askGPT_refine import start_whole_process
from database import database
from task import Task

init()
db = database()


def create_result_folder() -> str:
    """
    在 result_dir 下创建 scope_test%YYYYMMDDHHMMSS% 目录。
    与 ChatUniTest create_dataset_result_folder 逻辑相同。
    """
    now      = datetime.datetime.now()
    time_str = now.strftime("%Y%m%d%H%M%S")
    path     = os.path.join(result_dir, f"scope_test%{time_str}%")
    os.makedirs(path, exist_ok=True)
    return path


def start_generation(
    sql_query: str,
    multiprocess: bool = False,
    confirmed: bool = True,
):
    """
    与 ChatUniTest scope_test.start_generation 接口完全相同。
    替换内部的 start_whole_process 调用为 askGPT_refine 版本。

    Parameters
    ----------
    sql_query   : 筛选 focal method 的 SQL，e.g.
                  "SELECT id FROM method WHERE project_name='Csv_1_b';"
    multiprocess: 多进程开关
    confirmed   : False 时需要终端确认
    """
    # ── 从 SQL 提取项目名（一次只处理一个项目）─────────────────────
    match = re.search(r"project_name\s*=\s*'([\w\-]*)'", sql_query)
    if not match:
        raise RuntimeError(
            "SQL must contain project_name='...' filter (one project at a time)."
        )
    project_name = match.group(1)
    print(Fore.CYAN + f"Project: {project_name}" + Style.RESET_ALL)

    # ── 清理上轮遗留的单测输出目录 ──────────────────────────────────
    remove_single_test_output_dirs(get_project_abspath())

    # ── 查询需要处理的 focal method ids ─────────────────────────────
    method_ids = [str(x[0]) for x in db.select(script=sql_query)]
    if not method_ids:
        raise Exception(f"No methods found for query: {sql_query}")
    print(Fore.CYAN + f"Found {len(method_ids)} focal methods: {method_ids[:10]}..." + Style.RESET_ALL)

    # ── 确认 ──────────────────────────────────────────────────────────
    if not confirmed:
        ans = input("Start RefineTestGen? (y/n): ")
        if ans.lower() != "y":
            print("Cancelled.")
            return

    # ── 创建结果目录 ──────────────────────────────────────────────────
    result_path = create_result_folder()
    print(Fore.GREEN + f"Result dir: {result_path}" + Style.RESET_ALL)

    # 写 record.txt（与 ChatUniTest 一致）
    record = (
        "RefineTestGen scope test record\n"
        f"Result path: {result_path}\n"
        f'SQL: "{sql_query}"\n'
        f"Methods ({len(method_ids)}): {method_ids}\n"
    )
    with open(os.path.join(result_path, "record.txt"), "w") as f:
        f.write(record)

    # ── ★ 核心：Suite 级 Refine pipeline ─────────────────────────────
    # source_dir 是 dataset_batch/<proj>/direction_1/（与 ChatUniTest 相同）
    source_dir = os.path.join(dataset_dir, "direction_1")
    start_whole_process(
        source_dir=source_dir,
        result_path=result_path,
        method_ids=method_ids,
        multiprocess=multiprocess,
    )
    print(Fore.GREEN + "GENERATION FINISHED" + Style.RESET_ALL)

    # ── 运行最终测试（与 ChatUniTest 相同） ───────────────────────────
    project_path = os.path.abspath(project_dir)
    print(Fore.CYAN + "START ALL TESTS..." + Style.RESET_ALL)
    Task.all_test(result_path, project_path)

    print(Fore.GREEN + "SCOPE TEST FINISHED" + Style.RESET_ALL)


if __name__ == "__main__":
    # 示例
    start_generation(
        sql_query="SELECT id FROM method WHERE project_name='Csv_1_b' AND is_constructor=0;",
        multiprocess=False,
        confirmed=True,
    )
