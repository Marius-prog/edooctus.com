"""Mentor profiles, mentorship requests, sessions."""
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class MentorProfile(models.Model):
    """Mentor opt-in record + expertise."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="mentor_profile")
    bio = models.TextField(blank=True)
    expertise = models.JSONField(default=list, blank=True,
                                 help_text="List of tags / skill slugs.")
    timezone_name = models.CharField(max_length=64, blank=True)
    max_active_mentees = models.PositiveIntegerField(default=3)
    is_accepting = models.BooleanField(default=True)
    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    total_sessions = models.PositiveIntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["is_accepting", "-avg_rating"])]

    def __str__(self):
        return f"Mentor: {self.user}"

    def has_capacity(self) -> bool:
        if not self.is_accepting:
            return False
        active = MentorshipRequest.objects.filter(
            mentor=self.user, status=MentorshipRequest.STATUS_ACCEPTED
        ).count()
        return active < self.max_active_mentees


class MentorshipRequest(models.Model):
    """A mentee → mentor pairing request."""

    STATUS_PENDING = "pending"
    STATUS_ACCEPTED = "accepted"
    STATUS_DECLINED = "declined"
    STATUS_ENDED = "ended"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_DECLINED, "Declined"),
        (STATUS_ENDED, "Ended"),
    ]

    mentee = models.ForeignKey(User, on_delete=models.CASCADE, related_name="mentor_requests_sent")
    mentor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="mentor_requests_received")
    message = models.TextField(blank=True)
    goals = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created"]
        indexes = [
            models.Index(fields=["mentor", "status"]),
            models.Index(fields=["mentee", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=~models.Q(mentee=models.F("mentor")),
                name="mentee_neq_mentor",
            ),
        ]

    def __str__(self):
        return f"{self.mentee} \u2192 {self.mentor} ({self.status})"

    def accept(self):
        self.status = self.STATUS_ACCEPTED
        self.responded_at = timezone.now()
        self.save(update_fields=["status", "responded_at"])

    def decline(self):
        self.status = self.STATUS_DECLINED
        self.responded_at = timezone.now()
        self.save(update_fields=["status", "responded_at"])

    def end(self):
        self.status = self.STATUS_ENDED
        self.ended_at = timezone.now()
        self.save(update_fields=["status", "ended_at"])


class MentorshipSession(models.Model):
    """A single 1:1 session log."""

    pairing = models.ForeignKey(MentorshipRequest, on_delete=models.CASCADE,
                                related_name="sessions")
    scheduled_at = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=30)
    notes = models.TextField(blank=True)
    mentor_rating = models.PositiveSmallIntegerField(null=True, blank=True)
    mentee_rating = models.PositiveSmallIntegerField(null=True, blank=True)
    completed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-scheduled_at"]


# -- Matching service ---------------------------------------------------------

def find_mentors(skill_tags: list[str], limit: int = 5):
    """Naive matcher: mentors with overlapping expertise, sorted by rating + capacity."""
    qs = MentorProfile.objects.filter(is_accepting=True)
    if skill_tags:
        # JSONField contains lookup is DB-dependent; do this in Python for portability.
        candidates = []
        for m in qs:
            overlap = len(set(m.expertise or []) & set(skill_tags))
            if overlap:
                candidates.append((overlap, m))
        candidates.sort(key=lambda x: (-x[0], -float(x[1].avg_rating)))
        return [m for _, m in candidates[:limit] if m.has_capacity()]
    return list(qs.order_by("-avg_rating")[:limit])
