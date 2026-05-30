"""Async badge-checking & leaderboard cache refresh."""
from celery import shared_task
from django.contrib.auth import get_user_model

from .models import award_badge

User = get_user_model()


@shared_task(name="gamification.check_badges_for_user")
def check_badges_for_user(user_id: int, rule_code: str, awarded_for: str = "") -> bool:
    """Evaluate `rule_code` and award the matching Badge slug if eligible.

    Mapping is intentionally loose: rule_code == badge slug in the simplest case.
    More sophisticated rules can be added by extending the dispatch table below.
    """
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return False
    slug = rule_code.replace("_", "-")
    ub = award_badge(user, slug, awarded_for=awarded_for)
    return ub is not None
