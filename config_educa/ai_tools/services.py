"""Sandbox orchestration: enforces quota, calls provider, persists SandboxRun."""
from __future__ import annotations

from django.db import transaction

from .models import AITool, PromptTemplate, SandboxRun, UsageQuota
from .providers import get_provider


class QuotaExceeded(Exception):
    pass


@transaction.atomic
def run_prompt(user, tool: AITool, prompt: str, template: PromptTemplate | None = None,
               model: str | None = None) -> SandboxRun:
    quota, _ = UsageQuota.objects.get_or_create(user=user)
    if not quota.has_budget(est_tokens=len(prompt) // 4):
        raise QuotaExceeded(f"User {user} is over monthly AI budget.")

    provider = get_provider(tool)
    try:
        resp = provider.call(prompt, model=model or tool.default_model or None)
        run = SandboxRun.objects.create(
            user=user, tool=tool, template=template, prompt=prompt,
            response=resp.text, model_name=resp.model,
            tokens_input=resp.tokens_input, tokens_output=resp.tokens_output,
            cost_micros=resp.cost_micros, latency_ms=resp.latency_ms,
            status=SandboxRun.STATUS_OK,
        )
    except Exception as exc:  # noqa: BLE001 — surface any provider error
        run = SandboxRun.objects.create(
            user=user, tool=tool, template=template, prompt=prompt,
            status=SandboxRun.STATUS_ERROR, error_message=str(exc),
        )
        raise

    quota.runs_this_period += 1
    quota.tokens_this_period += resp.tokens_input + resp.tokens_output
    quota.save(update_fields=["runs_this_period", "tokens_this_period"])

    if template:
        PromptTemplate.objects.filter(pk=template.pk).update(use_count=template.use_count + 1)

    return run
