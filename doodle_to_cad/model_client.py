from __future__ import annotations

import base64
import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from .config import Settings


@dataclass
class ModelInfo:
    selected: str | None
    available: list[str]
    source: str
    error: str | None = None


class ReplyCache:
    """Content-addressed reply cache for A/B and replay work.

    Off unless DOODLE_LLM_CACHE names a directory — the product path never
    serves stale replies by accident. Only replies that survived the caller's
    validation (chat raises before storing anything else) are stored, so a
    cache hit is always a syntactically valid prior answer.
    """

    def __init__(self, directory: str | None):
        self.dir = Path(directory) if directory else None
        self.hits = 0
        self.misses = 0

    @staticmethod
    def key(payload: dict[str, Any]) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def get(self, payload: dict[str, Any]) -> str | None:
        if not self.dir:
            return None
        path = self.dir / (self.key(payload) + ".json")
        if not path.exists():
            self.misses += 1
            return None
        try:
            reply = json.loads(path.read_text())["reply"]
        except Exception:
            self.misses += 1
            return None
        self.hits += 1
        return reply

    def put(self, payload: dict[str, Any], reply: str) -> None:
        if not self.dir:
            return
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / (self.key(payload) + ".json")).write_text(json.dumps(
            {"created": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "payload_key": self.key(payload), "reply": reply}))


class CompatibleModelClient:
    """Small OpenAI-compatible client with explicit model provenance."""

    def __init__(self, config: Settings):
        self.config = config
        self._model: ModelInfo | None = None
        self.cache = ReplyCache(getattr(config, "llm_cache_dir", "") or None)

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.config.api_key}"}

    async def discover(self, refresh: bool = False) -> ModelInfo:
        if self._model and not refresh:
            return self._model
        try:
            async with httpx.AsyncClient(timeout=min(self.config.timeout, 20)) as client:
                response = await client.get(f"{self.config.base_url}/models", headers=self.headers)
                response.raise_for_status()
                available = [str(item["id"]) for item in response.json().get("data", []) if item.get("id")]
            requested = self.config.requested_model
            if requested:
                if available and requested not in available:
                    raise RuntimeError(f"OPENAI_MODEL '{requested}' is not listed by the endpoint")
                selected, source = requested, "environment"
            else:
                selected, source = self._choose(available), "auto-discovery"
            if not selected:
                raise RuntimeError("The endpoint returned no models")
            self._model = ModelInfo(selected, available, source)
        except Exception as exc:
            selected = self.config.requested_model or None
            self._model = ModelInfo(selected, [], "environment-fallback" if selected else "unavailable", str(exc))
        return self._model

    @staticmethod
    def _choose(models: list[str]) -> str | None:
        # Prefer IDs that commonly signal multimodal capability, then preserve server order.
        hints = ("vl", "vision", "omni", "qwen2.5-vl", "qwen3-vl", "gemma-3", "pixtral", "llava")
        return next((m for m in models if any(h in m.lower() for h in hints)), models[0] if models else None)

    async def chat(self, messages: list[dict[str, Any]], temperature: float = 0.15,
                   enable_thinking: bool | None = None, max_tokens: int | None = None) -> str:
        info = await self.discover()
        if not info.selected:
            raise RuntimeError(info.error or "No model is available")
        template_options = {
            "enable_thinking": self.config.enable_thinking if enable_thinking is None else enable_thinking,
        }
        if template_options["enable_thinking"] and self.config.thinking_budget > 0:
            template_options["thinking_budget"] = self.config.thinking_budget
        payload = {
            "model": info.selected, "messages": messages, "temperature": temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
            "chat_template_kwargs": template_options,
        }
        cached = self.cache.get(payload)
        if cached is not None:
            return cached
        content = await self._post_chat(payload)
        self.cache.put(payload, content)
        return content

    async def _post_chat(self, payload: dict[str, Any]) -> str:
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(f"{self.config.base_url}/chat/completions", headers=self.headers, json=payload)
            response.raise_for_status()
            body = response.json()
            choice = body["choices"][0]
            message = choice.get("message") or {}
            content = message.get("content") or choice.get("text")
            if not content:
                reason = choice.get("finish_reason") or "unknown"
                reasoning = message.get("reasoning") or message.get("reasoning_content") or ""
                detail = f" The model produced {len(reasoning)} reasoning characters but no final answer." if reasoning else ""
                raise RuntimeError(f"Model returned no final content (finish_reason={reason}).{detail}")
            return str(content)

    def cache_stats(self) -> dict[str, Any]:
        return {"enabled": bool(self.cache.dir), "dir": str(self.cache.dir) if self.cache.dir else None,
                "hits": self.cache.hits, "misses": self.cache.misses}

    @staticmethod
    def image_url(data: bytes, mime: str) -> str:
        return f"data:{mime};base64,{base64.b64encode(data).decode()}"


def extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        if text.lstrip().startswith("json"):
            text = text.lstrip()[4:].lstrip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("Model did not return a JSON object")
    return json.loads(text[start:end + 1])
