import os
import re
import glob
import argparse
from task import Task
# from parse_xml import result_analysis
from config import *
import subprocess
import sys
from tools import *

def run_tests(target_projects=None, all_versions=False):
    """
    执行生成的测试用例，生成覆盖率报告
    :param target_projects: 目标项目路径列表
    :param all_versions: 是否对目录下所有的 tests%* 文件夹进行评估，若为 False 则仅评估最新的
    """
    def project_key(path):
        name = os.path.basename(path)
        m = __import__('re').search(r"(\d+)", name)
        if m:
            return int(m.group(1))
        try:
            return int(name)
        except Exception:
            return 10 ** 9

    # --- 1. 项目识别逻辑 (保持不变) ---
    if target_projects is not None and len(target_projects) > 0:
        projects = []
        for proj in target_projects:
            abs_proj = os.path.abspath(proj)
            if not os.path.exists(abs_proj):
                print(f"⚠️ 传入的路径不存在，跳过：{proj}")
                continue
            tests_dirs = sorted(glob.glob(os.path.join(abs_proj, 'tests%*')))
            if tests_dirs:
                projects.append(abs_proj)
                continue
            children = sorted(glob.glob(os.path.join(abs_proj, 'Csv*_*_f')))
            if not children:
                children = sorted(glob.glob(os.path.join(abs_proj, 'Csv*_*_b')))
            if children:
                projects.extend([os.path.abspath(c) for c in children])
                continue
            if os.path.exists(os.path.join(abs_proj, 'pom.xml')):
                projects.append(abs_proj)
                continue
        projects = sorted(list(dict.fromkeys(projects)), key=project_key)
    else:
        projects_set = set()
        for p in glob.glob(os.path.join(project_dir, 'Csv*_*_f')):
            projects_set.add(os.path.abspath(p))
        if not projects_set:
            for p in glob.glob(os.path.join(project_dir, 'Csv*_*_b')):
                projects_set.add(os.path.abspath(p))
        for entry in glob.glob(os.path.join(project_dir, '*')):
            if os.path.isdir(entry) and glob.glob(os.path.join(entry, 'tests%*')):
                projects_set.add(os.path.abspath(entry))
        projects = sorted(list(projects_set), key=project_key)

    if not projects:
        print("❌ 未找到有效项目。")
        return

    print(f"📌 开始执行测试评估 (模式: {'所有版本' if all_versions else '仅最新版本'})...")

    # --- 2. 遍历项目执行测试 ---
    for proj in projects:
        proj = os.path.abspath(proj)
        project_name = os.path.basename(proj)
        
        candidate_tests = glob.glob(os.path.join(proj, 'tests%*'))
        if not candidate_tests:
            print(f"⚠️ 项目 {project_name} 无 tests%* 目录，跳过。")
            continue

        # 排序：按时间戳（目录名中的数字）升序
        def tests_dir_key(path):
            m = re.search(r"(\d+)", os.path.basename(path))
            return int(m.group(1)) if m else 0
        
        candidate_tests.sort(key=tests_dir_key)

        # 根据参数决定是处理全部还是只处理最后一个
        tests_to_process = candidate_tests if all_versions else [candidate_tests[-1]]

        for result_path in tests_to_process:
            result_path = os.path.abspath(result_path)
            tests_dirname = os.path.basename(result_path)
            print(f"🔍 处理项目: {project_name} -> 目录: {tests_dirname}")

            try:
                # 核心测试任务
                Task.all_test(result_path, proj)
                print(f"✅ [{tests_dirname}] 测试执行完成")

                # 运行 bug_revealing
                try:
                    rb = [sys.executable, os.path.join(os.path.dirname(__file__), 'run_bug_revealing.py'), proj]
                    subprocess.run(rb, check=False)
                except Exception as _e:
                    print(f"⚠️ bug_revealing 失败: {_e}")

                # 运行代码分析
                try:
                    if os.path.isdir(result_path):
                        scripts_dir = os.path.join(os.path.dirname(__file__), 'scripts')
                        subprocess.run([sys.executable, os.path.join(scripts_dir, 'code_to_ast.py'), result_path], check=False)
                        subprocess.run([sys.executable, os.path.join(scripts_dir, 'measure_similarity.py'), result_path], check=False)
                except Exception as _e:
                    print(f"⚠️ similarity 分析失败: {_e}")

                # 写入 Summary 统计
                try:
                    token_results = collect_token_results_from_result_path(result_path)
                    if token_results:
                        write_llm_summary(token_results, result_path)
                        print(f"[Summary] 已写入: {result_path}")
                except Exception as _e:
                    print(f"[Summary] 写入失败: {_e}")

            except Exception as e:
                print(f"❌ 项目 {project_name} 在处理 {tests_dirname} 时出错: {e}")

    print("✅ 所有指定任务执行完成")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="执行 Java 项目测试用例，生成覆盖率报告")
    parser.add_argument('projects', nargs='*', help="目标项目路径")
    # 新增参数：--all 或 -a
    parser.add_argument('--all', '-a', action='store_true', help="评估所有找到的 tests% 目录，而不只是最新的")
    
    args = parser.parse_args()
    
    run_tests(
        target_projects=args.projects if args.projects else None,
        all_versions=args.all  # 将参数传递给函数
    )