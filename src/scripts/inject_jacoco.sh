#!/bin/bash
set -euo pipefail

# ===================================== 配置项（可根据需求修改） =====================================
# 1. 总项目根目录（包含所有子项目文件夹，如csv_1_b）
DEFECT4J_PROJECTS_ROOT="/home/chenlu/refine_test_gen_v5/defect4j_projects"
# 2. 是否自动注入 Jacoco 插件（true=自动注入，false=仅检查不修改）
INJECT_JACOCO=true
# 3. Jacoco 插件版本（推荐使用稳定版，兼容大多数 Maven 项目）
JACOCO_VERSION="0.8.11"
# ==================================================================================================

# 函数：打印带颜色的日志（方便区分不同状态）
print_info() {
  echo -e "\033[34m[INFO] $1\033[0m"
}

print_success() {
  echo -e "\033[32m[SUCCESS] $1\033[0m"
}

print_warning() {
  echo -e "\033[33m[WARNING] $1\033[0m"
}

print_error() {
  echo -e "\033[31m[ERROR] $1\033[0m"
}

# 核心函数：处理单个 pom.xml 文件（注入 Jacoco 插件，保留原有核心逻辑）
process_single_pom() {
  local pom_path="$1"
  local project_dir=$(dirname "$pom_path")
  local project_name=$(basename "$project_dir")

  print_info "===================================== 处理项目：$project_name ====================================="

  # 步骤1：检查 pom.xml 是否存在（传入路径已验证，此处二次兜底）
  if [ ! -f "$pom_path" ]; then
    print_error "项目 $project_name 中未找到 pom.xml，路径：$pom_path"
    return 1
  fi

  # 步骤2：检查 Jacoco 插件是否已存在
  if grep -q "artifactId>jacoco-maven-plugin" "$pom_path" 2>/dev/null; then
    print_success "项目 $project_name 中 jacoco-maven-plugin 已存在，无需重复注入"
    return 0
  fi

  # 步骤3：若不开启自动注入，跳过当前项目
  if [ "$INJECT_JACOCO" != true ]; then
    print_info "项目 $project_name 中未找到 Jacoco 插件，且未开启自动注入，跳过"
    return 0
  fi

  # 步骤4：安全备份 pom.xml（带项目名+时间戳，避免备份文件冲突）
  local backup_pom="${pom_path}.bak_${project_name}_$(date +%Y%m%d_%H%M%S)"
  cp "$pom_path" "$backup_pom"
  print_info "项目 $project_name ：已创建 pom.xml 备份文件：$backup_pom"

  # 步骤5：定义 Jacoco 插件代码片段（格式规整，符合 Maven XML 规范）
  local jacoco_snippet="        <plugin>
            <groupId>org.jacoco</groupId>
            <artifactId>jacoco-maven-plugin</artifactId>
            <version>${JACOCO_VERSION}</version>
            <executions>
                <execution>
                    <id>prepare-agent</id>
                    <goals>
                        <goal>prepare-agent</goal>
                    </goals>
                </execution>
                <execution>
                    <id>report</id>
                    <phase>prepare-package</phase>
                    <goals>
                        <goal>report</goal>
                    </goals>
                </execution>
            </executions>
        </plugin>"

  # 步骤6：处理代码片段，转换为原始格式（解决换行/缩进转义问题）
  local jacoco_snippet_raw=$(printf "%b" "$jacoco_snippet")
  print_info "项目 $project_name ：已准备 Jacoco 插件代码片段（版本：${JACOCO_VERSION}）"

  # 步骤7：分情况注入 Jacoco 插件（兼容多种 pom.xml 结构）
  if grep -q "<build" "$pom_path" 2>/dev/null; then
    # 情况1：pom.xml 中存在 <build> 块
    print_info "项目 $project_name ：检测到 pom.xml 中存在 <build> 块，准备在其中注入 Jacoco 插件"
    
    # 找到 <build> 开始行和 </build> 结束行（行号）
    local build_start=$(grep -n -m1 "<build" "$pom_path" | cut -d: -f1)
    local build_end=$(grep -n -m1 "</build>" "$pom_path" | cut -d: -f1)
    
    # 查找 <build> 块内最后一个 </plugins> （避免插入到 <pluginManagement> 中）
    local plugin_rel_line=$(sed -n "${build_start},${build_end}p" "$pom_path" | grep -n "</plugins>" | tail -n1 | cut -d: -f1)
    
    if [ -n "$plugin_rel_line" ]; then
      # 子情况1.1：<build> 块内存在 <plugins> 块，插入到最后一个 </plugins> 之前
      local plugin_abs_line=$((build_start + plugin_rel_line - 1))
      print_info "项目 $project_name ：检测到 <build> 块内存在 <plugins> 块，准备插入到第 ${plugin_abs_line} 行之前"
      
      # 使用 awk 插入代码片段，保持格式完整
      awk -v LN="$plugin_abs_line" -v snippet="$jacoco_snippet_raw" '
        NR==LN { print snippet }
        { print }
      ' "$pom_path" > "$pom_path.tmp" && mv "$pom_path.tmp" "$pom_path"
    else
      # 子情况1.2：<build> 块内无 <plugins> 块，创建 <plugins> 块并插入
      print_info "项目 $project_name ：检测到 <build> 块内无 <plugins> 块，准备创建 <plugins> 块并注入"
      
      # 在 </build> 之前插入 <plugins> 块（包含 Jacoco 插件）
      local plugins_block="    <plugins>
${jacoco_snippet_raw}
    </plugins>"
      
      awk -v ENDLN="$build_end" -v snippet="$plugins_block" '
        NR==ENDLN { print snippet }
        { print }
      ' "$pom_path" > "$pom_path.tmp" && mv "$pom_path.tmp" "$pom_path"
    fi
  else
    # 情况2：pom.xml 中无 <build> 块，创建完整 <build><plugins> 块并插入
    print_info "项目 $project_name ：未检测到 pom.xml 中的 <build> 块，准备创建完整 <build> 块并注入"
    
    local build_block="  <build>
    <plugins>
${jacoco_snippet_raw}
    </plugins>
  </build>"
    
    # 在 </project> 之前插入完整 <build> 块
    sed -i.bak "s|</project>|${build_block}\n</project>|" "$pom_path"
    # 清理 sed 生成的临时备份文件（与我们的自定义备份区分）
    rm -f "${pom_path}.bak"
  fi

  # 步骤8：验证当前项目的注入结果
  if grep -q "artifactId>jacoco-maven-plugin" "$pom_path" 2>/dev/null; then
    print_success "项目 $project_name ：Jacoco 插件已成功注入到 pom.xml"
    print_info "项目 $project_name ：备份文件：$backup_pom"
    print_info "项目 $project_name ：后续可执行 'mvn clean test' 生成覆盖率报告（默认输出到 target/site/jacoco/）"
    return 0
  else
    print_error "项目 $project_name ：Jacoco 插件注入失败，请手动检查 pom.xml 格式"
    print_info "项目 $project_name ：已保留备份文件：$backup_pom，可用于还原 pom.xml"
    return 1
  fi
}

