from rest_framework import serializers
from .models import AITool, PromptTemplate, SandboxRun, UsageQuota


class AIToolSerializer(serializers.ModelSerializer):
    class Meta:
        model = AITool
        fields = ["id", "name", "slug", "provider", "description",
                  "docs_url", "homepage_url", "default_model", "is_active"]


class PromptTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromptTemplate
        fields = ["id", "tool", "course", "author", "title", "body",
                  "variables", "tags", "is_public", "use_count", "created"]
        read_only_fields = ["author", "use_count", "created"]


class SandboxRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = SandboxRun
        fields = ["id", "user", "tool", "template", "prompt", "response",
                  "model_name", "status", "error_message",
                  "tokens_input", "tokens_output", "cost_micros",
                  "latency_ms", "created"]
        read_only_fields = ["user", "response", "model_name", "status",
                            "error_message", "tokens_input", "tokens_output",
                            "cost_micros", "latency_ms", "created"]


class UsageQuotaSerializer(serializers.ModelSerializer):
    class Meta:
        model = UsageQuota
        fields = ["monthly_run_limit", "monthly_token_limit",
                  "runs_this_period", "tokens_this_period", "period_started_at"]
