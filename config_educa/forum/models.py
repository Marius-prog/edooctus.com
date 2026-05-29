"""Threaded discussion forum, attached to courses."""
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from courses.models import Course


class ForumCategory(models.Model):
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="forum_categories",
        null=True, blank=True,
        help_text="Null = site-wide category.",
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]
        unique_together = ["course", "slug"]
        verbose_name_plural = "Forum Categories"

    def __str__(self):
        return self.name


class Topic(models.Model):
    category = models.ForeignKey(ForumCategory, on_delete=models.CASCADE, related_name="topics")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="forum_topics")
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=240)
    is_pinned = models.BooleanField(default=False)
    is_locked = models.BooleanField(default=False)
    view_count = models.PositiveIntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-is_pinned", "-last_activity"]
        indexes = [
            models.Index(fields=["category", "-last_activity"]),
            models.Index(fields=["author", "-created"]),
        ]

    def __str__(self):
        return self.title


class Post(models.Model):
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="posts")
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies"
    )
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="forum_posts")
    body = models.TextField()
    is_solution = models.BooleanField(default=False, help_text="Marked as accepted answer.")
    is_flagged = models.BooleanField(default=False)
    flag_reason = models.CharField(max_length=200, blank=True)
    is_hidden = models.BooleanField(default=False, help_text="Hidden by moderator.")
    upvotes = models.PositiveIntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created"]
        indexes = [
            models.Index(fields=["topic", "created"]),
            models.Index(fields=["author", "-created"]),
            models.Index(fields=["is_flagged", "is_hidden"]),
        ]

    def __str__(self):
        return f"Post by {self.author} on {self.topic}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            Topic.objects.filter(pk=self.topic_id).update(last_activity=timezone.now())


class PostVote(models.Model):
    """Upvote/like records to prevent double-voting."""

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="votes")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="forum_votes")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["post", "user"]
