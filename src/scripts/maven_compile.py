import subprocess
import os
import glob
import argparse
import shutil

def check_compiled(project_path, core_module=None):
    """
    检查项目是否已编译（存在target目录）
    :param project_path: 项目根目录
    :param core_module: 核心子模块名（如Gson的"gson"）
    :return: 是否已编译
    """
    if core_module:
        target_path = os.path.join(project_path, core_module, "target")
    else:
        target_path = os.path.join(project_path, "target")
    return os.path.exists(target_path)

def maven_compile(project_path, core_module=None):
    """
    执行mvn compile指令
    :param project_path: 项目根目录
    :param core_module: 核心子模块名（如Gson的"gson"）
    :return: (编译是否成功, 错误日志)
    """
    # 定位pom.xml和编译工作目录
    if core_module:
        pom_path = os.path.join(project_path, core_module, "pom.xml")
        compile_cwd = os.path.join(project_path, core_module)
    else:
        pom_path = os.path.join(project_path, "pom.xml")
        compile_cwd = project_path

    if not os.path.exists(pom_path):
        return False, f"pom.xml不存在：{pom_path}"

    # 构建mvn compile命令
    cmd = [
        "mvn", "compile",
        "-Dmaven.compiler.source=11",
        "-Dmaven.compiler.target=11",
        "-Dmaven.repo.local=~/.m2/repository",
        "-Dmaven.compiler.plugin.version=3.8.1",
        "-Dmaven.bundle.skip=true",
        "-q",  # 静默模式，减少输出
        "-f", pom_path
    ]

    # 执行编译命令
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=compile_cwd
    )

    success = (result.returncode == 0)
    error_log = result.stderr.strip() if not success else ""
    return success, error_log

def batch_compile(root_dir, project_prefixes):
    """
    批量编译指定前缀的项目
    :param root_dir: 根目录（如/home/chenlu/ChatUniTest_GPT3.5/defect4j_projects）
    :param project_prefixes: 项目前缀列表（如["Csv", "Gson"]）
    """
    # 初始化统计信息
    stats = {
        "total": 0,
        "skipped": 0,
        "success": 0,
        "failed": 0,
        "failed_projects": []
    }

    # 1. 遍历所有指定前缀的项目目录（匹配*_b/*_f后缀）
    all_projects = []
    for prefix in project_prefixes:
        pattern = os.path.join(root_dir, f"{prefix}_*_[bf]")
        all_projects.extend(glob.glob(pattern))

    if not all_projects:
        print(f"⚠️ 在{root_dir}下未找到前缀为{project_prefixes}的项目（*_b/*_f）")
        return

    # 2. 逐个处理项目
    print(f"🚀 开始批量编译{len(all_projects)}个项目（前缀：{project_prefixes}）...\n")
    for project_path in sorted(all_projects):
        stats["total"] += 1
        project_name = os.path.basename(project_path)
        
        # 判断项目类型，确定核心子模块
        core_module = "gson" if project_name.startswith("Gson") else None

        # 检查是否已编译，跳过
        if check_compiled(project_path, core_module):
            print(f"⏭️ {project_name}：已存在target目录，跳过编译")
            stats["skipped"] += 1
            continue

        # 执行编译
        print(f"🔧 正在编译：{project_name}")
        success, error = maven_compile(project_path, core_module)

        # 统计结果
        if success:
            print(f"✅ {project_name} 编译成功\n")
            stats["success"] += 1
        else:
            print(f"❌ {project_name} 编译失败：{error[:500]}...\n")
            stats["failed"] += 1
            stats["failed_projects"].append((project_name, error))

    # 3. 输出编译报告
    print("="*60)
    print("📊 批量编译报告")
    print("="*60)
    print(f"总项目数：{stats['total']}")
    print(f"⏭️ 已编译跳过：{stats['skipped']}")
    print(f"✅ 编译成功：{stats['success']}")
    print(f"❌ 编译失败：{stats['failed']}")

    if stats["failed_projects"]:
        print("\n❌ 失败项目详情：")
        for proj_name, error in stats["failed_projects"]:
            print(f"- {proj_name}：{error[:300]}...")

if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="批量编译Defects4J项目（支持跳过已编译项目）")
    parser.add_argument("--root", 
                        default="/home/chenlu/ChatUniTest_GPT3.5/defect4j_projects",
                        help="Defects4J项目根目录（默认：/home/chenlu/ChatUniTest/defect4j_projects）")
    parser.add_argument("--prefixes", 
                        nargs="+", 
                        default=["Csv"],
                        help="要编译的项目前缀（如--prefixes Csv Gson，默认：Csv Gson）")
    
    args = parser.parse_args()

    # 执行批量编译
    batch_compile(args.root, args.prefixes)