"""
contract_integration.py
========================
将程序合约（Program Contracts）集成到 RefineTestGen pipeline 的辅助模块。

主要提供：
  1. extract_contract_for_focal_method()  —— 从 raw_data 提取合约
  2. generate_one_test_with_contract()    —— 带合约的测试生成（替换原 generate_one_test）
  3. build_fix_messages_with_contract()   —— 带合约的修复 Prompt 构建

设计原则：
  - 向后兼容：合约提取失败时静默降级，不影响现有流程
  - 合约内容以自然语言注入 Prompt，无需修改 LLM 调用接口
  - 合约信息同时作用于 Generator（初始生成）和 Refiner（精修）
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Dict, List, Optional, Tuple

from contract_extractor import ContractExtractor, MethodContract

logger = logging.getLogger(__name__)

_extractor = ContractExtractor()


# ════════════════════════════════════════════════════════════════════
# 合约提取：从 raw_data JSON 中解析并提取合约
# ════════════════════════════════════════════════════════════════════

def extract_contract_for_focal_method(
    raw_data: dict,
    ctx_d1: dict,
) -> Optional[MethodContract]:
    """
    从 raw_data（export_data 导出的 JSON）中提取 focal method 的程序合约。

    Parameters
    ----------
    raw_data : 原始方法数据（含 source_code, method_name, parameters 等）
    ctx_d1   : direction_1 数据（含 information 字段，包含类上下文）

    Returns
    -------
    MethodContract | None  失败时返回 None（不影响正常流程）
    """
    try:
        source_code  = raw_data.get("source_code", "")
        method_name  = raw_data.get("method_name", "")
        parameters   = raw_data.get("parameters", "")
        class_name   = raw_data.get("class_name", "")
        imports      = raw_data.get("imports", "")

        # 从 parameters 字段中提取完整参数字符串
        # parameters 字段格式为 "methodName(Type1 param1, Type2 param2)"
        # 提取括号内的内容
        params_str = ""
        if "(" in parameters and ")" in parameters:
            params_str = parameters[parameters.index("(") + 1:parameters.rindex(")")]

        # 推断返回类型（从源码第一行解析）
        return_type = _infer_return_type(source_code, method_name)

        # 从 information (ctx_d1) 中提取类字段
        class_fields = _extract_fields_from_context(ctx_d1.get("information", ""))

        # 提取合约
        contract = _extractor.extract(
            source_code  = source_code,
            method_name  = method_name,
            parameters   = params_str,
            return_type  = return_type,
            class_name   = class_name,
            class_fields = class_fields,
            javadoc      = _extract_javadoc(source_code),
        )

        if not contract.is_empty():
            logger.info(
                "[Contract] Extracted for %s.%s: %d preconditions, %d postconditions, %d exceptions",
                class_name, method_name,
                len(contract.preconditions),
                len(contract.postconditions),
                len(contract.exception_contracts),
            )
            return contract
        else:
            logger.debug("[Contract] No contract extracted for %s.%s", class_name, method_name)
            return None

    except Exception as e:
        logger.warning("[Contract] Extraction failed for %s: %s", raw_data.get("method_name", "?"), e)
        return None


def save_contract(contract: MethodContract, base_dir: str) -> str:
    """将合约保存为 JSON 文件，便于调试和审计。"""
    path = os.path.join(base_dir, "method_contract.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(contract.to_dict(), f, indent=2, ensure_ascii=False)
        logger.info("[Contract] Saved to %s", path)
    except Exception as e:
        logger.warning("[Contract] Save failed: %s", e)
    return path


# ════════════════════════════════════════════════════════════════════
# 内部辅助：从源码提取信息
# ════════════════════════════════════════════════════════════════════

def _infer_return_type(source_code: str, method_name: str) -> str:
    """从方法签名推断返回类型。"""
    import re
    if not source_code:
        return ""
    # 匹配方法签名第一行：public/private/protected ... ReturnType methodName(
    pattern = rf'(?:public|private|protected|static|final|synchronized|\s)+\s+([\w<>\[\],.?\s]+?)\s+{re.escape(method_name)}\s*\('
    m = re.search(pattern, source_code)
    if m:
        ret = m.group(1).strip()
        # 过滤掉修饰符（万一正则没过滤干净）
        ret = re.sub(r'\b(public|private|protected|static|final|synchronized|abstract|native)\b', '', ret).strip()
        return ret
    return ""


def _extract_fields_from_context(information: str) -> str:
    """从 ctx_d1.information（类上下文）中提取字段声明。"""
    import re
    field_lines = []
    for line in information.splitlines():
        stripped = line.strip()
        # 典型字段：修饰符 类型 名称;
        if re.match(r'(?:private|protected|public|static|final)\s+\w[\w<>\[\]]*\s+\w+\s*[=;]', stripped):
            field_lines.append(stripped)
    return "\n".join(field_lines)


def _extract_javadoc(source_code: str) -> str:
    """提取方法上方的 Javadoc 注释。"""
    import re
    m = re.search(r'/\*\*(.*?)\*/', source_code, re.DOTALL)
    return m.group(0) if m else ""


# ════════════════════════════════════════════════════════════════════
# 合约感知的 Prompt 上下文增强
# ════════════════════════════════════════════════════════════════════

def enrich_ctx_with_contract(
    ctx: dict,
    contract: Optional[MethodContract],
) -> dict:
    """
    将合约文本注入到 prompt 上下文字典中。
    返回增强后的上下文（不修改原始 ctx）。
    """
    import copy
    enriched = copy.deepcopy(ctx)
    if contract and not contract.is_empty():
        enriched["contract_text"] = contract.to_prompt_text()
    else:
        enriched["contract_text"] = ""
    return enriched


def get_contract_text(contract: Optional[MethodContract]) -> str:
    """安全地获取合约文本，合约为 None 时返回空字符串。"""
    if contract and not contract.is_empty():
        return contract.to_prompt_text()
    return ""