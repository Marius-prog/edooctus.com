"""In-app + email/push notifications with per-channel preferences."""
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


CHANNEL_IN_APP = "in_app"
CHANNEL_EMAIL = "email"
CHANNEL_PUSH = "push"
CHANNEL_CHOICES = [
    (CHANNEL_IN_APP, "In-app"),
    (CHANNEL_EMAIL, "Email"),
    (CHANNEL_PUSH, "Push"),
]


class NotificationPreference(models.Model):
    """Per-user, per-category opt-in/out."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="notif_prefs")
    email_enabled = models.BooleanField(default=True)
    push_enabled = models.BooleanField(default=False)
    in_app_enabled = models.BooleanField(default=True)
    course_updates = models.BooleanField(default=True)
    forum_replies = models.BooleanField(default=True)
    mentor_messages = models.BooleanField(default=True)
    marketing = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user} prefs"


class Notification(models.Model):
    """A single notification record."""

    KIND_CHOICES = [
        ("course_update", "Course Update"),
        ("forum_reply", "Forum Reply"),
        ("badge_earned", "Badge Earned"),
        ("certificate_ready", "Certificate Ready"),
        ("quiz_graded", "Quiz Graded"),
        ("mentor_message", "Mentor Message"),
        ("security_alert", "Security Alert"),
        ("system", "System"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    kind = models.CharField(max_length=30, choices=KIND_CHOICES)
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    link = models.CharField(max_length=500, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES, default=CHANNEL_IN_APP)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]
        indexes = [
            models.Index(fields=["user", "is_read", "-created"]),
            models.Index(fields=["user", "kind", "-created"]),
        ]

    def __str__(self):
        return f"{self.kind} \u2192 {self.user}"

    def mark_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])


# -- Helpers ------------------------------------------------------------------

def notify(user, kind: str, title: str, body: str = "", link: str = "",
           metadata: dict | None = None, channel: str = CHANNEL_IN_APP) -> Notification | None:
    """Create a Notification respecting user preferences."""
    prefs, _ = NotificationPreference.objects.get_or_create(user=user)
    if channel == CHANNEL_EMAIL and not prefs.email_enabled:
        return None
    if channel == CHANNEL_PUSH and not prefs.push_enabled:
        return None
    if channel == CHANNEL_IN_APP and not prefs.in_app_enabled:
        return None
    if kind == "course_update" and not prefs.course_updates:
        return None
    if kind == "forum_reply" and not prefs.forum_replies:
        return None
    if kind == "mentor_message" and not prefs.mentor_messages:
        return None
    n = Notification.objects.create(
        user=user, kind=kind, title=title, body=body, link=link,
        metadata=metadata or {}, channel=channel,
    )
    if channel == CHANNEL_EMAIL and user.email:
        # Queue async; runs inline in dev (CELERY_TASK_ALWAYS_EAGER=True).
        try:
            from .tasks import send_email_notification
            send_email_notification.delay(n.id)
        except Exception:  # pragma: no cover  — broker down shouldn't break web req
            pass
    return n


def unread_count(user) -> int:
    return Notification.objects.filter(user=user, is_read=False).count()
