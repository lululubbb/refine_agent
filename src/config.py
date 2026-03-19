"""config.py — 读取 config/config.ini（与 ChatUniTest 完全兼容，增加 [generator]/[refiner] 两节）"""
import configparser
import os

config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), "../config/config.ini"))

# ── ChatUniTest 原有参数（保持不变）────────────────────────────────────
process_number    = int(config.get("DEFAULT", "process_number",    fallback="8"))
test_number       = int(config.get("DEFAULT", "test_number",       fallback="5"))
max_rounds        = int(config.get("DEFAULT", "max_rounds",        fallback="3"))
MAX_PROMPT_TOKENS = int(config.get("DEFAULT", "MAX_PROMPT_TOKENS", fallback="3000"))
MIN_ERROR_TOKENS  = int(config.get("DEFAULT", "MIN_ERROR_TOKENS",  fallback="500"))
TIMEOUT           = int(config.get("DEFAULT", "TIMEOUT",           fallback="30"))

TEMPLATE_NO_DEPS  = config.get("DEFAULT", "PROMPT_TEMPLATE_NO_DEPS",  fallback="d1_4.jinja2")
TEMPLATE_WITH_DEPS= config.get("DEFAULT", "PROMPT_TEMPLATE_DEPS",     fallback="d3_4.jinja2")
TEMPLATE_REFINE   = config.get("DEFAULT", "PROMPT_TEMPLATE_REFINE",   fallback="refine_agent.jinja2")
TEMPLATE_FIX      = config.get("DEFAULT", "PROMPT_TEMPLATE_FIX",      fallback="refine_fix.jinja2")

LANGUAGE     = config.get("DEFAULT", "LANGUAGE",     fallback="java")
GRAMMAR_FILE = config.get("DEFAULT", "GRAMMAR_FILE", fallback="")
COBERTURA_DIR= config.get("DEFAULT", "COBERTURA_DIR",fallback="./dependencies/cobertura-2.1.1")
JUNIT_JAR    = config.get("DEFAULT", "JUNIT_JAR",    fallback="")
MOCKITO_JAR  = config.get("DEFAULT", "MOCKITO_JAR",  fallback="")
LOG4J_JAR    = config.get("DEFAULT", "LOG4J_JAR",    fallback="")
JACOCO_AGENT = config.get("DEFAULT", "JACOCO_AGENT", fallback="")
JACOCO_CLI   = config.get("DEFAULT", "JACOCO_CLI",   fallback="")
REPORT_FORMAT= config.get("DEFAULT", "REPORT_FORMAT",fallback="xml")

# ★ 注意：这三个路径在 ChatUniTest 中均来自 config.ini，我们保持相同
dataset_dir  = config.get("DEFAULT", "dataset_dir",  fallback="../dataset_batch/")
result_dir   = config.get("DEFAULT", "result_dir",   fallback="../results_batch/")
project_dir  = config.get("DEFAULT", "project_dir",  fallback="../defect4j_projects/")

# ── 新增：Generator LLM（闭源，负责生成/精修 Test）────────────────────
GEN_PROVIDER    = config.get("generator", "provider",     fallback="openai")
GEN_API_KEY     = config.get("generator", "api_key",      fallback="")
GEN_MODEL       = config.get("generator", "model",        fallback="gpt-4o")
GEN_TEMPERATURE = float(config.get("generator", "temperature", fallback="0.7"))
GEN_MAX_TOKENS  = int(config.get("generator",  "max_tokens",   fallback="4096"))
GEN_BASE_URL    = config.get("generator", "base_url",     fallback="https://api.openai.com/v1")

# ── 新增：Refiner Agent LLM（开源/本地，负责评估 + 指令生成）───────────
REF_PROVIDER    = config.get("refiner", "provider",     fallback="openai")
REF_API_KEY     = config.get("refiner", "api_key",      fallback="")
REF_MODEL       = config.get("refiner", "model",        fallback="gpt-4o-mini")
REF_TEMPERATURE = float(config.get("refiner", "temperature", fallback="0.2"))
REF_MAX_TOKENS  = int(config.get("refiner",  "max_tokens",   fallback="4096"))
REF_BASE_URL    = config.get("refiner", "base_url",     fallback="https://api.openai.com/v1")
