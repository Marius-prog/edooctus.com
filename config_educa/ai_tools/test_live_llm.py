"""End-to-end smoke tests against real OpenAI + Anthropic APIs.

Disabled by default. Enable with:

    RUN_LIVE_LLM_TESTS=1 \
    OPENAI_API_KEY=sk-... \
    ANTHROPIC_API_KEY=sk-ant-... \
    python manage.py test ai_tools.test_live_llm

Costs: ~$0.001 per test (uses cheapest models, short prompts, low max_tokens).
"""
import os
import unittest

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from .models import AITool
from .providers import (
    AnthropicProvider, FakeProvider, OpenAIProvider,
    get_provider, ProviderResponse,
)
from .services import run_prompt


_LIVE = os.environ.get("RUN_LIVE_LLM_TESTS") == "1"
_HAS_OPENAI = bool(os.environ.get("OPENAI_API_KEY"))
_HAS_ANTHROPIC = bool(os.environ.get("ANTHROPIC_API_KEY"))


@unittest.skipUnless(_LIVE and _HAS_OPENAI, "RUN_LIVE_LLM_TESTS=1 + OPENAI_API_KEY required")
class LiveOpenAITests(TestCase):
    """Hits the real OpenAI API. Costs ~$0.0001 per test."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("liveoai", password="pw12345!")
        cls.tool = AITool.objects.create(
            name="OpenAI gpt-4o-mini",
            slug="oai-mini",
            provider="openai",
            default_model="gpt-4o-mini",
            api_key_env_var="OPENAI_API_KEY",
        )

    def test_get_provider_returns_real_openai(self):
        with override_settings(OPENAI_API_KEY=os.environ["OPENAI_API_KEY"]):
            provider = get_provider(self.tool)
        self.assertIsInstance(provider, OpenAIProvider)

    def test_call_returns_nonempty_text(self):
        provider = OpenAIProvider(api_key=os.environ["OPENAI_API_KEY"])
        resp = provider.call(
            "Reply with the single word PONG and nothing else.",
            model="gpt-4o-mini",
            max_tokens=8,
        )
        self.assertIsInstance(resp, ProviderResponse)
        self.assertTrue(resp.text.strip())
        self.assertGreater(resp.tokens_input, 0)
        self.assertGreater(resp.tokens_output, 0)
        self.assertGreater(resp.latency_ms, 0)
        self.assertIn("pong", resp.text.lower())

    def test_run_prompt_persists_sandbox_run(self):
        with override_settings(OPENAI_API_KEY=os.environ["OPENAI_API_KEY"]):
            run = run_prompt(self.user, self.tool, "Say PONG.", model="gpt-4o-mini")
        self.assertEqual(run.status, "ok")
        self.assertTrue(run.response.strip())
        self.assertEqual(run.tool, self.tool)


@unittest.skipUnless(_LIVE and _HAS_ANTHROPIC,
                     "RUN_LIVE_LLM_TESTS=1 + ANTHROPIC_API_KEY required")
class LiveAnthropicTests(TestCase):
    """Hits the real Anthropic API. Costs ~$0.0005 per test."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("liveant", password="pw12345!")
        cls.tool = AITool.objects.create(
            name="Claude 3.5 Haiku",
            slug="claude-haiku",
            provider="anthropic",
            default_model="claude-3-5-haiku-20241022",
        )

    def test_get_provider_returns_real_anthropic(self):
        with override_settings(ANTHROPIC_API_KEY=os.environ["ANTHROPIC_API_KEY"]):
            p = get_provider(self.tool)
        self.assertIsInstance(p, AnthropicProvider)

    def test_call_returns_nonempty_text(self):
        provider = AnthropicProvider(api_key=os.environ["ANTHROPIC_API_KEY"])
        resp = provider.call(
            "Reply with the single word PONG and nothing else.",
            model="claude-3-5-haiku-20241022",
            max_tokens=8,
        )
        self.assertIsInstance(resp, ProviderResponse)
        self.assertTrue(resp.text.strip())
        self.assertGreater(resp.tokens_input, 0)
        self.assertGreater(resp.tokens_output, 0)
        self.assertIn("pong", resp.text.lower())


class FallbackBehaviorTests(TestCase):
    """These run unconditionally \u2014 verify safe fallback path."""

    def test_missing_openai_key_falls_back_to_fake(self):
        tool = AITool.objects.create(name="x", slug="x", provider="openai")
        with override_settings(OPENAI_API_KEY=""):
            p = get_provider(tool)
        self.assertIsInstance(p, FakeProvider)

    def test_missing_anthropic_key_falls_back_to_fake(self):
        tool = AITool.objects.create(name="y", slug="y", provider="anthropic")
        with override_settings(ANTHROPIC_API_KEY=""):
            p = get_provider(tool)
        self.assertIsInstance(p, FakeProvider)
