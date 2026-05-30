"""Quiz / assessment engine.

Design:
    Quiz  --has-many-->  Question  --has-many-->  Choice
    Quiz  --has-many-->  Submission (per user attempt) --has-many--> Answer
"""
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

from courses.models import Course, Module


class Quiz(models.Model):
    """A graded assessment attached to a course or module."""

    GRADING_AUTO = "auto"
    GRADING_MANUAL = "manual"
    GRADING_CHOICES = [
        (GRADING_AUTO, "Auto-graded"),
        (GRADING_MANUAL, "Manually graded"),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="quizzes")
    module = models.ForeignKey(
        Module, on_delete=models.SET_NULL, null=True, blank=True, related_name="quizzes"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    pass_mark_pct = models.PositiveIntegerField(
        default=70, validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Minimum % to pass.",
    )
    time_limit_seconds = models.PositiveIntegerField(
        null=True, blank=True, help_text="Optional time limit; null = unlimited."
    )
    max_attempts = models.PositiveIntegerField(default=3)
    grading_mode = models.CharField(max_length=10, choices=GRADING_CHOICES, default=GRADING_AUTO)
    is_published = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["course", "title"]
        indexes = [
            models.Index(fields=["course", "is_published"]),
        ]
        verbose_name_plural = "Quizzes"

    def __str__(self):
        return self.title

    @property
    def total_points(self):
        return self.questions.aggregate(t=models.Sum("points"))["t"] or 0


class Question(models.Model):
    """A single question on a quiz."""

    TYPE_SINGLE = "single"
    TYPE_MULTI = "multi"
    TYPE_TRUE_FALSE = "tf"
    TYPE_SHORT = "short"
    TYPE_CHOICES = [
        (TYPE_SINGLE, "Single choice"),
        (TYPE_MULTI, "Multiple choice"),
        (TYPE_TRUE_FALSE, "True / False"),
        (TYPE_SHORT, "Short answer"),
    ]

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    prompt = models.TextField()
    question_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=TYPE_SINGLE)
    points = models.PositiveIntegerField(default=1)
    order = models.PositiveIntegerField(default=0)
    explanation = models.TextField(blank=True, help_text="Shown after answer.")

    class Meta:
        ordering = ["order", "id"]
        indexes = [models.Index(fields=["quiz", "order"])]

    def __str__(self):
        return f"Q{self.order}: {self.prompt[:60]}"


class Choice(models.Model):
    """An answer option for a Question."""

    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.text[:60]


class Submission(models.Model):
    """A single attempt by a user."""

    STATUS_IN_PROGRESS = "in_progress"
    STATUS_SUBMITTED = "submitted"
    STATUS_GRADED = "graded"
    STATUS_CHOICES = [
        (STATUS_IN_PROGRESS, "In progress"),
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_GRADED, "Graded"),
    ]

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="submissions")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="quiz_submissions")
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    score_points = models.PositiveIntegerField(default=0)
    score_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    passed = models.BooleanField(default=False)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_IN_PROGRESS)

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["user", "quiz"]),
            models.Index(fields=["quiz", "-submitted_at"]),
        ]

    def __str__(self):
        return f"{self.user} - {self.quiz} ({self.status})"

    def grade(self):
        """Auto-grade objective questions. Returns (points, pct, passed)."""
        total = self.quiz.total_points or 1
        earned = 0
        for ans in self.answers.select_related("question").prefetch_related("selected_choices"):
            q = ans.question
            if q.question_type == Question.TYPE_SHORT:
                # Manual grading — defer (use ans.awarded_points already set).
                earned += ans.awarded_points or 0
                continue
            correct_ids = set(
                q.choices.filter(is_correct=True).values_list("id", flat=True)
            )
            selected_ids = set(c.id for c in ans.selected_choices.all())
            if correct_ids and correct_ids == selected_ids:
                earned += q.points
                ans.awarded_points = q.points
            else:
                ans.awarded_points = 0
            ans.save(update_fields=["awarded_points"])
        pct = round((earned / total) * 100, 2)
        self.score_points = earned
        self.score_pct = pct
        self.passed = pct >= self.quiz.pass_mark_pct
        self.submitted_at = self.submitted_at or timezone.now()
        self.status = self.STATUS_GRADED
        self.save(update_fields=["score_points", "score_pct", "passed", "submitted_at", "status"])
        return earned, pct, self.passed


class Answer(models.Model):
    """A user's answer to one question within a Submission."""

    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="answers")
    selected_choices = models.ManyToManyField(Choice, blank=True, related_name="picked_in_answers")
    text_response = models.TextField(blank=True, help_text="For short-answer questions.")
    awarded_points = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ["submission", "question"]

    def __str__(self):
        return f"{self.submission_id}/{self.question_id}"


class Rubric(models.Model):
    """A grading rubric for short-answer / project questions."""

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class RubricCriterion(models.Model):
    """A single line-item in a rubric."""

    rubric = models.ForeignKey(Rubric, on_delete=models.CASCADE, related_name="criteria")
    criterion = models.CharField(max_length=200)
    max_points = models.PositiveIntegerField(default=10)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.rubric}: {self.criterion}"
