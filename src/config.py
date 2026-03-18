"""config.py — 读取 config/config.ini（与 ChatUniTest 完全兼容，增加 [generator]/[refiner] 两节）"""
import configparser
import os

_CFG = configparser.ConfigParser()
_CFG.read(os.path.join(os.path.dirname(__file__), "../config/config.ini"))

# ── ChatUniTest 原有参数（保持不变）────────────────────────────────────
process_number    = int(_CFG.get("DEFAULT", "process_number",    fallback="8"))
test_number       = int(_CFG.get("DEFAULT", "test_number",       fallback="5"))
max_rounds        = int(_CFG.get("DEFAULT", "max_rounds",        fallback="3"))
MAX_PROMPT_TOKENS = int(_CFG.get("DEFAULT", "MAX_PROMPT_TOKENS", fallback="3000"))
MIN_ERROR_TOKENS  = int(_CFG.get("DEFAULT", "MIN_ERROR_TOKENS",  fallback="500"))
TIMEOUT           = int(_CFG.get("DEFAULT", "TIMEOUT",           fallback="30"))

TEMPLATE_NO_DEPS  = _CFG.get("DEFAULT", "PROMPT_TEMPLATE_NO_DEPS",  fallback="d1_4.jinja2")
TEMPLATE_WITH_DEPS= _CFG.get("DEFAULT", "PROMPT_TEMPLATE_DEPS",     fallback="d3_4.jinja2")
TEMPLATE_REFINE   = _CFG.get("DEFAULT", "PROMPT_TEMPLATE_REFINE",   fallback="refine_agent.jinja2")
TEMPLATE_FIX      = _CFG.get("DEFAULT", "PROMPT_TEMPLATE_FIX",      fallback="refine_fix.jinja2")

LANGUAGE     = _CFG.get("DEFAULT", "LANGUAGE",     fallback="java")
GRAMMAR_FILE = _CFG.get("DEFAULT", "GRAMMAR_FILE", fallback="")
COBERTURA_DIR= _CFG.get("DEFAULT", "COBERTURA_DIR",fallback="./dependencies/cobertura-2.1.1")
JUNIT_JAR    = _CFG.get("DEFAULT", "JUNIT_JAR",    fallback="")
MOCKITO_JAR  = _CFG.get("DEFAULT", "MOCKITO_JAR",  fallback="")
LOG4J_JAR    = _CFG.get("DEFAULT", "LOG4J_JAR",    fallback="")
JACOCO_AGENT = _CFG.get("DEFAULT", "JACOCO_AGENT", fallback="")
JACOCO_CLI   = _CFG.get("DEFAULT", "JACOCO_CLI",   fallback="")
REPORT_FORMAT= _CFG.get("DEFAULT", "REPORT_FORMAT",fallback="xml")

# ★ 注意：这三个路径在 ChatUniTest 中均来自 config.ini，我们保持相同
dataset_dir  = _CFG.get("DEFAULT", "dataset_dir",  fallback="../dataset_batch/")
result_dir   = _CFG.get("DEFAULT", "result_dir",   fallback="../results_batch/")
project_dir  = _CFG.get("DEFAULT", "project_dir",  fallback="../defect4j_projects/")

# ── 新增：Generator LLM（闭源，负责生成/精修 Test）────────────────────
GEN_PROVIDER    = _CFG.get("generator", "provider",     fallback="openai")
GEN_API_KEY     = _CFG.get("generator", "api_key",      fallback="")
GEN_MODEL       = _CFG.get("generator", "model",        fallback="gpt-4o")
GEN_TEMPERATURE = float(_CFG.get("generator", "temperature", fallback="0.7"))
GEN_MAX_TOKENS  = int(_CFG.get("generator",  "max_tokens",   fallback="4096"))
GEN_BASE_URL    = _CFG.get("generator", "base_url",     fallback="https://api.openai.com/v1")

# ── 新增：Refiner Agent LLM（开源/本地，负责评估 + 指令生成）───────────
REF_PROVIDER    = _CFG.get("refiner", "provider",     fallback="openai")
REF_API_KEY     = _CFG.get("refiner", "api_key",      fallback="")
REF_MODEL       = _CFG.get("refiner", "model",        fallback="gpt-4o-mini")
REF_TEMPERATURE = float(_CFG.get("refiner", "temperature", fallback="0.2"))
REF_MAX_TOKENS  = int(_CFG.get("refiner",  "max_tokens",   fallback="4096"))
REF_BASE_URL    = _CFG.get("refiner", "base_url",     fallback="https://api.openai.com/v1")
