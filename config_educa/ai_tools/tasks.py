"""Async LLM invocation so HTTP requests don't block on provider latency."""
from celery import shared_task
from django.contrib.auth import get_user_model

from .models import AITool, PromptTemplate
from .services import run_prompt

User = get_user_model()


@shared_task(name="ai_tools.run_prompt_async", bind=True, max_retries=2)
def run_prompt_async(self, user_id: int, tool_id: int, prompt: str,
                     template_id: int | None = None, model: str | None = None) -> int:
    user = User.objects.get(pk=user_id)
    tool = AITool.objects.get(pk=tool_id)
    template = PromptTemplate.objects.filter(pk=template_id).first() if template_id else None
    run = run_prompt(user, tool, prompt, template=template, model=model)
    return run.id
