"""
llm_client.py
=============
统一封装 Generator (闭源) 和 Refiner Agent (开/本地) 的 LLM HTTP 调用。
- 支持 OpenAI 兼容接口 (OpenAI / Ollama / 其他)
- 记录每次调用的 prompt_tokens / completion_tokens / elapsed_time_seconds
- chat_json() 支持强制 JSON 输出模式 (json_mode=True)
"""
from __future__ import annotations

import json
import logging
import time
from typing import Dict, List, Optional, Tuple
from config import *
import requests

logger = logging.getLogger(__name__)

# 429 限速时的基础等待秒数（每次重试翻倍）
RATE_LIMIT_BASE_SLEEP = 20   # seconds
RATE_LIMIT_MAX_SLEEP  = 180  # seconds cap


def _rate_limit_sleep(attempt: int, client_name: str = "LLM"):
    """在收到 429 时进行指数退避睡眠，并打印提示。"""
    sleep_sec = min(RATE_LIMIT_BASE_SLEEP * (2 ** (attempt - 1)), RATE_LIMIT_MAX_SLEEP)
    print(
        f"\n⏳ [{client_name}] 触发 API 限速 (429)，"
        f"第 {attempt} 次重试前等待 {sleep_sec}s ...",
        flush=True
    )
    logger.warning("[%s] 429 rate limit hit (attempt %d), sleeping %ds", client_name, attempt, sleep_sec)
    time.sleep(sleep_sec)


class LLMCallResult:
    """单次 LLM 调用结果 + 耗时/Token 统计。"""
    def __init__(self, content: str, prompt_tokens: int,
                 completion_tokens: int, elapsed_seconds: float):
        self.content           = content
        self.prompt_tokens     = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens      = prompt_tokens + completion_tokens
        self.elapsed_seconds   = elapsed_seconds

    def to_usage_dict(self) -> dict:
        return {
            "prompt_tokens":      self.prompt_tokens,
            "completion_tokens":  self.completion_tokens,
            "total_tokens":       self.total_tokens,
            "llm_elapsed_time_seconds": round(self.elapsed_seconds, 3),
        }


