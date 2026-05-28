from django.conf import settings


def feature_flags(request):
    """Expose feature flags to templates."""
    return {
        "USE_FOUNDRY_UI": getattr(settings, "USE_FOUNDRY_UI", False),
    }
