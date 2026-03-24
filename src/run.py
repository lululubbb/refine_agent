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
import re
import shutil
import subprocess
import sys
import time
import glob
# ── sys.path 配置（在 src/ 目录下运行）──────────────────────────────
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from tools import dataset_dir, result_dir, project_dir, find_result_in_projects
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
        sql_query = f"SELECT id FROM method WHERE project_name='{project_name}' ;"
    start_generation(sql_query, multiprocess=multiprocess, confirmed=confirmed)

    # ── Step 5: 数据后处理（bug_revealing + similarity）──────────────────
    # 生成后：自动运行 bug_revealing 与 similarity（针对当前 project）
    try:
        # project_dir 在 config.py 中定义，指向当前处理的 defects4j 单个项目（可能带 _b 后缀）
        proj = os.path.abspath(project_dir)
        # 找到该项目下最新的 tests%* 目录（如果存在）
        tests_dirs = sorted(glob.glob(os.path.join(proj, 'tests%*')))
        tests_dir = tests_dirs[-1] if tests_dirs else None

        # 1) 运行 bug_revealing（使用 src/run_bug_revealing.py，传入项目路径以批量处理）
        rb = [sys.executable, os.path.join(os.path.dirname(__file__), 'run_bug_revealing.py'), proj]
        print(f"📌 运行 bug_revealing: {' '.join(rb)}")
        subprocess.run(rb, check=False)

        # 2) 运行 code_to_ast + measure_similarity（对最新 tests_dir）
        if tests_dir and os.path.isdir(tests_dir):
            code_to_ast = [sys.executable, os.path.join(os.path.dirname(__file__), 'scripts', 'code_to_ast.py'), tests_dir]
            print(f"📌 运行 code_to_ast: {' '.join(code_to_ast)}")
            subprocess.run(code_to_ast, check=False)

            measure_sim = [sys.executable, os.path.join(os.path.dirname(__file__), 'scripts', 'measure_similarity.py'), tests_dir]
            print(f"📌 运行 measure_similarity: {' '.join(measure_sim)}")
            subprocess.run(measure_sim, check=False)
        else:
            print(f"⚠️ 未找到 tests 目录，跳过 similarity 计算: {proj}")
    except Exception as e:
        print(f"⚠️ 自动运行 bug_revealing/similarity 失败: {e}")

    print("\n✅ 全流程完成！")


if __name__ == "__main__":
    print("Make sure the config.ini is correctly configured.")
    seconds = 1
    while seconds > 0:
        print(seconds)
        time.sleep(1)  # Pause for 1 second
        seconds -= 1
    run()