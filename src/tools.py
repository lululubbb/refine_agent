"""
tools.py — 工具函数（完全复用 ChatUniTest tools.py 的接口，保持兼容）
"""
from __future__ import annotations

import json
import os
import re
import shutil

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
    """
    Find the process's and all subprocesses' pid
    """
    parent_process = psutil.Process(pid)
    child_processes = parent_process.children(recursive=True)
    pids = [process.pid for process in child_processes]
    return pids.append(pid)

def find_result_in_projects():
    """
    Find the new directory.
    :return: The new directory.
    """
    all_results = [x for x in os.listdir(project_dir) if '%' in x]
    all_results = sorted(all_results, key=get_date_string)
    return os.path.join(result_dir, all_results[-1])


def check_java_version():
    java_home = os.environ.get('JAVA_HOME')
    if 'jdk-17' in java_home:
        return 17
    elif 'jdk-11' in java_home:
        return 11

# ── 数据集路径工具（复用 ChatUniTest 约定） ────────────────────────────

def gen_file_name(method_id, project_name, class_name, method_name, direction) -> str:
    return f"{method_id}%{project_name}%{class_name}%{method_name}%{direction}.json"

def get_project_abspath():
    return os.path.abspath(project_dir)


def get_dataset_path(method_id, project_name, class_name, method_name, direction):
    """
    Get the dataset path
    :return:
    """
    if direction == "raw":
        return os.path.join(dataset_dir, "raw_data",
                            method_id + "%" + project_name + "%" + class_name + "%" + method_name + "%raw.json")
    return os.path.join(dataset_dir, "direction_" + str(direction),
                        method_id + "%" + project_name + "%" + class_name + "%" + method_name + "%d" + str(
                            direction) + ".json")

def remove_single_test_output_dirs(project_path):
    prefix = "test_"

    # Get a list of all directories in the current directory with the prefix
    directories = [d for d in os.listdir(project_path) if os.path.isdir(d) and d.startswith(prefix)]

    # Iterate through the directories and delete them if they are not empty
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


# ── Java 代码工具（复用 ChatUniTest 实现） ─────────────────────────────

def repair_package(code: str, package_info: str) -> str:
    """修正 package 声明。"""
    lines = code.splitlines()
    if any(l.strip().startswith("package ") for l in lines):
        new_lines = []
        replaced = False
        for l in lines:
            if l.strip().startswith("package ") and not replaced:
                new_lines.append(package_info)
                replaced = True
            else:
                new_lines.append(l)
        return "\n".join(new_lines)
    return package_info + "\n" + code


def remove_imports(code: str) -> str:
    return re.sub(r'^import\s+.*;\s*\n', '', code, flags=re.MULTILINE)


def repair_imports(code: str, imports: str) -> str:
    """将 imports 追加到代码顶部（如果还没有）。"""
    if not imports:
        return code
    for imp_line in imports.strip().splitlines():
        imp_line = imp_line.strip()
        if imp_line and imp_line not in code:
            code = imp_line + "\n" + code
    return code


def change_class_name(code: str, class_name: str, method_id, seq: int) -> str:
    """
    将源码中的测试类名替换为 <ClassName>_<method_id>_<seq>Test。
    """
    new_cls = f"{class_name}_{method_id}_{seq}Test"
    # 替换 class 声明中的类名
    code = re.sub(
        r'\bclass\s+(\w+Test)\b',
        lambda m: f"class {new_cls}",
        code,
    )
    # 替换构造函数名（如有）
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
    """
    语法修复：尝试补全不完整的大括号。
    返回 (had_error, fixed_code)
    """
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

    # 1) 找 markdown code block
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

    # 2) 找 public class ... { ... }
    full = input_string
    m = re.search(r'(public\s+class|class)\s+\w+', full)
    if m:
        start = full.rfind('\n', 0, m.start())
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
