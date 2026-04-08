"""
tools.py — 工具函数
"""
from __future__ import annotations

import json
import os
import re
import shutil
import psutil

import javalang
import tiktoken

from config import dataset_dir, result_dir, project_dir, MAX_PROMPT_TOKENS

enc      = tiktoken.get_encoding("cl100k_base")
encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")


# ── Token 计算 ─────────────────────────────────────────────────────────

def count_tokens(s: str) -> int:
    return len(encoding.encode(s))


def get_messages_tokens(messages: list) -> int:
    if not isinstance(messages, list):
        return 0
    total = 0
    for msg in messages:
        if not isinstance(msg, dict) or "content" not in msg:
            continue
        try:
            total += len(enc.encode(msg["content"]))
        except Exception:
            total += len(msg["content"]) // 4
    return total


def process_error_message(error_message: str, allowed_tokens: int) -> str:
    if allowed_tokens <= 0:
        return ""
    while count_tokens(error_message) > allowed_tokens:
        if len(error_message) > 50:
            error_message = error_message[:-50]
        else:
            break
    return error_message


def find_processes_created_by(pid):
    """Find the process's and all subprocesses' pid"""
    parent_process = psutil.Process(pid)
    child_processes = parent_process.children(recursive=True)
    pids = [process.pid for process in child_processes]
    return pids.append(pid)


def find_result_in_projects():
    """Find the new directory."""
    all_results = [x for x in os.listdir(project_dir) if '%' in x]
    all_results = sorted(all_results, key=lambda x: x)
    return os.path.join(result_dir, all_results[-1])


def check_java_version():
    java_home = os.environ.get('JAVA_HOME', '')
    if 'jdk-17' in java_home:
        return 17
    elif 'jdk-11' in java_home:
        return 11


# ── 数据集路径工具 ─────────────────────────────────────────────────────

def gen_file_name(method_id, project_name, class_name, method_name, direction) -> str:
    return f"{method_id}%{project_name}%{class_name}%{method_name}%{direction}.json"


def get_project_abspath():
    return os.path.abspath(project_dir)


def get_dataset_path(method_id, project_name, class_name, method_name, direction):
    if direction == "raw":
        return os.path.join(dataset_dir, "raw_data",
                            method_id + "%" + project_name + "%" + class_name + "%" + method_name + "%raw.json")
    return os.path.join(dataset_dir, "direction_" + str(direction),
                        method_id + "%" + project_name + "%" + class_name + "%" + method_name + "%d" + str(
                            direction) + ".json")


def remove_single_test_output_dirs(project_path):
    prefix = "test_"
    directories = [d for d in os.listdir(project_path) if os.path.isdir(d) and d.startswith(prefix)]
    for d in directories:
        try:
            shutil.rmtree(d)
            print(f"Directory {d} deleted successfully.")
        except Exception as e:
            print(f"Error deleting directory {d}: {e}")


def parse_file_name(base_name: str):
    """
    Parse: 1%Csv_1_b%Token%reset%d3.json  →  (method_id, project_name, class_name, method_name)
    """
    name = base_name.replace(".json", "")
    parts = name.split("%")
    if len(parts) >= 4:
        return parts[0], parts[1], parts[2], parts[3]
    return name, "", "", ""


# ── Package 规范化（Bug Fix 核心）────────────────────────────────────

def normalize_package_decl(package_val: str) -> str:
    """
    将任意格式的 package 值规范化为纯净的包名字符串（不含 "package " 前缀和 ";" 后缀）。

    输入示例：
      "package org.apache.commons.csv;"   → "org.apache.commons.csv"
      "org.apache.commons.csv"            → "org.apache.commons.csv"
      "package org.apache.commons.csv"    → "org.apache.commons.csv"
      "  package  org.apache.commons.csv; " → "org.apache.commons.csv"

    这样调用方可以安全地构造 f"package {normalize_package_decl(package)};" 而不会重复。
    """
    if not package_val:
        return ""
    s = package_val.strip()
    # 去掉 "package " 前缀（可能重复出现）
    while s.startswith("package ") or s.startswith("package\t"):
        s = re.sub(r'^package\s+', '', s).strip()
    # 去掉尾部分号
    s = s.rstrip(";").strip()
    return s


