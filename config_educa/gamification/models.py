"""Points, badges, leaderboards."""
from django.contrib.auth.models import User
from django.db import models, transaction
from django.db.models import Sum


class Badge(models.Model):
    """A named achievement.

    `rule_code` is a free-form identifier used by signals/services to award
    the badge (e.g. "first_course_completed", "five_streak", "first_post").
    """

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=80, blank=True,
                            help_text="Icon name or emoji.")
    points_reward = models.PositiveIntegerField(default=0)
    rule_code = models.CharField(max_length=80, blank=True, db_index=True)
    is_active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class UserBadge(models.Model):
    """One badge awarded to one user (idempotent)."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="badges")
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE, related_name="awarded_to")
    awarded_at = models.DateTimeField(auto_now_add=True)
    awarded_for = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = ["user", "badge"]
        ordering = ["-awarded_at"]
        indexes = [models.Index(fields=["user", "-awarded_at"])]

    def __str__(self):
        return f"{self.user} \u2192 {self.badge}"


class PointsTransaction(models.Model):
    """A single +/- points event. Sum gives current balance."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="points_transactions")
    delta = models.IntegerField(help_text="Positive = earn, negative = spend.")
    reason = models.CharField(max_length=200)
    metadata = models.JSONField(default=dict, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]
        indexes = [models.Index(fields=["user", "-created"])]

    def __str__(self):
        return f"{self.user} {self.delta:+d} ({self.reason})"


# -- Service helpers ----------------------------------------------------------

@transaction.atomic
def award_badge(user, slug: str, awarded_for: str = "") -> UserBadge | None:
    """Idempotent: returns the UserBadge (existing or new), or None if no badge."""
    try:
        badge = Badge.objects.get(slug=slug, is_active=True)
    except Badge.DoesNotExist:
        return None
    ub, created = UserBadge.objects.get_or_create(
        user=user, badge=badge, defaults={"awarded_for": awarded_for}
    )
    if created and badge.points_reward:
        PointsTransaction.objects.create(
            user=user, delta=badge.points_reward,
            reason=f"badge:{badge.slug}",
        )
    return ub


def user_points(user) -> int:
    return PointsTransaction.objects.filter(user=user).aggregate(s=Sum("delta"))["s"] or 0


def leaderboard(limit: int = 10):
    """Return top-N users with their point totals."""
    return (
        PointsTransaction.objects
        .values("user_id", "user__username")
        .annotate(total=Sum("delta"))
        .order_by("-total")[:limit]
    )
