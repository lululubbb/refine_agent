#!/usr/bin/env python3
"""Run bug_revealing.py across defects4j-like projects and collect summaries.

支持两种工作流（自动检测）：
  1. Fixed-first（新默认）: project_dir 指向 _f 版本
     - 测试文件在 _f 目录下的 tests%* 中（因为在 fixed 版本上生成）
     - bug_revealing: --buggy _b --fixed _f --tests <_f 的 tests 目录>
  2. Buggy-first（旧版兼容）: project_dir 指向 _b 版本
     - 测试文件在 _b 目录下的 tests%* 中（原有行为）
     - bug_revealing: --buggy _b --fixed _f --tests <_b 的 tests 目录>

用法:
  python3 run_bug_revealing.py [project_paths...]

  # Fixed-first（在 _f 目录下找测试）
  python3 run_bug_revealing.py /path/to/defect4j_projects/Csv_1_f

  # Buggy-first（在 _b 目录下找测试，兼容旧版）
  python3 run_bug_revealing.py /path/to/defect4j_projects/Csv_1_b

  # 传入根目录，自动展开所有子项目（自动检测每个子项目的模式）
  python3 run_bug_revealing.py /path/to/defect4j_projects
"""

import os
import sys
import glob
import argparse
import subprocess
from config import project_dir

PY = sys.executable
HERE = os.path.dirname(os.path.abspath(__file__))
BUG_REVEALING = os.path.join(HERE, 'scripts', 'bug_revealing.py')

if not os.path.exists(BUG_REVEALING):
    BUG_REVEALING = os.path.join(os.path.dirname(HERE), 'src', 'scripts', 'bug_revealing.py')


def extract_project_number(project_path):
    """提取项目路径中的数字，用于自然排序"""
    basename = os.path.basename(project_path)
    import re
    m = re.search(r'(\d+)', basename)
    try:
        return int(m.group(1)) if m else 9999
    except ValueError:
        return 9999


def find_projects(targets=None):
    """
    解析传入路径，返回项目列表。
    每个元素是一个目录路径，可能以 _f 或 _b 结尾。
    """
    projects = []
    if targets and len(targets) > 0:
        seen = []
        for p in targets:
            ap = os.path.abspath(p)
            if not os.path.exists(ap):
                print(f"Warning: provided project path does not exist: {p}")
                continue

            base = os.path.basename(ap)

            # 情况1：传入的是单个 _f 或 _b 项目目录
            if (base.endswith('_f') or base.endswith('_b')) and os.path.isdir(ap):
                seen.append(ap)
                continue

            # 情况2：传入的是根目录，展开其下所有 Csv*_*_f 和 Csv*_*_b 子目录
            # 优先找 _f（fixed-first 模式），如果没有 _f 才找 _b
            children_f = sorted(glob.glob(os.path.join(ap, 'Csv*_*_f')))
            children_b = sorted(glob.glob(os.path.join(ap, 'Csv*_*_b')))

            if children_f:
                # fixed-first: 有 _f 目录就用 _f
                for c in children_f:
                    seen.append(os.path.abspath(c))
                continue
            elif children_b:
                # 兼容 buggy-first：只有 _b 时用 _b
                for c in children_b:
                    seen.append(os.path.abspath(c))
                continue

            print(f"Warning: provided path did not resolve to projects: {p}")

        # 去重并按数字排序
        projects = []
        for s in seen:
            if s not in projects:
                projects.append(s)
        projects = sorted(projects, key=extract_project_number)
        return projects

    # 没有传入参数时，从 config 的 project_dir 自动发现
    root = os.path.abspath(project_dir)
    if not os.path.isdir(root):
        print(f"project_dir from config not found: {root}")
        return []

    # 优先找 _f，其次找 _b
    candidates_f = glob.glob(os.path.join(root, 'Csv*_*_f'))
    candidates_b = glob.glob(os.path.join(root, 'Csv*_*_b'))

    if candidates_f:
        for p in sorted(candidates_f, key=extract_project_number):
            projects.append(os.path.abspath(p))
    elif candidates_b:
        for p in sorted(candidates_b, key=extract_project_number):
            projects.append(os.path.abspath(p))

    return projects


def find_newest_tests(project_root):
    """在给定项目目录下找最新的 tests%* 目录"""
    candidates = sorted(glob.glob(os.path.join(project_root, 'tests%*')))
    if not candidates:
        return None
    return os.path.abspath(candidates[-1])