def canonical_package_decl(package_val: str) -> str:
    """
    返回标准的 package 声明行，格式为 "package xxx.yyy;"。
    无论 package_val 是 "org.apache.commons.csv" 还是
    "package org.apache.commons.csv;" 都能正确处理。
    """
    pkg = normalize_package_decl(package_val)
    if not pkg:
        return ""
    return f"package {pkg};"


# ── Java 代码工具 ──────────────────────────────────────────────────────

def repair_package(code: str, package_info: str) -> str:
    """
    修正 Java 源码中的 package 声明。

    package_info 应为完整声明行，如 "package org.apache.commons.csv;"
    内部会先用 canonical_package_decl 规范化，防止调用方传入已含 "package " 前缀的值。

    Bug Fix:
      旧代码中调用方传 f"package {package};" 而 package 值可能已含
      "package xxx;" 全文，导致产生 "package package xxx;;"。
      修复后此函数内部自行规范化，调用方无需关心 package_val 的原始格式。
    """
    # 规范化 package_info：确保是标准的 "package xxx;" 格式
    pkg_decl = canonical_package_decl(package_info) if package_info else ""
    if not pkg_decl:
        return code

    lines = code.splitlines()

    # 检测代码里是否已有 package 声明
    if any(l.strip().startswith("package ") for l in lines):
        new_lines = []
        replaced = False
        for l in lines:
            if l.strip().startswith("package ") and not replaced:
                new_lines.append(pkg_decl)
                replaced = True
            else:
                new_lines.append(l)
        return "\n".join(new_lines)

    # 没有 package 声明：插到最前面
    return pkg_decl + "\n" + code


def repair_imports(code: str, imports: str) -> str:
    """
    将缺失的 import 行追加到代码顶部。

    Bug Fix:
      原实现对 imports 里每行都 prepend，导致：
      1. package 行可能混入 imports（export_data direction_1 里含 package）被错误 prepend
      2. 多次 prepend 破坏 package 必须在最前的 Java 语法要求

      修复：
      - 过滤掉 imports 中的 package 声明行（package 行由 repair_package 负责）
      - import 行只在代码中真正缺失时才添加（原逻辑保留）
      - 新增的 import 行统一插入到 package 声明之后、class 声明之前的正确位置
    """
    if not imports:
        return code

    # 收集需要添加的 import 行（过滤掉 package 行）
    missing_imports = []
    for imp_line in imports.strip().splitlines():
        imp_line = imp_line.strip()
        if not imp_line:
            continue
        # 跳过 package 声明行（不属于 import）
        if imp_line.startswith("package "):
            continue
        if imp_line not in code:
            missing_imports.append(imp_line)

    if not missing_imports:
        return code

    # 找到插入位置：package 声明之后、第一个 import 或 class 之前
    lines = code.splitlines(keepends=True)
    insert_idx = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("package "):
            insert_idx = i + 1  # package 之后
        elif stripped.startswith("import ") or re.match(r'(public\s+)?(class|interface|enum|@interface)\s+', stripped):
            # 在第一个 import 或 class 声明之前插入
            insert_idx = i
            break

    import_block = "\n".join(missing_imports) + "\n"
    lines.insert(insert_idx, import_block)
    return "".join(lines)


def remove_imports(code: str) -> str:
    return re.sub(r'^import\s+.*;\s*\n', '', code, flags=re.MULTILINE)


def change_class_name(code: str, class_name: str, method_id, seq: int) -> str:
    """将源码中的测试类名替换为 <ClassName>_<method_id>_<seq>Test。"""
    new_cls = f"{class_name}_{method_id}_{seq}Test"
    code = re.sub(
        r'\bclass\s+(\w+Test)\b',
        lambda m: f"class {new_cls}",
        code,
    )
    code = re.sub(
        rf'\b{re.escape(class_name)}Test\b',
        new_cls,
        code,
    )
    return code


def is_syntactic_correct(code: str) -> bool:
    try:
        javalang.parse.parse(code)
        return True
    except Exception:
        return False


def syntactic_check(code: str):
    """语法修复：尝试补全不完整的大括号。返回 (had_error, fixed_code)"""
    if is_syntactic_correct(code):
        return False, code
    stop_points = [";", "}", "{", " "]
    for idx in range(len(code) - 1, -1, -1):
        if code[idx] in stop_points:
            code = code[:idx + 1]
            break
    left  = code.count("{")
    right = code.count("}")
    code += "}\n" * (left - right)
    if is_syntactic_correct(code):
        return True, code
    return True, ""