class LLMClient:
    """通用 OpenAI-compatible LLM 客户端。"""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str = "https://api.openai.com/v1",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: int = 120,
        max_retries: int = 3,
        name: str = "LLM",
    ):
        self.api_key     = api_key
        self.model       = model
        self.base_url    = base_url.rstrip("/").strip('"')  
        self.temperature = temperature
        self.max_tokens  = max_tokens
        self.timeout     = timeout
        self.max_retries = max_retries
        self.name        = name

    # ── 核心调用 ──────────────────────────────────────────────────────
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
    ) -> LLMCallResult:
        """
        发送 chat/completions 请求，返回 LLMCallResult。
        包含 token 统计和耗时。
        遇到 429 时强制指数退避睡眠后重试，不会快速失败。
        """
        payload: Dict = {
            "model":       self.model,
            "messages":    messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens":  max_tokens  if max_tokens  is not None else self.max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Content-Type":  "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        url = f"{self.base_url}/chat/completions"

        last_error = None
        for attempt in range(1, self.max_retries + 1):
            print(f"  ⏳ [{self.name}] 正在进行频率控制，休眠 3s...", flush=True)
            time.sleep(10)
            t0 = time.time()
            try:
                resp = requests.post(url, headers=headers,
                                     json=payload, timeout=self.timeout)

                # ── 429: 限速，强制睡眠后重试 ──────────────────────
                if resp.status_code == 429:
                    last_error = f"429 Too Many Requests"
                    # time.sleep(10)
                    _rate_limit_sleep(attempt, self.name)
                    print(f"  ⚠️  [{self.name}] 触发 429 限速，准备进行第 {attempt}/{self.max_retries} 次重试...", flush=True)
                    continue

                resp.raise_for_status()
                data    = resp.json()
                elapsed = time.time() - t0

                content = data["choices"][0]["message"]["content"]
                usage   = data.get("usage", {})
                pt = usage.get("prompt_tokens",     0)
                ct = usage.get("completion_tokens", 0)
                # 若接口不返回 usage，降级估算
                if pt == 0:
                    pt = sum(len(m["content"]) // 4 for m in messages)
                if ct == 0:
                    ct = len(content) // 4

                logger.debug("[%s] tokens=%d+%d elapsed=%.2fs",
                             self.name, pt, ct, elapsed)
                print(
                    f"  ✅ [{self.name}] OK | "
                    f"tokens={pt}+{ct} | elapsed={elapsed:.1f}s",
                    flush=True
                )
                return LLMCallResult(content, pt, ct, elapsed)

            except requests.exceptions.Timeout:
                last_error = "timeout"
                logger.warning("[%s] attempt %d timeout", self.name, attempt)
                print(f"  ⚠️  [{self.name}] 超时 (attempt {attempt}/{self.max_retries})，重试中...", flush=True)
                time.sleep(5)

            except requests.exceptions.HTTPError as e:
                status_code = getattr(e.response, 'status_code', 0) if hasattr(e, 'response') else 0
                last_error = str(e)
                logger.warning("[%s] HTTP error: %s", self.name, e)
                if status_code == 429:
                    # 也有可能在 raise_for_status() 前被捕获
                    _rate_limit_sleep(attempt, self.name)
                    # time.sleep(10)
                    print(f"  ⚠️  [{self.name}] 触发 429 限速，准备进行第 {attempt}/{self.max_retries} 次重试...", flush=True)
                    continue
                if status_code in (400, 401, 403):
                    print(f"  ❌ [{self.name}] 认证/请求错误 {status_code}: {e}", flush=True)
                    raise
                # 其他 5xx 等，短暂等待后重试
                sleep_s = min(5 * attempt, 30)
                print(f"  ⚠️  [{self.name}] HTTP {status_code} 错误，{sleep_s}s 后重试...", flush=True)
                time.sleep(sleep_s)

            except Exception as e:
                last_error = str(e)
                logger.warning("[%s] attempt %d error: %s", self.name, attempt, e)
                print(f"  ⚠️  [{self.name}] 未知错误 (attempt {attempt}): {e}", flush=True)
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)

        elapsed = 0.0
        print(f"  ❌ [{self.name}] 全部 {self.max_retries} 次重试失败: {last_error}", flush=True)
        return LLMCallResult(
            content=f"[LLM_ERROR] {self.name}: {last_error}",
            prompt_tokens=0, completion_tokens=0, elapsed_seconds=elapsed
        )

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
    ) -> Tuple[dict, LLMCallResult]:
        """
        调用 chat() 并解析 JSON 响应。
        返回 (parsed_dict, LLMCallResult)
        """
        result = self.chat(messages, temperature=temperature, json_mode=True)
        raw = result.content.strip()
        # 去掉 ```json ... ``` 包裹
        if raw.startswith("```"):
            parts = raw.split("```")
            for i, p in enumerate(parts):
                if i % 2 == 1:
                    raw = p.lstrip("json").strip()
                    break
        raw = raw.strip("`").strip()
        try:
            return json.loads(raw), result
        except json.JSONDecodeError as e:
            logger.error("[%s] JSON parse error: %s\nraw=%s", self.name, e, raw[:400])
            return {}, result


# ── 工厂函数 ──────────────────────────────────────────────────────────

def make_generator_client() -> LLMClient:
    from config import GEN_API_KEY, GEN_MODEL, GEN_BASE_URL, GEN_TEMPERATURE, GEN_MAX_TOKENS
    return LLMClient(
        api_key=GEN_API_KEY, model=GEN_MODEL, base_url=GEN_BASE_URL,
        temperature=GEN_TEMPERATURE, max_tokens=GEN_MAX_TOKENS,
        max_retries=3, name="Generator",
    )

def make_refiner_client() -> LLMClient:
    from config import REF_API_KEY, REF_MODEL, REF_BASE_URL, REF_TEMPERATURE, REF_MAX_TOKENS
    return LLMClient(
        api_key=REF_API_KEY, model=REF_MODEL, base_url=REF_BASE_URL,
        temperature=REF_TEMPERATURE, max_tokens=REF_MAX_TOKENS,
        max_retries=3, name="Refiner",
    )