# ===================================== 主流程：批量遍历子文件夹并处理 =====================================
main() {
  # 步骤1：验证总项目根目录是否存在
  if [ ! -d "$DEFECT4J_PROJECTS_ROOT" ]; then
    print_error "总项目根目录未找到，路径：$DEFECT4J_PROJECTS_ROOT"
    print_info "请检查目录路径是否正确，或修改脚本中的 DEFECT4J_PROJECTS_ROOT 配置项"
    exit 1
  fi

  print_info "===================================== 开始批量处理项目 ====================================="
  print_info "总项目根目录：$DEFECT4J_PROJECTS_ROOT"
  print_info "Jacoco 插件版本：$JACOCO_VERSION"
  print_info "自动注入开关：$INJECT_JACOCO"
  echo -e

  # 步骤2：初始化统计变量
  local total_projects=0
  local success_projects=0
  local failed_projects=0
  local skipped_projects=0

  # 步骤3：遍历总项目根目录下的所有直接子文件夹（如 csv_1_b）
  while IFS= read -r -d '' project_dir; do
    # 跳过非目录（兜底过滤）
    if [ ! -d "$project_dir" ]; then
      continue
    fi

    total_projects=$((total_projects + 1))
    local project_name=$(basename "$project_dir")
    local pom_path="${project_dir}/pom.xml"

    # 检查当前子文件夹中是否存在 pom.xml
    if [ ! -f "$pom_path" ]; then
      print_warning "项目 $project_name ：未找到 pom.xml，跳过该项目"
      skipped_projects=$((skipped_projects + 1))
      echo -e
      continue
    fi

    # 步骤4：处理当前项目的 pom.xml
    if process_single_pom "$pom_path"; then
      # 处理成功（包含「已存在插件」和「注入成功」两种情况）
      if grep -q "artifactId>jacoco-maven-plugin" "$pom_path" 2>/dev/null; then
        success_projects=$((success_projects + 1))
      else
        skipped_projects=$((skipped_projects + 1))
      fi
    else
      # 处理失败
      failed_projects=$((failed_projects + 1))
    fi

    echo -e  # 空行分隔，优化日志可读性
  done < <(find "$DEFECT4J_PROJECTS_ROOT" -maxdepth 1 -type d -print0 | grep -vzZ "^${DEFECT4J_PROJECTS_ROOT}$")

  # 步骤5：输出批量处理汇总报告
  print_info "===================================== 批量处理完成汇总 ====================================="
  print_info "总扫描项目数：$total_projects"
  print_success "成功处理（已存在/注入成功）：$success_projects"
  print_warning "跳过项目（无 pom.xml/未开启注入）：$skipped_projects"
  print_error "处理失败项目：$failed_projects"
  print_info "============================================================================================"
}

# 调用主流程
main