def extract_code(input_string: str):
    """
    从 LLM 输出中提取 Java 代码。
    返回 (has_code, extracted_code, has_syntactic_error)
    """
    code_lines       = input_string.splitlines(keepends=True)
    extracted_code   = ""
    has_code         = False
    has_syntactic_err= False

    # 1) 找 markdown code block（```java ... ```）
    in_block = False
    block_lines: list = []
    for line in code_lines:
        if line.strip().startswith("```java"):
            in_block = True
            continue
        if in_block and line.strip().startswith("```"):
            in_block = False
            break
        if in_block:
            block_lines.append(line)
    if block_lines:
        candidate = "".join(block_lines)
        has_syntactic_err, candidate = syntactic_check(candidate)
        if candidate:
            extracted_code = candidate
            has_code = True
            return has_code, extracted_code, has_syntactic_err

    # 2) LLM 直接输出完整 Java（无 ``` 包裹）
    # 从文件开头尝试（保留 package 声明）
    full = input_string.strip()
    if full.startswith("package ") or full.startswith("import ") or re.match(r'\s*(public\s+)?class\s+', full):
        # 整个输出就是 Java 代码
        has_syntactic_err, candidate = syntactic_check(full)
        if candidate:
            return True, candidate, has_syntactic_err

    # 3) 从 class 关键字开始截取（向前保留 package/import）
    m = re.search(r'(public\s+class|class)\s+\w+', full)
    if m:
        # 尝试从头开始（保留 package）
        start = 0
        # 找 package 行
        pkg_m = re.search(r'^package\s+[\w.]+;', full, re.MULTILINE)
        if pkg_m and pkg_m.start() < m.start():
            start = pkg_m.start()
        else:
            # 退而向前找最近的换行
            start = full.rfind('\n', 0, m.start())
            if start < 0:
                start = 0

        snippet = full[start:].strip()
        depth = 0
        end = len(snippet)
        for i, ch in enumerate(snippet):
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        candidate = snippet[:end]
        has_syntactic_err, candidate = syntactic_check(candidate)
        if candidate:
            extracted_code = candidate
            has_code = True
    return has_code, extracted_code, has_syntactic_err


# ── 结果目录工具 ────────────────────────────────────────────────────────

def get_latest_file(directory: str, suffix: str = None) -> str | None:
    """返回目录下最新（按修改时间）的文件路径。"""
    files = [
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if os.path.isfile(os.path.join(directory, f))
        and (suffix is None or suffix in f)
    ]
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def export_method_test_case(temp_dir: str, class_name: str, method_id, seq: int, code: str):
    """将测试类写入 temp_dir 下的 java 文件（ChatUniTest 约定）。"""
    fname = f"{class_name}_{method_id}_{seq}Test.java"
    path  = os.path.join(temp_dir, fname)
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    return path


def collect_token_results_from_result_path(tests_dir_path):
    """
    tests_dir_path 参数传入的是 defect4j_projects/Csv_1_b/tests%xxx/ 路径，
    但实际 time_stats.json 存储在 results_batch/Csv_1_b/scope_test%xxx/<method>/<num>/time_stats.json。
    → 解决方案：遍历配置文件中 result_dir 目录下最新的 scope_test%* 目录
    """
    import re

    # ── 查找 result_dir 目录下最新的 scope_test%* 目录 ──
    scope_test_dirs = sorted(
        glob.glob(os.path.join(result_dir, "scope_test%*")),
        key=lambda p: int(re.search(r"(\d+)", os.path.basename(p)).group(1))
                      if re.search(r"(\d+)", os.path.basename(p)) else 0
    )
    if not scope_test_dirs:
        return []
    search_root = scope_test_dirs[-1]   # 使用最新的 scope_test%* 目录

    token_results = []
    # 目录结构：scope_test%xxx / <method_id>%<proj>%<class>%<method> / <test_num> / time_stats.json
    for method_dir in os.listdir(search_root):
        method_path = os.path.join(search_root, method_dir)
        if not os.path.isdir(method_path) or '%' not in method_dir:
            continue
        parts = method_dir.split('%')
        if len(parts) < 4:
            continue
        method_id, project_name, class_name, method_name = parts[0], parts[1], parts[2], parts[3]

        for test_num_str in os.listdir(method_path):
            test_dir = os.path.join(method_path, test_num_str)
            if not os.path.isdir(test_dir) or not test_num_str.isdigit():
                continue
            time_stats_file = os.path.join(test_dir, "time_stats.json")
            if not os.path.exists(time_stats_file):
                continue
            try:
                with open(time_stats_file, "r", encoding="utf-8") as f:
                    ts = json.load(f)
                # 累计 token 需从最新的 raw/imports 文件中读取
                # 或累加 time_stats.json 同目录下 *_raw_*.json 文件的 token 数值
                total_prompt = 0
                total_completion = 0
                total_tokens = 0
                for fname in os.listdir(test_dir):
                    if fname.endswith(".json") and "_raw_" in fname:
                        try:
                            with open(os.path.join(test_dir, fname), "r") as rf:
                                raw = json.load(rf)
                            total_prompt     += raw.get("prompt_tokens", 0)
                            total_completion += raw.get("completion_tokens", 0)
                            total_tokens     += raw.get("total_tokens", 0)
                        except Exception:
                            pass

                token_results.append({
                    "method_id":               method_id,
                    "project_name":            project_name,
                    "class_name":              class_name,
                    "method_name":             method_name,
                    "test_num":                int(test_num_str),
                    "elapsed_seconds":         ts.get("total_elapsed_time_seconds", 0),
                    "total_prompt_tokens":     total_prompt,
                    "total_completion_tokens": total_completion,
                    "total_tokens":            total_tokens,
                })
            except Exception as e:
                print(f"[WARN] 读取 {time_stats_file} 失败: {e}")
    return token_results


