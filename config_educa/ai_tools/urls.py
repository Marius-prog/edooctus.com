from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

app_name = "ai_tools"

router = DefaultRouter()
router.register(r"tools", views.AIToolViewSet, basename="tool")
router.register(r"templates", views.PromptTemplateViewSet, basename="template")
router.register(r"runs", views.SandboxRunViewSet, basename="run")

urlpatterns = [
    path("", views.ToolListView.as_view(), name="list"),
    # `sandbox/run/` must precede the slug pattern so it isn't matched as a slug.
    path("sandbox/run/", views.sandbox_run_htmx, name="sandbox_run"),
    path("sandbox/<slug:slug>/", views.SandboxView.as_view(), name="sandbox"),
    path("api/", include(router.urls)),
]
