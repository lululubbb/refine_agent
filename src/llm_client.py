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

import requests

logger = logging.getLogger(__name__)


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
        self.base_url    = base_url.rstrip("/")
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
            t0 = time.time()
            try:
                resp = requests.post(url, headers=headers,
                                     json=payload, timeout=self.timeout)
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
                return LLMCallResult(content, pt, ct, elapsed)

            except requests.exceptions.Timeout:
                last_error = "timeout"
                logger.warning("[%s] attempt %d timeout", self.name, attempt)
            except requests.exceptions.HTTPError as e:
                last_error = str(e)
                logger.warning("[%s] HTTP error: %s", self.name, e)
                if resp.status_code in (400, 401, 403):
                    raise
            except Exception as e:
                last_error = str(e)
                logger.warning("[%s] attempt %d error: %s", self.name, attempt, e)

            if attempt < self.max_retries:
                time.sleep(2 ** attempt)

        elapsed = 0.0
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
        temperature=GEN_TEMPERATURE, max_tokens=GEN_MAX_TOKENS, name="Generator",
    )

def make_refiner_client() -> LLMClient:
    from config import REF_API_KEY, REF_MODEL, REF_BASE_URL, REF_TEMPERATURE, REF_MAX_TOKENS
    return LLMClient(
        api_key=REF_API_KEY, model=REF_MODEL, base_url=REF_BASE_URL,
        temperature=REF_TEMPERATURE, max_tokens=REF_MAX_TOKENS, name="Refiner",
    )
