from django.conf import settings


def feature_flags(request):
    """Expose feature flags + base-template selection to templates."""
    use_foundry = getattr(settings, "USE_FOUNDRY_UI", False)
    return {
        "USE_FOUNDRY_UI": use_foundry,
        "BASE_TEMPLATE": "foundry_base.html" if use_foundry else "base.html",
    }
