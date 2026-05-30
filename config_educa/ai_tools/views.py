from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST
from django.views.generic import ListView, DetailView

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import AITool, PromptTemplate, SandboxRun, UsageQuota
from .serializers import (
    AIToolSerializer, PromptTemplateSerializer,
    SandboxRunSerializer, UsageQuotaSerializer,
)
from .services import run_prompt, QuotaExceeded


class AIToolViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AITool.objects.filter(is_active=True)
    serializer_class = AIToolSerializer
    permission_classes = [permissions.IsAuthenticated]


class PromptTemplateViewSet(viewsets.ModelViewSet):
    serializer_class = PromptTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        u = self.request.user
        return (PromptTemplate.objects.filter(is_public=True) |
                PromptTemplate.objects.filter(author=u)).distinct().select_related("tool", "author")

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class SandboxRunViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SandboxRunSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SandboxRun.objects.filter(user=self.request.user).select_related("tool")

    @action(detail=False, methods=["post"])
    def run(self, request):
        tool_id = request.data.get("tool")
        prompt = request.data.get("prompt", "")
        template_id = request.data.get("template")
        model = request.data.get("model")
        if not (tool_id and prompt):
            return Response({"detail": "tool and prompt required."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            tool = AITool.objects.get(pk=tool_id, is_active=True)
        except AITool.DoesNotExist:
            return Response({"detail": "Unknown tool."}, status=status.HTTP_404_NOT_FOUND)
        template = PromptTemplate.objects.filter(pk=template_id).first() if template_id else None
        try:
            run_obj = run_prompt(request.user, tool, prompt, template=template, model=model)
        except QuotaExceeded as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        return Response(SandboxRunSerializer(run_obj).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"])
    def quota(self, request):
        q, _ = UsageQuota.objects.get_or_create(user=request.user)
        return Response(UsageQuotaSerializer(q).data)


# -- Server-rendered ----------------------------------------------------------

class ToolListView(LoginRequiredMixin, ListView):
    model = AITool
    template_name = "ai_tools/list.html"
    queryset = AITool.objects.filter(is_active=True)


class SandboxView(LoginRequiredMixin, DetailView):
    model = AITool
    template_name = "ai_tools/sandbox.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"


@login_required
@require_POST
def sandbox_run_htmx(request):
    """HTMX-friendly endpoint that renders an HTML partial response."""
    tool_id = request.POST.get("tool")
    prompt = (request.POST.get("prompt") or "").strip()
    if not (tool_id and prompt):
        return render(request, "ai_tools/_run_result.html",
                      {"error": "Missing tool or prompt."}, status=400)
    tool = get_object_or_404(AITool, pk=tool_id, is_active=True)
    try:
        run_obj = run_prompt(request.user, tool, prompt)
    except QuotaExceeded as exc:
        return render(request, "ai_tools/_run_result.html",
                      {"error": str(exc)}, status=429)
    return render(request, "ai_tools/_run_result.html", {"run": run_obj})
