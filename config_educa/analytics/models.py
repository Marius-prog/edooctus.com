from django.db import models
from django.contrib.auth.models import User
from courses.models import Course, Module, Content
from django.utils import timezone


class CourseView(models.Model):
    """Track every time a course page is viewed"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='views')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    session_id = models.CharField(max_length=40, db_index=True)
    viewed_at = models.DateTimeField(auto_now_add=True, db_index=True)
    referrer = models.URLField(max_length=500, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ['-viewed_at']
        indexes = [
            models.Index(fields=['course', '-viewed_at']),
            models.Index(fields=['user', '-viewed_at']),
            models.Index(fields=['session_id', '-viewed_at']),
        ]
        verbose_name = 'Course View'
        verbose_name_plural = 'Course Views'

    def __str__(self):
        return f"{self.course.title} - {self.viewed_at.strftime('%Y-%m-%d %H:%M')}"


class ModuleProgress(models.Model):
    """Track student progress through course modules"""
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='module_progress')
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='progress_records')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    time_spent_seconds = models.IntegerField(default=0)
    last_accessed = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'module']
        ordering = ['-last_accessed']
        indexes = [
            models.Index(fields=['user', 'module']),
            models.Index(fields=['module', 'status']),
            models.Index(fields=['-last_accessed']),
        ]
        verbose_name = 'Module Progress'
        verbose_name_plural = 'Module Progress'

    def __str__(self):
        return f"{self.user.username} - {self.module.title} ({self.status})"

    def mark_started(self):
        """Mark module as started"""
        if not self.started_at:
            self.started_at = timezone.now()
            self.status = 'in_progress'
            self.save()

    def mark_completed(self):
        """Mark module as completed"""
        if not self.completed_at:
            self.completed_at = timezone.now()
            self.status = 'completed'
            self.save()

    @property
    def completion_time_hours(self):
        """Calculate time to complete in hours"""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return delta.total_seconds() / 3600
        return None


class ContentInteraction(models.Model):
    """Track granular content engagement (videos, files, etc.)"""
    INTERACTION_TYPES = [
        ('view', 'View'),
        ('play', 'Play'),
        ('pause', 'Pause'),
        ('complete', 'Complete'),
        ('download', 'Download'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='content_interactions')
    content = models.ForeignKey(Content, on_delete=models.CASCADE, related_name='interactions')
    interaction_type = models.CharField(max_length=20, choices=INTERACTION_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    duration_seconds = models.IntegerField(null=True, blank=True, help_text="For video/audio content")
    position_seconds = models.IntegerField(null=True, blank=True, help_text="Playback position")
    completed = models.BooleanField(default=False)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'content', '-timestamp']),
            models.Index(fields=['content', '-timestamp']),
            models.Index(fields=['interaction_type', '-timestamp']),
        ]
        verbose_name = 'Content Interaction'
        verbose_name_plural = 'Content Interactions'

    def __str__(self):
        return f"{self.user.username} - {self.interaction_type} - {self.content}"


class EnrollmentEvent(models.Model):
    """Track enrollment funnel from view to completion"""
    EVENT_TYPES = [
        ('course_view', 'Course View'),
        ('enroll_click', 'Enroll Button Click'),
        ('enrolled', 'Enrolled'),
        ('first_module_accessed', 'First Module Accessed'),
        ('course_completed', 'Course Completed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollment_events')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollment_events')
    event_type = models.CharField(max_length=30, choices=EVENT_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'course', '-timestamp']),
            models.Index(fields=['event_type', '-timestamp']),
        ]
        verbose_name = 'Enrollment Event'
        verbose_name_plural = 'Enrollment Events'

    def __str__(self):
        return f"{self.user.username} - {self.course.title} - {self.event_type}"


class UserSession(models.Model):
    """Track user login sessions and activity"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=40, unique=True)
    started_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['user', '-started_at']),
            models.Index(fields=['session_key']),
        ]
        verbose_name = 'User Session'
        verbose_name_plural = 'User Sessions'

    def __str__(self):
        return f"{self.user.username} - {self.started_at.strftime('%Y-%m-%d %H:%M')}"

    @property
    def duration_minutes(self):
        """Calculate session duration in minutes"""
        end_time = self.ended_at or self.last_activity
        delta = end_time - self.started_at
        return delta.total_seconds() / 60


class LearningStreak(models.Model):
    """Gamification: track consecutive learning days"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='learning_streaks')
    date = models.DateField(db_index=True)
    courses_accessed = models.ManyToManyField(Course, related_name='streak_records')
    modules_completed = models.IntegerField(default=0)
    time_spent_minutes = models.IntegerField(default=0)

    class Meta:
        unique_together = ['user', 'date']
        ordering = ['-date']
        indexes = [
            models.Index(fields=['user', '-date']),
        ]
        verbose_name = 'Learning Streak'
        verbose_name_plural = 'Learning Streaks'

    def __str__(self):
        return f"{self.user.username} - {self.date}"

    @classmethod
    def get_current_streak(cls, user):
        """Calculate user's current learning streak"""
        from datetime import date, timedelta

        today = date.today()
        streak_count = 0
        check_date = today

        while True:
            if cls.objects.filter(user=user, date=check_date).exists():
                streak_count += 1
                check_date -= timedelta(days=1)
            else:
                break

        return streak_count
