"""
run.py
======
一键运行入口（与 ChatUniTest run.py 结构完全相同）：
  Step 1: Task.parse(project_dir)          → class_info/ JSON
  Step 2: parse_data(class_info 路径)       → MySQL
  Step 3: export_data()                     → dataset_batch/ JSON
  Step 4: scope_test_refine.start_generation → results_batch/ 生成 + 迭代
  Step 5: Task.all_test                     → 最终测试执行

唯一改动：导入 scope_test_refine 而非 scope_test
"""
import json
import os
import shutil
import sys
import time

# ── sys.path 配置（在 src/ 目录下运行）──────────────────────────────
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from tools import dataset_dir, result_dir, project_dir
from database import drop_table, create_table
from parse_data import parse_data
from export_data import export_data
from scope_test_refine import start_generation
from task import Task


# ── 断点续跑进度管理 ──────────────────────────────────────────────────

def _progress_file() -> str:
    project_name = os.path.basename(os.path.normpath(project_dir))
    return os.path.join(result_dir, project_name, "progress.json")


def _load_progress() -> dict:
    path = _progress_file()
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}


def _save_progress(step: str, status: str):
    path = _progress_file()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    progress = _load_progress()
    progress[step] = status
    with open(path, "w") as f:
        json.dump(progress, f, indent=2)


# ─────────────────────────────────────────────────────────────────────

def run(
    sql_query: str = None,
    multiprocess: bool = True,
    skip_parse: bool = False,
    skip_export: bool = False,
    confirmed: bool = True,
):
    """
    完整 pipeline 入口。

    Parameters
    ----------
    sql_query   : 筛选 focal method 的 SQL（如 None，则处理全部）
    multiprocess: 是否开启多进程
    skip_parse  : 跳过 parse + export 步骤（已有 dataset 时使用）
    skip_export : 跳过 export 步骤
    confirmed   : 无需交互确认
    """
    progress = _load_progress()

    # ── Step 1: 重置数据库 ────────────────────────────────────────────
    if not skip_parse:
        print("\n📌 Step 1: 重置数据库...")
        drop_table()
        create_table()

    # ── Step 2: 解析项目 ──────────────────────────────────────────────
    if not skip_parse and progress.get("parse") != "success":
        print("📌 Step 2: 解析项目 →", project_dir)
        info_path = Task.parse(project_dir)
        parse_data(info_path)
        _save_progress("parse", "success")
        print("✅ 解析完成")
    else:
        print("⏭  解析步骤已完成或跳过")

    # ── Step 3: 导出数据集 JSON ────────────────────────────────────────
    if not skip_parse and not skip_export and progress.get("export") != "success":
        print("📌 Step 3: 导出数据集 →", dataset_dir)
        export_data()
        _save_progress("export", "success")
        print("✅ 导出完成")
    else:
        print("⏭  导出步骤已完成或跳过")

    # ── Step 4: 生成 + Refine 迭代 ────────────────────────────────────
    print("📌 Step 4: 启动 RefineTestGen pipeline...")
    if sql_query is None:
        project_name = os.path.basename(os.path.normpath(project_dir))
        sql_query = f"SELECT id FROM method WHERE project_name='{project_name}' AND is_constructor=0 AND is_get_set=0;"
    start_generation(sql_query, multiprocess=multiprocess, confirmed=confirmed)

    print("\n✅ 全流程完成！")


if __name__ == "__main__":
    # 示例：测试 Csv_1_b 项目的 Token 类
    run(
        sql_query="SELECT id FROM method WHERE project_name='Csv_1_b' AND class_name='Token' AND is_constructor=0;",
        multiprocess=False,
        confirmed=True,
    )
