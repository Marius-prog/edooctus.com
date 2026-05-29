"""AI tool integrations: registered providers, prompt templates, usage logs, sandbox.

Designed so real API calls are pluggable via the `provider` field — the
abstract `BaseProvider` in `ai_tools.providers` is the integration seam.
"""
from django.contrib.auth.models import User
from django.db import models

from courses.models import Course


class AITool(models.Model):
    """A registered AI tool that learners study (e.g. ChatGPT, Claude, Midjourney)."""

    PROVIDER_OPENAI = "openai"
    PROVIDER_ANTHROPIC = "anthropic"
    PROVIDER_GOOGLE = "google"
    PROVIDER_LOCAL = "local"
    PROVIDER_OTHER = "other"
    PROVIDER_CHOICES = [
        (PROVIDER_OPENAI, "OpenAI"),
        (PROVIDER_ANTHROPIC, "Anthropic"),
        (PROVIDER_GOOGLE, "Google"),
        (PROVIDER_LOCAL, "Local / self-hosted"),
        (PROVIDER_OTHER, "Other"),
    ]

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    description = models.TextField(blank=True)
    docs_url = models.URLField(blank=True)
    homepage_url = models.URLField(blank=True)
    # Encrypted in production; here a placeholder. NEVER commit real keys.
    api_key_env_var = models.CharField(
        max_length=100, blank=True,
        help_text="Name of env var holding the API key (do not store the key itself)."
    )
    default_model = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class PromptTemplate(models.Model):
    """A reusable, taggable prompt — the canonical 'AI tool' learning artifact."""

    tool = models.ForeignKey(AITool, on_delete=models.CASCADE, related_name="templates")
    course = models.ForeignKey(
        Course, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="prompt_templates"
    )
    author = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="prompt_templates"
    )
    title = models.CharField(max_length=200)
    body = models.TextField(help_text="Prompt body with {{placeholders}}.")
    variables = models.JSONField(
        default=list, blank=True,
        help_text="List of {name, label, default} for placeholders."
    )
    tags = models.JSONField(default=list, blank=True)
    is_public = models.BooleanField(default=True)
    use_count = models.PositiveIntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]
        indexes = [
            models.Index(fields=["tool", "-created"]),
            models.Index(fields=["-use_count"]),
        ]

    def __str__(self):
        return self.title

    def render(self, values: dict) -> str:
        """Naive {{var}} substitution."""
        out = self.body
        for k, v in (values or {}).items():
            out = out.replace("{{" + k + "}}", str(v))
        return out


class SandboxRun(models.Model):
    """A single user invocation of a tool through the platform sandbox."""

    STATUS_PENDING = "pending"
    STATUS_OK = "ok"
    STATUS_ERROR = "error"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_OK, "OK"),
        (STATUS_ERROR, "Error"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sandbox_runs")
    tool = models.ForeignKey(AITool, on_delete=models.CASCADE, related_name="runs")
    template = models.ForeignKey(
        PromptTemplate, on_delete=models.SET_NULL, null=True, blank=True, related_name="runs"
    )
    prompt = models.TextField()
    response = models.TextField(blank=True)
    model_name = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    error_message = models.TextField(blank=True)
    tokens_input = models.PositiveIntegerField(default=0)
    tokens_output = models.PositiveIntegerField(default=0)
    cost_micros = models.PositiveIntegerField(
        default=0, help_text="Estimated cost in millionths of a USD."
    )
    latency_ms = models.PositiveIntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]
        indexes = [
            models.Index(fields=["user", "-created"]),
            models.Index(fields=["tool", "-created"]),
        ]

    def __str__(self):
        return f"{self.user} \u2192 {self.tool} ({self.status})"


class UsageQuota(models.Model):
    """Per-user monthly budget so learners can experiment safely."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="ai_quota")
    monthly_run_limit = models.PositiveIntegerField(default=100)
    monthly_token_limit = models.PositiveIntegerField(default=200_000)
    runs_this_period = models.PositiveIntegerField(default=0)
    tokens_this_period = models.PositiveIntegerField(default=0)
    period_started_at = models.DateTimeField(auto_now_add=True)

    def has_budget(self, est_tokens: int = 0) -> bool:
        return (
            self.runs_this_period < self.monthly_run_limit
            and self.tokens_this_period + est_tokens <= self.monthly_token_limit
        )

    def __str__(self):
        return f"{self.user} quota"
