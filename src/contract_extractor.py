"""
contract_extractor.py
======================
程序合约（Program Contracts）提取器

概念：程序合约源于 Hoare 逻辑（1969），包含：
  - 前置条件（Precondition）：调用函数前必须满足的约束（输入限制）
  - 后置条件（Postcondition）：函数执行后的输出保证
  - 不变量（Invariant）：执行前后均成立的类状态约束

本模块通过静态分析 Java focal method 的源码，自动推断其合约，
并将合约以自然语言形式注入到 Generator 的 Prompt 中，
从而减少 LLM 生成无效输入/错误断言，提升测试质量。

使用方式：
    from contract_extractor import ContractExtractor
    extractor = ContractExtractor()
    contract = extractor.extract(source_code, method_name, params, return_type)
    prompt_addition = contract.to_prompt_text()
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict


# ════════════════════════════════════════════════════════════════════
# 合约数据结构
# ════════════════════════════════════════════════════════════════════

@dataclass
class MethodContract:
    """单个 focal method 的程序合约。"""
    method_name: str
    return_type: str = ""

    # ── 前置条件（Preconditions）────────────────────────────────
    # 输入参数约束：参数不能为 null、必须在某范围内、不能为空集合等
    preconditions: List[str] = field(default_factory=list)

    # ── 后置条件（Postconditions）────────────────────────────────
    # 输出/副作用约束：返回值的类型/范围/内容保证、状态变化保证等
    postconditions: List[str] = field(default_factory=list)

    # ── 异常合约（Exception Contract）───────────────────────────
    # 在什么条件下抛出什么异常（帮助 LLM 生成异常测试用例）
    exception_contracts: List[str] = field(default_factory=list)

    # ── 状态不变量（State Invariants）───────────────────────────
    # 对象字段的约束，调用前后均成立
    invariants: List[str] = field(default_factory=list)

    # ── 参数语义摘要（辅助信息）─────────────────────────────────
    param_semantics: Dict[str, str] = field(default_factory=dict)

    def is_empty(self) -> bool:
        return (not self.preconditions and not self.postconditions
                and not self.exception_contracts and not self.invariants)

    def to_prompt_text(self) -> str:
        """
        将合约转换为适合注入到 LLM Prompt 的自然语言文本。
        格式简洁、清晰，方便 LLM 理解并遵循。
        """
        if self.is_empty():
            return ""

        lines = [
            f"## Program Contract for `{self.method_name}`",
            "",
            "Use the following contract to guide test generation. Tests MUST respect these constraints:",
        ]

        if self.preconditions:
            lines.append("")
            lines.append("### Preconditions (valid input constraints):")
            lines.append("Generate test cases that BOTH respect these constraints AND deliberately violate them")
            lines.append("(to test error handling). At least one test per constraint violation is required.")
            for p in self.preconditions:
                lines.append(f"  - {p}")

        if self.postconditions:
            lines.append("")
            lines.append("### Postconditions (guaranteed output properties):")
            lines.append("Each test assertion MUST verify at least one of these guarantees:")
            for p in self.postconditions:
                lines.append(f"  - {p}")

        if self.exception_contracts:
            lines.append("")
            lines.append("### Exception Contracts (when exceptions should be thrown):")
            lines.append("Generate specific tests for each exception condition using `assertThrows`:")
            for e in self.exception_contracts:
                lines.append(f"  - {e}")

        if self.invariants:
            lines.append("")
            lines.append("### State Invariants (must hold before and after the call):")
            for inv in self.invariants:
                lines.append(f"  - {inv}")

        if self.param_semantics:
            lines.append("")
            lines.append("### Parameter Semantics:")
            for param, desc in self.param_semantics.items():
                lines.append(f"  - `{param}`: {desc}")

        lines.append("")
        lines.append("### Test Generation Strategy based on Contract:")
        lines.append("  1. Happy path: all preconditions satisfied → verify postconditions hold")
        lines.append("  2. Boundary tests: values at the edge of valid ranges")
        lines.append("  3. Violation tests: each precondition violated separately → verify exceptions/error behavior")
        lines.append("  4. Null/empty tests: null inputs, empty collections, zero values")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "method_name":          self.method_name,
            "return_type":          self.return_type,
            "preconditions":        self.preconditions,
            "postconditions":       self.postconditions,
            "exception_contracts":  self.exception_contracts,
            "invariants":           self.invariants,
            "param_semantics":      self.param_semantics,
        }


# ════════════════════════════════════════════════════════════════════
# 合约提取器
# ════════════════════════════════════════════════════════════════════

class ContractExtractor:
    """
    从 Java focal method 源码中静态提取程序合约。

    提取策略（多级，逐级降级）：
    Level 1: Javadoc / 注解（@param, @throws, @return, @pre, @post）
    Level 2: 方法体中的防御性检查（if-throw、Objects.requireNonNull、assert）
    Level 3: 参数类型推断（原始类型、集合类型、String、数组）
    Level 4: 返回类型推断（void/非void、集合返回、boolean返回）
    Level 5: 方法名语义推断（get/set/add/remove/is 前缀）
    """

    # ── 类型 → 前置条件模板 ───────────────────────────────────────
    _TYPE_PRECONDITIONS = {
        "String":       "{name} should not be null; consider also testing empty string \"\"",
        "int":          "{name} must be a valid integer; test with 0, negative values, Integer.MAX_VALUE",
        "long":         "{name} must be a valid long; test with 0L, negative values, Long.MAX_VALUE",
        "double":       "{name} must be a valid double; test with 0.0, NaN, Double.POSITIVE_INFINITY, negative",
        "float":        "{name} must be a valid float; test with 0.0f, Float.NaN, negative values",
        "boolean":      "{name} can be true or false; generate tests for both values",
        "char":         "{name} must be a valid char; test with special characters, whitespace",
        "byte":         "{name} must be in range [Byte.MIN_VALUE, Byte.MAX_VALUE]",
        "short":        "{name} must be in range [Short.MIN_VALUE, Short.MAX_VALUE]",
        "List":         "{name} should not be null; test with empty list, single element, multiple elements",
        "Collection":   "{name} should not be null; test with empty collection and populated collection",
        "Map":          "{name} should not be null; test with empty map and map with entries",
        "Set":          "{name} should not be null; test with empty set and set with elements",
        "Object":       "{name} may be null unless documented otherwise; test null and valid objects",
        "Reader":       "{name} must be a valid, open Reader; test with StringReader for controlled input",
        "InputStream":  "{name} must be a valid, open InputStream; test with ByteArrayInputStream",
        "char[]":       "{name} should not be null; test with empty array and populated array",
    }

    # ── 返回类型 → 后置条件模板 ───────────────────────────────────
    _RETURN_POSTCONDITIONS = {
        "boolean":    "Return value is true or false; assert the specific expected boolean for each scenario",
        "String":     "Return value is a String (may be null or empty based on contract); assert exact value",
        "int":        "Return value is an integer; assert specific expected numeric value for each input",
        "long":       "Return value is a long; assert specific expected numeric value",
        "double":     "Return value is a double; use assertEquals with delta for floating-point comparison",
        "float":      "Return value is a float; use assertEquals with delta for floating-point comparison",
        "List":       "Return value is a List; assert size, content, and order when applicable",
        "Collection": "Return value is a Collection; assert it is not null and has expected size/content",
        "Map":        "Return value is a Map; assert it is not null, check specific key-value pairs",
        "Set":        "Return value is a Set; assert it is not null, check membership of expected elements",
        "Optional":   "Return value is Optional; use assertTrue(result.isPresent()) or assertFalse",
        "void":       "No return value; verify side effects: state changes, file writes, listener callbacks",
    }

    # ── 方法名前缀 → 语义推断 ─────────────────────────────────────
    _METHOD_PREFIX_SEMANTICS = {
        "get":      ("getter method", ["Returns the current value of a field; test after setting it",
                                        "Return value should reflect the object's internal state"]),
        "set":      ("setter method", ["Sets a field value; verify via corresponding getter",
                                        "Test with boundary values and null (if type allows)"]),
        "is":       ("boolean query", ["Returns true or false based on object state",
                                        "Test both conditions that return true and false"]),
        "has":      ("existence check", ["Returns true if element exists, false otherwise",
                                          "Test with existing and non-existing elements"]),
        "add":      ("collection add", ["Adds element to collection; verify size increases by 1",
                                         "Verify added element can be retrieved"]),
        "remove":   ("collection remove", ["Removes element from collection; verify size decreases",
                                             "Test removing non-existing element"]),
        "contains": ("membership check", ["Returns true if element is present",
                                           "Test with present and absent elements"]),
        "parse":    ("parsing method", ["Parses input into structured form; test valid/invalid formats",
                                         "Test with null, empty, malformed input"]),
        "read":     ("read method", ["Reads data from source; test end-of-stream condition (returns -1 or EOF)",
                                      "Test reading from empty source and partially-read source"]),
        "write":    ("write method", ["Writes data to target; verify written content",
                                       "Test writing empty data and large data"]),
        "format":   ("format method", ["Formats data according to pattern; test with valid/invalid patterns",
                                         "Test with null input and edge-case values"]),
        "validate": ("validation method", ["Validates input; test with valid input (no exception) and invalid",
                                             "Each validation rule should have its own test"]),
        "create":   ("factory method", ["Creates new instance; verify returned object is not null",
                                          "Verify created object has expected initial state"]),
        "build":    ("builder method", ["Builds object; verify all configured properties are reflected",
                                          "Test with minimal and maximal configuration"]),
        "compare":  ("comparison method", ["Returns negative/zero/positive; test all three outcomes",
                                              "Test reflexivity: compare(a, a) == 0"]),
        "equals":   ("equality check", ["Returns true if equal; test reflexivity, symmetry, null",
                                          "Test with equal and unequal objects"]),
        "encode":   ("encoding method", ["Encodes data; verify encoded result can be decoded back",
                                           "Test with special characters and empty input"]),
        "decode":   ("decoding method", ["Decodes data; verify result matches original",
                                           "Test with invalid encoded data"]),
        "reset":    ("reset method", ["Resets internal state; verify object returns to initial state",
                                        "Verify all fields are reset, not just some"]),
    }

    def extract(
        self,
        source_code: str,
        method_name: str,
        parameters: str = "",
        return_type: str = "",
        class_name: str = "",
        class_fields: str = "",
        javadoc: str = "",
    ) -> MethodContract:
        """
        主入口：从 focal method 源码中提取完整合约。

        Parameters
        ----------
        source_code  : focal method 完整源码（含签名和方法体）
        method_name  : 方法名（如 'read', 'getLineNumber'）
        parameters   : 参数字符串（如 'char[] buf, int offset, int len'）
        return_type  : 返回类型（如 'int', 'String', 'List<String>'）
        class_name   : 所在类名（辅助推断构造函数合约）
        class_fields : 类字段列表（辅助推断不变量）
        javadoc      : 方法的 Javadoc 注释（如果能单独提取）
        """
        contract = MethodContract(
            method_name=method_name,
            return_type=return_type,
        )

        # Level 1: 从 Javadoc 和注释提取
        self._extract_from_javadoc(source_code, javadoc, contract)

        # Level 2: 从防御性检查提取
        self._extract_from_defensive_checks(source_code, contract)

        # Level 3: 从参数类型推断前置条件
        self._extract_from_param_types(parameters, contract)

        # Level 4: 从返回类型推断后置条件
        self._extract_from_return_type(return_type, contract)

        # Level 5: 从方法名语义推断
        self._extract_from_method_name(method_name, return_type, contract)

        # Level 6: 从字段推断不变量（如果字段信息可用）
        if class_fields:
            self._extract_invariants_from_fields(class_fields, source_code, contract)

        # 去重
        contract.preconditions     = _dedup(contract.preconditions)
        contract.postconditions    = _dedup(contract.postconditions)
        contract.exception_contracts = _dedup(contract.exception_contracts)
        contract.invariants        = _dedup(contract.invariants)

        return contract

    # ── Level 1: Javadoc 解析 ────────────────────────────────────

    def _extract_from_javadoc(self, source_code: str, external_javadoc: str,
                               contract: MethodContract):
        """从 Javadoc 注释提取 @param, @throws, @return 信息。"""
        # 合并源码内的注释和外部传入的 javadoc
        combined = (external_javadoc or "") + "\n" + (source_code or "")

        # 提取 /** ... */ 块
        javadoc_blocks = re.findall(r'/\*\*(.*?)\*/', combined, re.DOTALL)
        for block in javadoc_blocks:
            lines = [l.strip().lstrip('*').strip() for l in block.splitlines()]
            for line in lines:
                # @param
                pm = re.match(r'@param\s+(\w+)\s+(.*)', line)
                if pm:
                    param_name, desc = pm.group(1), pm.group(2).strip()
                    if desc:
                        contract.param_semantics[param_name] = desc
                        # 从描述中推断前置条件
                        if any(kw in desc.lower() for kw in ['must', 'should', 'cannot', 'not null', 'positive', 'non-negative']):
                            contract.preconditions.append(f"`{param_name}`: {desc}")

                # @throws / @exception
                tm = re.match(r'@(?:throws?|exception)\s+(\w+)\s+(.*)', line)
                if tm:
                    exc_type, desc = tm.group(1), tm.group(2).strip()
                    contract.exception_contracts.append(
                        f"{exc_type} is thrown when: {desc or '(see source)'}"
                    )

                # @return
                rm = re.match(r'@return\s+(.*)', line)
                if rm:
                    desc = rm.group(1).strip()
                    if desc:
                        contract.postconditions.append(f"Return value: {desc}")

                # @pre / @post (custom tags)
                pre_m = re.match(r'@pre\s+(.*)', line)
                if pre_m:
                    contract.preconditions.append(pre_m.group(1).strip())
                post_m = re.match(r'@post\s+(.*)', line)
                if post_m:
                    contract.postconditions.append(post_m.group(1).strip())

        # 单行注释中的 precondition hints
        inline_comments = re.findall(r'//\s*(.*)', source_code)
        for comment in inline_comments:
            lower = comment.lower()
            if any(kw in lower for kw in ['precondition', 'require', 'assert that', 'must be']):
                contract.preconditions.append(comment.strip())
            elif any(kw in lower for kw in ['postcondition', 'ensure', 'guarantees']):
                contract.postconditions.append(comment.strip())

    # ── Level 2: 防御性检查分析 ──────────────────────────────────

    def _extract_from_defensive_checks(self, source_code: str, contract: MethodContract):
        """
        分析方法体中的防御性编程模式，提取隐式前置条件。

        模式：
          - if (x == null) throw new ...
          - if (x < 0) throw new ...
          - Objects.requireNonNull(x)
          - assert x != null
          - Preconditions.checkArgument(...)
        """
        if not source_code:
            return

        # 1) Objects.requireNonNull(param)
        for m in re.finditer(r'Objects\.requireNonNull\s*\(\s*(\w+)', source_code):
            param = m.group(1)
            contract.preconditions.append(
                f"`{param}` must not be null (verified by Objects.requireNonNull)"
            )

        # 2) if (...) throw new XxxException(...)
        throw_patterns = re.finditer(
            r'if\s*\(([^)]+)\)\s*(?:\{[^}]*\})?\s*throw\s+new\s+(\w+)',
            source_code, re.DOTALL
        )
        for m in throw_patterns:
            condition, exc_type = m.group(1).strip(), m.group(2).strip()
            # 前置条件：条件的反面
            contract.exception_contracts.append(
                f"{exc_type} thrown when `{condition}` is true"
            )
            # 从条件推断参数约束
            if 'null' in condition:
                param_m = re.search(r'(\w+)\s*==\s*null', condition)
                if param_m:
                    contract.preconditions.append(
                        f"`{param_m.group(1)}` must not be null"
                    )
            if '< 0' in condition or 'negative' in condition.lower():
                param_m = re.search(r'(\w+)\s*<\s*0', condition)
                if param_m:
                    contract.preconditions.append(
                        f"`{param_m.group(1)}` must be non-negative (≥ 0)"
                    )
            if '<= 0' in condition:
                param_m = re.search(r'(\w+)\s*<=\s*0', condition)
                if param_m:
                    contract.preconditions.append(
                        f"`{param_m.group(1)}` must be positive (> 0)"
                    )
            if 'isEmpty' in condition or 'length() == 0' in condition:
                param_m = re.search(r'(\w+)\.isEmpty', condition)
                if param_m:
                    contract.preconditions.append(
                        f"`{param_m.group(1)}` must not be empty"
                    )

        # 3) Preconditions.checkArgument / checkNotNull (Guava style)
        for m in re.finditer(r'Preconditions\.check\w+\s*\(([^,)]+)', source_code):
            condition = m.group(1).strip()
            contract.preconditions.append(f"Guava precondition: `{condition}` must hold")

        # 4) assert 语句
        for m in re.finditer(r'\bassert\s+([^;]+);', source_code):
            assertion = m.group(1).strip()
            if len(assertion) < 100:  # 过滤太长的断言
                contract.preconditions.append(f"Internal assert: `{assertion}` must hold")

        # 5) 范围检查模式 (offset, length, index)
        range_check = re.search(
            r'if\s*\(\s*(\w+)\s*[<>]=?\s*(\w+\.length|this\.\w+|\d+)', source_code)
        if range_check:
            contract.preconditions.append(
                "Array/buffer offset and length parameters must be within valid bounds"
            )

        # 6) 状态检查（isClosed、isOpen 等）
        state_checks = re.findall(r'if\s*\(\s*(is\w+|!\s*is\w+)\s*\)', source_code)
        for sc in state_checks:
            if 'Closed' in sc or 'Open' in sc or 'Ready' in sc:
                contract.preconditions.append(
                    f"Object must be in valid state: `{sc.strip()}` check in method body"
                )

    # ── Level 3: 参数类型推断 ────────────────────────────────────

    def _extract_from_param_types(self, parameters: str, contract: MethodContract):
        """根据参数类型和名称推断前置条件。"""
        if not parameters:
            return

        # 解析参数列表（支持泛型、数组）
        # 去掉 final 关键字，分割参数
        params_clean = re.sub(r'\bfinal\b', '', parameters).strip()
        # 简单拆分（以逗号分割，但要处理泛型 <...> 中的逗号）
        param_list = _split_params(params_clean)

        for param_str in param_list:
            param_str = param_str.strip()
            if not param_str:
                continue

            # 提取类型和名称
            parts = param_str.rsplit(None, 1)
            if len(parts) < 2:
                continue
            param_type = parts[0].strip()
            param_name = parts[1].strip().lstrip('...')  # 处理可变参数

            # 存储参数语义
            # 查找基础类型（忽略泛型参数和数组）
            base_type = re.sub(r'<.*?>', '', param_type).replace('[]', '').strip()

            # 从模板生成前置条件
            template = self._TYPE_PRECONDITIONS.get(base_type)
            if template:
                constraint = template.format(name=param_name)
                contract.preconditions.append(constraint)

            # 根据参数名推断语义
            name_lower = param_name.lower()
            if 'offset' in name_lower or 'off' in name_lower:
                contract.preconditions.append(
                    f"`{param_name}` (offset) must be ≥ 0 and < buffer length"
                )
            elif 'length' in name_lower or 'len' in name_lower or 'count' in name_lower:
                contract.preconditions.append(
                    f"`{param_name}` (length/count) must be ≥ 0; test 0 and max valid value"
                )
            elif 'index' in name_lower or 'idx' in name_lower or 'pos' in name_lower:
                contract.preconditions.append(
                    f"`{param_name}` (index) must be ≥ 0 and < collection size"
                )
            elif 'timeout' in name_lower or 'delay' in name_lower:
                contract.preconditions.append(
                    f"`{param_name}` must be positive; test with 0 and negative values"
                )
            elif 'size' in name_lower or 'capacity' in name_lower:
                contract.preconditions.append(
                    f"`{param_name}` must be > 0; test with 0 and negative values"
                )

    # ── Level 4: 返回类型推断 ────────────────────────────────────

    def _extract_from_return_type(self, return_type: str, contract: MethodContract):
        """根据返回类型推断后置条件。"""
        if not return_type or return_type == "void":
            if return_type == "void":
                contract.postconditions.append(
                    "Method has no return value; verify side effects (state changes, exceptions, etc.)"
                )
            return

        # 查找基础类型
        base_type = re.sub(r'<.*?>', '', return_type).replace('[]', '').strip()

        # 从模板生成后置条件
        postcond = self._RETURN_POSTCONDITIONS.get(base_type)
        if postcond:
            contract.postconditions.append(postcond)
        elif base_type not in ('void',):
            contract.postconditions.append(
                f"Return value is of type `{return_type}`; assert it is not null "
                f"(unless documented to return null) and has expected value"
            )

        # 数组返回类型
        if '[]' in return_type:
            contract.postconditions.append(
                f"Return value is an array; assert it is not null and has expected length/content"
            )

    # ── Level 5: 方法名语义推断 ──────────────────────────────────

    def _extract_from_method_name(self, method_name: str, return_type: str,
                                   contract: MethodContract):
        """根据方法名前缀推断语义和合约。"""
        if not method_name:
            return

        for prefix, (semantic, hints) in self._METHOD_PREFIX_SEMANTICS.items():
            if method_name.lower().startswith(prefix):
                for hint in hints:
                    # 区分前置和后置
                    if any(kw in hint.lower() for kw in ['verify', 'assert', 'returns', 'return']):
                        contract.postconditions.append(f"[{semantic}] {hint}")
                    elif any(kw in hint.lower() for kw in ['test', 'generate', 'boundary']):
                        contract.preconditions.append(f"[{semantic}] {hint}")
                    else:
                        contract.postconditions.append(f"[{semantic}] {hint}")
                break

        # 特殊方法名处理
        name_lower = method_name.lower()
        if 'close' in name_lower:
            contract.postconditions.append(
                "After close(), further read/write operations should throw IOException"
            )
            contract.exception_contracts.append(
                "Calling close() multiple times should be idempotent (no exception on second close)"
            )
        elif 'open' in name_lower or 'connect' in name_lower:
            contract.postconditions.append(
                "After successful open/connect, the resource should be usable"
            )
        elif 'toString' in method_name:
            contract.postconditions.append(
                "Return value must not be null; should represent the object's state meaningfully"
            )
        elif 'hashCode' in method_name:
            contract.postconditions.append(
                "Objects equal by equals() must have the same hashCode; consistent across calls"
            )
        elif 'compareTo' in method_name:
            contract.postconditions.append(
                "compareTo(self) must return 0; result must be antisymmetric"
            )
            contract.exception_contracts.append(
                "NullPointerException when argument is null (standard Comparable contract)"
            )

    # ── Level 6: 字段不变量推断 ──────────────────────────────────

    def _extract_invariants_from_fields(self, class_fields: str,
                                         source_code: str, contract: MethodContract):
        """从类字段推断状态不变量。"""
        if not class_fields:
            return

        # 检查方法是否修改了字段
        field_names = re.findall(r'\b(\w+)\s*;', class_fields)
        modified_fields = []
        for fname in field_names:
            if re.search(rf'\bthis\.{fname}\s*=', source_code) or \
               re.search(rf'\b{fname}\s*[+\-*/%]?=', source_code):
                modified_fields.append(fname)

        if modified_fields:
            contract.invariants.append(
                f"Modified fields in this method: {', '.join(modified_fields)}; "
                f"verify their values before and after the call"
            )


# ════════════════════════════════════════════════════════════════════
# 工具函数
# ════════════════════════════════════════════════════════════════════

def _dedup(lst: list) -> list:
    """保序去重。"""
    seen, result = set(), []
    for item in lst:
        key = item.strip().lower()[:80]
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def _split_params(params_str: str) -> list:
    """
    按顶层逗号分割参数字符串，正确处理泛型中的逗号。
    例：'Map<String, Integer> m, int n' → ['Map<String, Integer> m', 'int n']
    """
    result, depth, current = [], 0, []
    for char in params_str:
        if char == '<':
            depth += 1
            current.append(char)
        elif char == '>':
            depth -= 1
            current.append(char)
        elif char == ',' and depth == 0:
            result.append(''.join(current).strip())
            current = []
        else:
            current.append(char)
    if current:
        result.append(''.join(current).strip())
    return result