def resolve_buggy_fixed(proj_path):
    """
    根据传入的项目路径，推导出 buggy_proj、fixed_proj 和 tests_source_proj。

    Fixed-first 模式（proj_path 以 _f 结尾）：
      - fixed_proj  = proj_path          (_f)
      - buggy_proj  = sibling _b 目录
      - tests_source_proj = fixed_proj   (测试在 _f 下生成)

    Buggy-first 模式（proj_path 以 _b 结尾，兼容旧版）：
      - buggy_proj  = proj_path          (_b)
      - fixed_proj  = sibling _f 目录
      - tests_source_proj = buggy_proj   (测试在 _b 下生成)

    返回: (buggy_proj, fixed_proj, tests_source_proj) 或 None（找不到 sibling 时）
    """
    proj_path = os.path.abspath(proj_path)
    project_name = os.path.basename(proj_path)
    parent_dir = os.path.dirname(proj_path)

    if project_name.endswith('_f'):
        # Fixed-first 模式
        fixed_proj = proj_path
        buggy_name = project_name[:-2] + '_b'
        buggy_proj = os.path.join(parent_dir, buggy_name)
        if not os.path.isdir(buggy_proj):
            print(f"Buggy project not found for {project_name}, expected: {buggy_proj}")
            return None
        tests_source_proj = fixed_proj
        mode = "fixed-first"

    elif project_name.endswith('_b'):
        # Buggy-first 模式（兼容旧版）
        buggy_proj = proj_path
        fixed_name = project_name[:-2] + '_f'
        fixed_proj = os.path.join(parent_dir, fixed_name)
        if not os.path.isdir(fixed_proj):
            print(f"Fixed project not found for {project_name}, expected: {fixed_proj}")
            return None
        tests_source_proj = buggy_proj
        mode = "buggy-first (legacy)"

    else:
        print(f"Cannot determine mode for project: {project_name} (no _f/_b suffix)")
        return None

    print(f"  Mode: {mode}")
    print(f"  buggy_proj:        {buggy_proj}")
    print(f"  fixed_proj:        {fixed_proj}")
    print(f"  tests_source_proj: {tests_source_proj}")
    return buggy_proj, fixed_proj, tests_source_proj


def run_for_project(proj_path):
    """
    对单个项目运行 bug_revealing.py。
    proj_path 可以是 _f 或 _b 结尾的目录。
    """
    project_name = os.path.basename(os.path.abspath(proj_path))

    result = resolve_buggy_fixed(proj_path)
    if result is None:
        return
    buggy_proj, fixed_proj, tests_source_proj = result

    # 从 tests_source_proj 目录找测试文件
    tests_dir = find_newest_tests(tests_source_proj)
    if not tests_dir:
        print(f"No tests%* directory found under {tests_source_proj}, skipping")
        return

    # 构造 bug_revealing.py 调用命令
    # 注意：--buggy 永远是 _b，--fixed 永远是 _f
    # --tests 指向测试文件所在的目录（fixed-first 时在 _f 下，buggy-first 时在 _b 下）
    cmd = [
        PY, BUG_REVEALING,
        '--buggy', buggy_proj,
        '--fixed', fixed_proj,
        '--tests', tests_dir,
    ]
    print(f"Running bug_revealing for {project_name} using tests dir: {tests_dir}")
    print(f"  cmd: {' '.join(cmd)}")
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print(proc.stdout)
        if proc.returncode != 0:
            print(f"bug_revealing failed for {project_name}, rc={proc.returncode}")
            print(proc.stderr)
        else:
            print(f"Completed {project_name}, results in {tests_dir}")
    except Exception as e:
        print(f"Error running bug_revealing for {project_name}: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='Run bug_revealing across projects (supports both _f and _b as project_dir)'
    )
    parser.add_argument(
        'projects', nargs='*',
        help=(
            'Optional project paths. '
            'Can be _f (fixed-first, new default) or _b (buggy-first, legacy). '
            'If empty, uses config.project_dir discovery.'
        )
    )
    args = parser.parse_args()

    projects = find_projects(args.projects if args.projects else None)
    if not projects:
        print('No projects found to run')
        return
    print(f"Found {len(projects)} projects to process.")
    for p in projects:
        print(f"\n{'='*60}")
        print(f"Processing: {os.path.basename(p)}")
        print(f"{'='*60}")
        run_for_project(p)


if __name__ == '__main__':
    main()