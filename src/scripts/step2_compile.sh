#!/bin/bash
# =============================================================================
# Step 2: 批量编译 Defects4J 项目（buggy + fixed 版本）
#
# 修复记录：
#   v1: 原版，用 xargs | while 管道，有 SIGPIPE + 子shell计数失效问题
#   v2: 改用后台进程池 + 临时文件，修复 SIGPIPE
#   v3（本版）: 修复 Ant 项目跳过检测——原跳过逻辑只看 target/classes，
#              Closure/Chart 等 Ant 项目产物在 build/classes 或 build/，
#              导致中断后重跑还会重新编译这些项目
#
# 构建工具 & 产物路径说明（Defects4J v2/v3）：
#   Maven 项目（Csv/Codec/Collections/Compress/Gson/JacksonCore/
#              JacksonDatabind/JacksonXml/Jsoup/JxPath/Cli 等）:
#       → target/classes
#   Ant 项目，D4J 注入 Maven wrapper（Lang/Math/Time）:
#       → target/classes  （D4J 统一了产物路径）
#   Ant 项目，原生构建（Chart）:
#       → build/          （Chart.build.xml 指定）
#   Ant 项目，原生构建（Closure）:
#       → build/classes   （你已确认 build/lib 也会生成）
#   Gradle 项目，D4J 用 Ant wrapper（Mockito）:
#       → target/classes  （wrapper 统一了产物路径）
#
# 用法:
#   bash step2_compile.sh --root /storage/nvme3/chenlu/data/d4j_projects
#   bash step2_compile.sh --root /storage/nvme3/chenlu/data/d4j_projects --projects Csv,Lang
#   PARALLEL=8 bash step2_compile.sh --root /storage/nvme3/chenlu/data/d4j_projects
# =============================================================================

ROOT_DIR="/home/chenlu/refine_test_gen_v5/defect4j_projects"
PARALLEL="${PARALLEL:-4}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

# ── 参数解析 ──────────────────────────────────────────────────────────────────
FILTER_PROJECTS=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --root)     ROOT_DIR="$2"; shift 2 ;;
        --projects) IFS=',' read -ra FILTER_PROJECTS <<< "$2"; shift 2 ;;
        --parallel) PARALLEL="$2"; shift 2 ;;
        *) shift ;;
    esac
done

LOG_FILE="$ROOT_DIR/compile_$(date +%Y%m%d_%H%M%S).log"
RESULT_DIR=$(mktemp -d)
trap 'rm -rf "$RESULT_DIR"' EXIT

echo -e "${BLUE}[INFO]${NC} === 批量编译开始 ===" | tee -a "$LOG_FILE"
echo -e "${BLUE}[INFO]${NC} 根目录:  $ROOT_DIR"    | tee -a "$LOG_FILE"
echo -e "${BLUE}[INFO]${NC} 并行数:  $PARALLEL"    | tee -a "$LOG_FILE"
echo -e "${BLUE}[INFO]${NC} 日志:    $LOG_FILE"    | tee -a "$LOG_FILE"

# ── 判断项目是否已编译（兼容 Maven / Ant / Gradle 产物路径）──────────────────
# 返回 0 = 已编译可跳过，返回 1 = 需要编译
is_already_compiled() {
    local proj_dir="$1"

    # ── 路径1: Maven / D4J-wrapped Ant+Gradle 的统一产物路径 ──────────────
    if [[ -d "$proj_dir/target/classes" ]]; then
        return 0
    fi

    # ── 路径2: Chart 原生 Ant（产物直接在 build/ 下，无 classes 子目录）──
    # Chart.build.xml: <javac destdir="${basedir}/build" ...>
    if [[ -d "$proj_dir/build" && -f "$proj_dir/build.xml" ]]; then
        # 检查 build/ 下是否真的有 .class 文件（避免空 build 目录被误判）
        local class_count
        class_count=$(find "$proj_dir/build" -name "*.class" -maxdepth 5 2>/dev/null | wc -l)
        if [[ $class_count -gt 10 ]]; then  # 阈值10，避免少量测试 class 触发
            return 0
        fi
    fi

    # ── 路径3: Closure 原生 Ant（产物在 build/classes）────────────────────
    if [[ -d "$proj_dir/build/classes" ]]; then
        local class_count
        class_count=$(find "$proj_dir/build/classes" -name "*.class" -maxdepth 5 2>/dev/null | wc -l)
        if [[ $class_count -gt 10 ]]; then
            return 0
        fi
    fi

    # ── 路径4: 通用兜底——读取 defects4j.build.properties 里的产物路径 ────
    # defects4j checkout 后会生成 defects4j.build.properties
    # 里面有 d4j.dir.src.classes 字段指向实际编译产物目录
    local prop_file="$proj_dir/defects4j.build.properties"
    if [[ -f "$prop_file" ]]; then
        local classes_dir
        classes_dir=$(grep "^d4j.dir.classes.main=" "$prop_file" 2>/dev/null \
                      | cut -d= -f2 | tr -d '[:space:]')
        if [[ -n "$classes_dir" ]]; then
            local full_path="$proj_dir/$classes_dir"
            if [[ -d "$full_path" ]]; then
                local class_count
                class_count=$(find "$full_path" -name "*.class" -maxdepth 5 2>/dev/null | wc -l)
                [[ $class_count -gt 10 ]] && return 0
            fi
        fi
    fi

    return 1
}

