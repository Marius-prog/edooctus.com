from django.contrib import admin
from .models import AITool, PromptTemplate, SandboxRun, UsageQuota


@admin.register(AITool)
class AIToolAdmin(admin.ModelAdmin):
    list_display = ("name", "provider", "default_model", "is_active")
    list_filter = ("provider", "is_active")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(PromptTemplate)
class PromptTemplateAdmin(admin.ModelAdmin):
    list_display = ("title", "tool", "author", "is_public", "use_count", "created")
    list_filter = ("tool", "is_public")
    search_fields = ("title", "body")


@admin.register(SandboxRun)
class SandboxRunAdmin(admin.ModelAdmin):
    list_display = ("user", "tool", "status", "tokens_input", "tokens_output",
                    "latency_ms", "created")
    list_filter = ("status", "tool")
    readonly_fields = [f.name for f in SandboxRun._meta.fields]


@admin.register(UsageQuota)
class UsageQuotaAdmin(admin.ModelAdmin):
    list_display = ("user", "runs_this_period", "monthly_run_limit",
                    "tokens_this_period", "monthly_token_limit")
