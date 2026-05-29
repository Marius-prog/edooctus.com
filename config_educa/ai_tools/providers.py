"""Pluggable provider interface for LLMs.

Providers:
    FakeProvider       \u2014 deterministic echo, used in tests / offline mode.
    OpenAIProvider     \u2014 real OpenAI Chat Completions (gpt-4o etc.).
    AnthropicProvider  \u2014 real Anthropic Messages (claude-3.5-sonnet etc.).

Selection rules (in `get_provider`):
    1. If `AITool.provider == 'openai'` and OPENAI_API_KEY is set \u2192 OpenAIProvider
    2. If `AITool.provider == 'anthropic'` and ANTHROPIC_API_KEY is set \u2192 AnthropicProvider
    3. Otherwise \u2192 FakeProvider (so the platform never hard-crashes on missing keys).

Cost estimation: rough per-1K-token rates baked into PROVIDER_RATES below.
Override per-tool by setting `AITool.default_model` to a known key in the rate table.
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass

from django.conf import settings

log = logging.getLogger(__name__)

# Per-1K-token rates in micros of USD (1 USD = 1_000_000 micros).
PROVIDER_RATES: dict[str, tuple[int, int]] = {
    # (input_per_1k, output_per_1k) in micros
    "gpt-4o-mini": (150, 600),
    "gpt-4o": (5_000, 15_000),
    "claude-3-5-sonnet-20241022": (3_000, 15_000),
    "claude-3-5-haiku-20241022": (800, 4_000),
    "echo": (0, 0),
}


@dataclass
class ProviderResponse:
    text: str
    model: str
    tokens_input: int = 0
    tokens_output: int = 0
    cost_micros: int = 0
    latency_ms: int = 0


def _estimate_cost(model: str, tokens_in: int, tokens_out: int) -> int:
    rin, rout = PROVIDER_RATES.get(model, (0, 0))
    return (tokens_in * rin + tokens_out * rout) // 1000


class FakeProvider:
    """Deterministic provider used in tests and the offline sandbox."""

    def call(self, prompt: str, model: str | None = None, **kwargs) -> ProviderResponse:
        t0 = time.perf_counter()
        text = f"[fake:{model or 'echo'}] " + prompt[:200]
        latency = int((time.perf_counter() - t0) * 1000)
        tokens_in = max(1, len(prompt) // 4)
        tokens_out = max(1, len(text) // 4)
        return ProviderResponse(
            text=text, model=model or "echo",
            tokens_input=tokens_in, tokens_output=tokens_out,
            cost_micros=_estimate_cost(model or "echo", tokens_in, tokens_out),
            latency_ms=latency,
        )


class OpenAIProvider:
    """Calls OpenAI Chat Completions. Requires `openai` package + OPENAI_API_KEY."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or getattr(settings, "OPENAI_API_KEY", "") or os.environ.get("OPENAI_API_KEY", "")

    def call(self, prompt: str, model: str | None = None, **kwargs) -> ProviderResponse:
        from openai import OpenAI  # imported lazily so package isn't required at import time
        client = OpenAI(api_key=self.api_key)
        model = model or "gpt-4o-mini"
        t0 = time.perf_counter()
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=kwargs.get("max_tokens", 1024),
            temperature=kwargs.get("temperature", 0.7),
        )
        latency = int((time.perf_counter() - t0) * 1000)
        usage = getattr(resp, "usage", None)
        tin = getattr(usage, "prompt_tokens", 0) or 0
        tout = getattr(usage, "completion_tokens", 0) or 0
        text = resp.choices[0].message.content or ""
        return ProviderResponse(
            text=text, model=model,
            tokens_input=tin, tokens_output=tout,
            cost_micros=_estimate_cost(model, tin, tout),
            latency_ms=latency,
        )


class AnthropicProvider:
    """Calls Anthropic Messages API. Requires `anthropic` package + ANTHROPIC_API_KEY."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or getattr(settings, "ANTHROPIC_API_KEY", "") or os.environ.get("ANTHROPIC_API_KEY", "")

    def call(self, prompt: str, model: str | None = None, **kwargs) -> ProviderResponse:
        from anthropic import Anthropic  # lazy import
        client = Anthropic(api_key=self.api_key)
        model = model or "claude-3-5-haiku-20241022"
        t0 = time.perf_counter()
        resp = client.messages.create(
            model=model,
            max_tokens=kwargs.get("max_tokens", 1024),
            messages=[{"role": "user", "content": prompt}],
        )
        latency = int((time.perf_counter() - t0) * 1000)
        # Anthropic returns content as list of blocks
        text_parts = [b.text for b in resp.content if getattr(b, "type", "") == "text"]
        text = "".join(text_parts)
        usage = getattr(resp, "usage", None)
        tin = getattr(usage, "input_tokens", 0) or 0
        tout = getattr(usage, "output_tokens", 0) or 0
        return ProviderResponse(
            text=text, model=model,
            tokens_input=tin, tokens_output=tout,
            cost_micros=_estimate_cost(model, tin, tout),
            latency_ms=latency,
        )


def get_provider(tool) -> "FakeProvider | OpenAIProvider | AnthropicProvider":
    """Factory: pick the right provider for an AITool, falling back to fake."""
    provider_name = getattr(tool, "provider", "fake")
    try:
        if provider_name == "openai":
            key = getattr(settings, "OPENAI_API_KEY", "")
            if key:
                return OpenAIProvider(api_key=key)
            log.warning("OpenAI key missing \u2014 using FakeProvider for tool=%s", tool)
        elif provider_name == "anthropic":
            key = getattr(settings, "ANTHROPIC_API_KEY", "")
            if key:
                return AnthropicProvider(api_key=key)
            log.warning("Anthropic key missing \u2014 using FakeProvider for tool=%s", tool)
    except ImportError as exc:
        log.warning("Provider SDK not installed (%s) \u2014 falling back to fake", exc)
    return FakeProvider()