# ── 单任务编译函数 ─────────────────────────────────────────────────────────────
compile_one() {
    local proj_dir="$1"
    local result_dir="$2"
    local proj_name
    proj_name=$(basename "$proj_dir")
    local status_file="$result_dir/$proj_name"
    local log_file="$result_dir/${proj_name}.log"

    if [[ "$proj_name" == Time_* ]]; then
        rm -rf "$proj_dir/build" "$proj_dir/target"
    fi

    # 已编译跳过（兼容 Maven/Ant/Gradle 所有路径）
    if is_already_compiled "$proj_dir"; then
        echo "SKIP" > "$status_file"
        return 0
    fi

    # 方法1: defects4j compile（优先，自动处理所有构建工具差异）
    if defects4j compile -w "$proj_dir" > "$log_file" 2>&1; then
        echo "OK_D4J" > "$status_file"
        return 0
    fi

    # 方法2: mvn compile 降级（仅对 Maven 项目有效，Ant 项目 pom.xml 不存在会自然跳过）
    if [[ -f "$proj_dir/pom.xml" ]]; then
        if mvn compile \
                -f "$proj_dir/pom.xml" \
                -q -DskipTests \
                -Dmaven.compiler.failOnError=false \
                >> "$log_file" 2>&1; then
            echo "OK_MVN" > "$status_file"
            return 0
        fi
    fi

    echo "FAIL" > "$status_file"
    return 0
}