def write_llm_summary(token_results, output_dir):
    """
    将 token_results 写成 test_summary.json 和 method_summary.json，
    输出到 output_dir（应为 tests%xxx/ 目录，与 status/coverage 同级）。
    
    :param token_results: collect_token_results_from_result_path() 或
                          start_whole_process() 返回的列表
    :param output_dir: 目标目录（确保已存在）
    """
    from collections import defaultdict
    import json, os

    os.makedirs(output_dir, exist_ok=True)

    # ── test_summary.json ────────────────────────────────────────────────
    test_summary_rows = []
    for ts in token_results:
        test_summary_rows.append({
            "method_id":               ts.get("method_id", ""),
            "project_name":            ts.get("project_name", ""),
            "class_name":              ts.get("class_name", ""),
            "method_name":             ts.get("method_name", ""),
            "test_num":                ts.get("test_num", ""),
            "elapsed_seconds":         ts.get("elapsed_seconds", 0),
            "total_prompt_tokens":     ts.get("total_prompt_tokens", 0),
            "total_completion_tokens": ts.get("total_completion_tokens", 0),
            "total_tokens":            ts.get("total_tokens", 0),
        })

    test_summary_path = os.path.join(output_dir, "test_summary.json")
    with open(test_summary_path, "w", encoding="utf-8") as f:
        json.dump(test_summary_rows, f, indent=2, ensure_ascii=False)
    print(f"[Summary] test_summary 已写入: {test_summary_path}")

    # ── method_summary.json ─────────────────────────────────────────────
    method_groups = defaultdict(list)
    for ts in token_results:
        method_groups[ts.get("method_id", "unknown")].append(ts)

    method_summary_rows = []
    for mid, group in sorted(method_groups.items()):
        test_count       = len(group)
        total_elapsed    = round(sum(r.get("elapsed_seconds", 0) for r in group), 2)
        total_prompt     = sum(r.get("total_prompt_tokens", 0) for r in group)
        total_completion = sum(r.get("total_completion_tokens", 0) for r in group)
        total_tok        = sum(r.get("total_tokens", 0) for r in group)
        method_summary_rows.append({
            "method_id":               mid,
            "project_name":            group[0].get("project_name", ""),
            "class_name":              group[0].get("class_name", ""),
            "method_name":             group[0].get("method_name", ""),
            "test_count":              test_count,
            "total_elapsed_seconds":   total_elapsed,
            "avg_elapsed_seconds":     round(total_elapsed / test_count, 2) if test_count else 0,
            "total_prompt_tokens":     total_prompt,
            "total_completion_tokens": total_completion,
            "total_tokens":            total_tok,
            "avg_tokens_per_test":     round(total_tok / test_count, 2) if test_count else 0,
        })

    method_summary_path = os.path.join(output_dir, "method_summary.json")
    with open(method_summary_path, "w", encoding="utf-8") as f:
        json.dump(method_summary_rows, f, indent=2, ensure_ascii=False)
    print(f"[Summary] method_summary 已写入: {method_summary_path}")
