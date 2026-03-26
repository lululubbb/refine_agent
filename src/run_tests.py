import os
import re
import glob
import argparse
from task import Task
from parse_xml import result_analysis
from config import *
import subprocess
import sys
from tools import *
# 使用示例：python3 run_tests.py /home/chenlu/ChatUniTest/defect4j_projects

def run_tests(target_projects=None):
    """
    执行生成的所有测试用例，生成覆盖率报告
    """
    # 从result_dir中找到最新的测试结果目录
    # 该目录应该是在run.py执行完成后生成的
    # 自动获取最新生成结果目录
    # 遍历 project_dir 下的所有缺陷版本项目（如 Csv*_?_b），对每个项目找到最新的 tests%* 目录并执行
    def project_key(path):
        name = os.path.basename(path)
        # 提取第一个整数作为排序键，找不到则返回大数保证放后面
        m = (re_search := __import__('re').search(r"(\d+)", name))
        if m:
            return int(m.group(1))
        try:
            return int(name)
        except Exception:
            return 10 ** 9

    if target_projects is not None and len(target_projects) > 0:
        # 外部传入的项目路径，转换为绝对路径并验证有效性
        projects = []
        for proj in target_projects:
            abs_proj = os.path.abspath(proj)
            if not os.path.exists(abs_proj):
                print(f"⚠️  传入的路径不存在，跳过：{proj}")
                continue
            # 情况1：传入的是一个单项目目录，且该目录下直接有 tests%* 目录（例如 /home/chenlu/commons-csv）
            tests_dirs = sorted(glob.glob(os.path.join(abs_proj, 'tests%*')))
            if tests_dirs:
                projects.append(abs_proj)
                continue
            # 情况2：传入的是 defects4j 根目录，展开包含多个 Csv*_*_b 子项目
            children = sorted(glob.glob(os.path.join(abs_proj, 'Csv_5_f')))
            if not children:
                children = sorted(glob.glob(os.path.join(abs_proj, 'Csv*_*_b')))
            if children:
                projects.extend([os.path.abspath(c) for c in children])
                continue
            # 情况3：传入的是单个项目目录但没有 tests（仍可能为 maven 项目），尝试接纳它
            if os.path.exists(os.path.join(abs_proj, 'pom.xml')):
                projects.append(abs_proj)
                continue
            print(f"⚠️  传入路径未识别为可执行项目或包含子项目，跳过：{abs_proj}")
        # 去重并按目录名中的数字排序（数值升序）
        projects = sorted(list(dict.fromkeys(projects)), key=project_key)
        if not projects:
            print("❌ 外部传入的项目路径均无效或不包含子项目，终止执行。")
            return
    else:
        # 默认从 config 中的 project_dir 自动发现项目：
        # - 包含 Csv*_*_b 的目录（defects4j 风格）
        # - 或者直接包含 tests%* 的项目目录（单一项目）
        projects_set = set()
        for p in glob.glob(os.path.join(project_dir, 'Csv_5_f')):
            projects_set.add(os.path.abspath(p))
        if not projects_set:
            for p in glob.glob(os.path.join(project_dir, 'Csv*_*_b')):
                projects_set.add(os.path.abspath(p))
        # 还扫描 project_dir 下可能的直接项目（含 tests%*）
        for entry in glob.glob(os.path.join(project_dir, '*')):
            if os.path.isdir(entry):
                if glob.glob(os.path.join(entry, 'tests%*')):
                    projects_set.add(os.path.abspath(entry))
        projects = sorted(list(projects_set), key=project_key)
        if not projects:
            print(f"未在 {project_dir} 中找到匹配的项目目录 (Csv*_1_b 或 包含 tests%*)。")
            return

    print("📌 开始对所有项目执行测试用例...")
    for proj in projects:
        proj = os.path.abspath(proj)
        project_name = os.path.basename(proj)
        # 在项目目录下查找 tests%* 目录（测试结果目录）
        candidate_tests = glob.glob(os.path.join(proj, 'tests%*'))
        if not candidate_tests:
            print(f"⚠️ 项目 {project_name} 无 tests%* 目录，跳过。")
            continue
        # 选择最近的 tests 目录：按目录名中的第一个数字（时间戳）排序，若无法解析则作为最小值处理
        def tests_dir_key(path):
            name = os.path.basename(path)
            m = re.search(r"(\d+)", name)
            if m:
                try:
                    return int(m.group(1))
                except Exception:
                    return 0
            return 0

        candidate_tests.sort(key=tests_dir_key)
        result_path = os.path.abspath(candidate_tests[-1])

        print(f"🔍 项目: {project_name}，使用测试结果目录: {result_path}")
        try:
            Task.all_test(result_path, proj)
            print(f"✅ 项目 {project_name} 测试执行完成\n")

            # 运行 bug_revealing（针对该项目）
            try:
                rb = [sys.executable, os.path.join(os.path.dirname(__file__), 'run_bug_revealing.py'), proj]
                print(f"📌 运行 bug_revealing: {' '.join(rb)}")
                subprocess.run(rb, check=False)
            except Exception as _e:
                print(f"⚠️ bug_revealing 运行失败: {_e}")

            # 运行 code_to_ast + measure_similarity（针对该 tests 目录）
            try:
                if os.path.isdir(result_path):
                    code_to_ast = [sys.executable, os.path.join(os.path.dirname(__file__), 'scripts', 'code_to_ast.py'), result_path]
                    print(f"📌 运行 code_to_ast: {' '.join(code_to_ast)}")
                    subprocess.run(code_to_ast, check=False)

                    measure_sim = [sys.executable, os.path.join(os.path.dirname(__file__), 'scripts', 'measure_similarity.py'), result_path]
                    print(f"📌 运行 measure_similarity: {' '.join(measure_sim)}")
                    subprocess.run(measure_sim, check=False)
                else:
                    print(f"⚠️ 未找到 result tests 目录，跳过 similarity: {result_path}")
            except Exception as _e:
                print(f"⚠️ similarity 运行失败: {_e}")
        except Exception as e:
            print(f"❌ 项目 {project_name} 执行时出错: {e}")

        # ── 新增：Task.all_test() 完成后，找到刚创建的 tests%* 目录，写入 summary ──
        try:
            import glob as _glob, re as _re

            def _find_latest_tests_dir(base_dir):
                candidates = [
                    p for p in _glob.glob(os.path.join(base_dir, "tests%*"))
                    if os.path.isdir(p)
                ]
                if not candidates:
                    return None
                def _ts_key(p):
                    m = _re.search(r"(\d+)", os.path.basename(p))
                    return int(m.group(1)) if m else 0
                candidates.sort(key=_ts_key)
                return candidates[-1]

            summary_output_dir = _find_latest_tests_dir(proj)
            if summary_output_dir:
                # 从 results_batch 的 scope_test 目录遍历读取已有 time_stats.json
                token_results = collect_token_results_from_result_path(result_path)
                if token_results:
                    write_llm_summary(token_results, summary_output_dir)
                    print(f"[Summary] summary 文件已写入: {summary_output_dir}")
                else:
                    print(f"[Summary] 未找到 token 统计数据，跳过写入 summary")
            else:
                print(f"[Summary] 未找到 tests%* 目录，跳过写入 summary")
        except Exception as _e:
            import traceback
            print(f"[Summary] 写入 summary 失败: {_e}")
            traceback.print_exc()

    print("✅ 所有项目测试执行完成")

def get_latest_result_path():
    """获取results_batch中最新的测试结果目录"""
    if not os.path.exists(result_dir):
        raise Exception(f"结果目录不存在: {result_dir}")
    
    # 获取所有scope_test目录
    scope_tests = [d for d in os.listdir(result_dir) 
                   if d.startswith('scope_test%')]
    
    if not scope_tests:
        raise Exception("未找到生成的测试用例")
    
    # 返回最新的
    latest = sorted(scope_tests)[-1]
    return os.path.join(result_dir, latest)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="执行 Java 项目测试用例，生成覆盖率报告")
    # 添加项目路径参数（支持多个，可选）
    parser.add_argument('projects', nargs='*', help="目标项目路径（可传入多个，空格分隔，无则使用 config 配置）")
    
    # 解析命令行参数
    args = parser.parse_args()
    
    # 调用 run_tests
    run_tests(target_projects=args.projects if args.projects else None)