# ── 收集项目目录 ──────────────────────────────────────────────────────────────
all_projects=()
while IFS= read -r -d '' proj; do
    proj_name=$(basename "$proj")
    if [[ ${#FILTER_PROJECTS[@]} -gt 0 ]]; then
        match=false
        for fp in "${FILTER_PROJECTS[@]}"; do
            [[ "$proj_name" == ${fp}_* ]] && match=true && break
        done
        [[ "$match" == false ]] && continue
    fi
    all_projects+=("$proj")
done < <(find "$ROOT_DIR" -maxdepth 1 -type d \( -name "*_b" -o -name "*_f" \) -print0 | sort -z)

echo -e "${BLUE}[INFO]${NC} 共发现 ${#all_projects[@]} 个项目目录" | tee -a "$LOG_FILE"

# 预检：打印各项目的编译状态（帮助确认哪些已完成）
echo -e "${BLUE}[INFO]${NC} 预检已编译项目..." | tee -a "$LOG_FILE"
precheck_compiled=0
for proj_dir in "${all_projects[@]}"; do
    if is_already_compiled "$proj_dir"; then
        ((precheck_compiled++))
    fi
done
echo -e "${BLUE}[INFO]${NC} 预检: ${precheck_compiled}/${#all_projects[@]} 个项目已编译，将跳过" | tee -a "$LOG_FILE"
echo ""

# ── 后台进程池 ────────────────────────────────────────────────────────────────
active_pids=()

wait_for_one_slot() {
    while true; do
        local remaining=()
        local freed=false
        for pid in "${active_pids[@]}"; do
            if kill -0 "$pid" 2>/dev/null; then
                remaining+=("$pid")
            else
                freed=true
                wait "$pid" 2>/dev/null || true
            fi
        done
        active_pids=("${remaining[@]}")
        [[ "$freed" == true ]] && return 0
        sleep 0.3
    done
}

total=${#all_projects[@]}
submitted=0

for proj_dir in "${all_projects[@]}"; do
    while [[ ${#active_pids[@]} -ge $PARALLEL ]]; do
        wait_for_one_slot
    done

    compile_one "$proj_dir" "$RESULT_DIR" &
    active_pids+=($!)
    ((submitted++))

    if (( submitted % 20 == 0 || submitted == total )); then
        echo -e "${BLUE}[INFO]${NC} 提交进度: $submitted / $total  (活跃: ${#active_pids[@]})" | tee -a "$LOG_FILE"
    fi
done

if [[ ${#active_pids[@]} -gt 0 ]]; then
    echo -e "${BLUE}[INFO]${NC} 等待最后 ${#active_pids[@]} 个任务完成..." | tee -a "$LOG_FILE"
    for pid in "${active_pids[@]}"; do
        wait "$pid" 2>/dev/null || true
    done
fi

# ── 汇总结果 ──────────────────────────────────────────────────────────────────
echo "" | tee -a "$LOG_FILE"
echo -e "${BLUE}[INFO]${NC} --- 编译结果汇总 ---" | tee -a "$LOG_FILE"

OK=0; FAIL=0; SKIP=0
failed_list=()

for proj_dir in "${all_projects[@]}"; do
    proj_name=$(basename "$proj_dir")
    status_file="$RESULT_DIR/$proj_name"

    if [[ ! -f "$status_file" ]]; then
        echo -e "${RED}[FAIL]${NC} $proj_name  (结果文件缺失)" | tee -a "$LOG_FILE"
        ((FAIL++))
        failed_list+=("$proj_name:no_result_file")
        continue
    fi

    status=$(cat "$status_file")
    case "$status" in
        OK_D4J)
            echo -e "${GREEN}[OK]${NC} $proj_name  (defects4j)" | tee -a "$LOG_FILE"
            ((OK++))
            ;;
        OK_MVN)
            echo -e "${GREEN}[OK]${NC} $proj_name  (maven降级)" | tee -a "$LOG_FILE"
            ((OK++))
            ;;
        SKIP)
            echo -e "${YELLOW}[SKIP]${NC} $proj_name  (已编译，跳过)" | tee -a "$LOG_FILE"
            ((SKIP++))
            ;;
        FAIL)
            echo -e "${RED}[FAIL]${NC} $proj_name" | tee -a "$LOG_FILE"
            ((FAIL++))
            failed_list+=("$proj_name")
            log_src="$RESULT_DIR/${proj_name}.log"
            if [[ -f "$log_src" ]]; then
                cp "$log_src" "${proj_dir}_compile_error.log"
                echo "        错误日志: ${proj_dir}_compile_error.log" | tee -a "$LOG_FILE"
            fi
            ;;
        *)
            echo -e "${RED}[FAIL]${NC} $proj_name  (未知状态: $status)" | tee -a "$LOG_FILE"
            ((FAIL++))
            failed_list+=("$proj_name:unknown_status")
            ;;
    esac
done

echo "" | tee -a "$LOG_FILE"
echo -e "${BLUE}[INFO]${NC} ============================================" | tee -a "$LOG_FILE"
echo -e "${BLUE}[INFO]${NC} === 编译完成 ===" | tee -a "$LOG_FILE"
echo -e "${GREEN}[OK]${NC}   成功: $OK" | tee -a "$LOG_FILE"
echo -e "${YELLOW}[SKIP]${NC} 跳过: $SKIP  (已编译)" | tee -a "$LOG_FILE"
echo -e "${RED}[FAIL]${NC} 失败: $FAIL" | tee -a "$LOG_FILE"
echo -e "${BLUE}[INFO]${NC} ============================================" | tee -a "$LOG_FILE"

if [[ ${#failed_list[@]} -gt 0 ]]; then
    echo "" | tee -a "$LOG_FILE"
    echo -e "${RED}[FAIL]${NC} 失败项目（共 ${#failed_list[@]} 个）:" | tee -a "$LOG_FILE"
    for p in "${failed_list[@]}"; do
        echo "  - $p" | tee -a "$LOG_FILE"
    done
fi

echo -e "${BLUE}[INFO]${NC} 完整日志: $LOG_FILE" | tee -a "$LOG_FILE"