"""Assignments + peer-review workflow.

Flow:
    Assignment (instructor-defined, optionally with a Rubric)
        \u2193
    Submission (one per student)
        \u2193
    PeerReview (other students grade against rubric)
        \u2193
    Aggregated score on the Submission
"""
from django.contrib.auth.models import User
from django.db import models
from django.db.models import Avg
from django.utils import timezone

from courses.models import Course
from quizzes.models import Rubric


class Assignment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="assignments")
    title = models.CharField(max_length=200)
    instructions = models.TextField()
    rubric = models.ForeignKey(
        Rubric, on_delete=models.SET_NULL, null=True, blank=True, related_name="assignments"
    )
    due_at = models.DateTimeField(null=True, blank=True)
    peer_reviews_required = models.PositiveIntegerField(
        default=2, help_text="Number of peer reviews each submission must receive."
    )
    is_published = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]
        indexes = [models.Index(fields=["course", "is_published"])]

    def __str__(self):
        return self.title


class Submission(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_SUBMITTED = "submitted"
    STATUS_REVIEWED = "reviewed"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_REVIEWED, "Reviewed"),
    ]

    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="submissions")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="peer_submissions")
    content = models.TextField(blank=True)
    file = models.FileField(upload_to="peer_review/", null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    submitted_at = models.DateTimeField(null=True, blank=True)
    avg_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    review_count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ["assignment", "author"]
        ordering = ["-submitted_at"]
        indexes = [models.Index(fields=["assignment", "status"])]

    def __str__(self):
        return f"{self.author} \u2192 {self.assignment}"

    def submit(self):
        self.status = self.STATUS_SUBMITTED
        self.submitted_at = timezone.now()
        self.save(update_fields=["status", "submitted_at"])

    def recalculate_score(self):
        stats = self.peer_reviews.aggregate(a=Avg("score"), c=models.Count("id"))
        self.avg_score = round(stats["a"] or 0, 2)
        self.review_count = stats["c"] or 0
        if self.review_count >= self.assignment.peer_reviews_required:
            self.status = self.STATUS_REVIEWED
        self.save(update_fields=["avg_score", "review_count", "status"])


class PeerReview(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="peer_reviews")
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="peer_reviews_given")
    score = models.DecimalField(max_digits=5, decimal_places=2)
    feedback = models.TextField(blank=True)
    is_anonymous = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["submission", "reviewer"]
        ordering = ["-created"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(score__gte=0) & models.Q(score__lte=100),
                name="peerreview_score_range",
            ),
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.submission.recalculate_score()

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.reviewer_id == self.submission.author_id:
            raise ValidationError("Cannot review own submission.")
