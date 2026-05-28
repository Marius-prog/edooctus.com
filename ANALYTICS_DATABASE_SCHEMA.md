# Educto Analytics Database Schema

## Analytics Requirements

### Business Context

Educto is an online education platform serving three primary stakeholders: **instructors** who create and manage courses, **students** who enroll and learn, and **platform administrators** who oversee platform health. Currently, the platform tracks only basic enrollment data through a many-to-many relationship and uses Redis to store the last accessed module per student. This minimal tracking leaves critical questions unanswered: Which courses drive the most engagement? Where do students struggle or drop off? How much time do students spend learning? Which content types perform best?

A comprehensive analytics system will transform raw user interactions into actionable insights. For **instructors**, metrics like module completion rates, average time-to-complete, content engagement patterns, and student drop-off points enable data-driven course improvements. For **students**, personal progress tracking, learning streaks, achievement milestones, and peer comparison create motivation and accountability. For **platform administrators**, overall platform health metrics, popular courses, user retention rates, revenue per course, and infrastructure utilization guide strategic decisions and resource allocation.

The analytics database must balance granular event tracking with pre-aggregated performance metrics. Raw event data captures every user interaction (page views, content views, enrollments) for deep analysis, while daily/weekly rollup tables enable fast dashboard queries. The schema prioritizes GDPR compliance through minimal data collection, clear retention policies, and user anonymization capabilities. All tracking respects user privacy while delivering the insights needed to grow the platform and improve learning outcomes.

---

## Core Analytics Models

### 1. CourseView - Course Page View Tracking

**Purpose**: Track every time a course detail page is viewed to measure course popularity and traffic sources.

```python
from django.db import models
from django.contrib.auth import get_user_model
from courses.models import Course

User = get_user_model()


class CourseView(models.Model):
    """
    Records every course detail page view.
    Tracks both authenticated and anonymous users.
    """
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='analytics_views'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='course_views'
    )
    session_id = models.CharField(
        max_length=40,
        help_text="Session key for tracking anonymous users"
    )
    viewed_at = models.DateTimeField(auto_now_add=True)
    referrer = models.URLField(
        blank=True,
        max_length=500,
        help_text="Where the user came from (HTTP_REFERER)"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="User's IP address for geographic analysis"
    )
    user_agent = models.TextField(
        blank=True,
        help_text="Browser/device information"
    )

    class Meta:
        ordering = ['-viewed_at']
        indexes = [
            models.Index(fields=['course', '-viewed_at']),
            models.Index(fields=['user', '-viewed_at']),
            models.Index(fields=['session_id', '-viewed_at']),
            models.Index(fields=['-viewed_at']),  # Time-series queries
        ]

    def __str__(self):
        viewer = self.user.username if self.user else f"Anonymous ({self.session_id[:8]})"
        return f"{viewer} viewed {self.course.title} at {self.viewed_at}"
```

**Use Case**: "Show me all course views in the last 7 days, broken down by authenticated vs anonymous users."

**Privacy Note**: IP addresses stored only for geographic analysis (country/region level), never for individual tracking. Anonymized after 90 days.

---

### 2. ModuleProgress - Student Module Completion Tracking

**Purpose**: Track when students complete modules and how long they take, enabling completion rate analysis and drop-off detection.

```python
from django.db import models
from django.contrib.auth import get_user_model
from courses.models import Module

User = get_user_model()


class ModuleProgress(models.Model):
    """
    Tracks student progress through course modules.
    A module is "completed" when explicitly marked or when all content items are completed.
    """
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='module_progress'
    )
    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name='student_progress'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='not_started'
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the student first accessed this module"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the student completed this module"
    )
    time_spent_seconds = models.PositiveIntegerField(
        default=0,
        help_text="Total time spent on this module (tracked via content interactions)"
    )
    last_accessed_at = models.DateTimeField(
        auto_now=True,
        help_text="Last time student accessed this module"
    )

    class Meta:
        unique_together = ['student', 'module']
        ordering = ['student', 'module__order']
        indexes = [
            models.Index(fields=['student', 'status']),
            models.Index(fields=['module', 'status']),
            models.Index(fields=['student', 'module']),
            models.Index(fields=['-completed_at']),
        ]

    def __str__(self):
        return f"{self.student.username} - {self.module.course.title}: {self.module.title} ({self.status})"

    @property
    def completion_time_days(self):
        """Calculate days between start and completion"""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return delta.days
        return None

    @property
    def time_spent_hours(self):
        """Convert seconds to hours"""
        return round(self.time_spent_seconds / 3600, 2)
```

**Use Case**: "Which module has the lowest completion rate in Course X?"

---

### 3. ContentInteraction - Detailed Content Engagement Tracking

**Purpose**: Track every interaction with content items (text, video, image, file) to measure engagement depth and content effectiveness.

```python
from django.db import models
from django.contrib.auth import get_user_model
from courses.models import Content

User = get_user_model()


class ContentInteraction(models.Model):
    """
    Tracks granular interactions with course content.
    Records views, time spent, completion status for each content item.
    """
    INTERACTION_TYPES = [
        ('view', 'Viewed'),
        ('start', 'Started'),
        ('pause', 'Paused'),
        ('complete', 'Completed'),
        ('download', 'Downloaded'),  # For files
    ]

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='content_interactions'
    )
    content = models.ForeignKey(
        Content,
        on_delete=models.CASCADE,
        related_name='interactions'
    )
    interaction_type = models.CharField(
        max_length=20,
        choices=INTERACTION_TYPES
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    session_id = models.CharField(
        max_length=40,
        help_text="Session key for tracking individual learning sessions"
    )

    # Video-specific fields
    video_position_seconds = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Current playback position for videos"
    )
    video_duration_seconds = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Total video duration (cached for analysis)"
    )

    # Time tracking
    time_spent_seconds = models.PositiveIntegerField(
        default=0,
        help_text="Time spent on this content item in this session"
    )

    # Completion tracking
    is_completed = models.BooleanField(
        default=False,
        help_text="Whether this content item was fully consumed"
    )

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['student', 'content', '-timestamp']),
            models.Index(fields=['content', 'interaction_type', '-timestamp']),
            models.Index(fields=['student', '-timestamp']),
            models.Index(fields=['session_id', '-timestamp']),
        ]

    def __str__(self):
        return f"{self.student.username} {self.interaction_type} {self.content} at {self.timestamp}"

    @property
    def content_type_name(self):
        """Get the content type (text, video, image, file)"""
        return self.content.content_type.model

    @property
    def video_completion_percentage(self):
        """Calculate video completion percentage"""
        if self.video_position_seconds and self.video_duration_seconds:
            return round((self.video_position_seconds / self.video_duration_seconds) * 100, 2)
        return 0
```

**Use Case**: "What's the average video completion rate for all videos in the platform?"

---

### 4. EnrollmentEvent - Enrollment Funnel Tracking

**Purpose**: Track the complete enrollment journey from course view to first module access, enabling funnel optimization.

```python
from django.db import models
from django.contrib.auth import get_user_model
from courses.models import Course

User = get_user_model()


class EnrollmentEvent(models.Model):
    """
    Tracks the enrollment funnel and student lifecycle within a course.
    Captures key milestones from first view to course completion.
    """
    EVENT_TYPES = [
        ('first_view', 'First Course View'),
        ('enroll_click', 'Clicked Enroll Button'),
        ('enrolled', 'Successfully Enrolled'),
        ('first_module_access', 'Accessed First Module'),
        ('course_completed', 'Completed All Modules'),
        ('unenrolled', 'Unenrolled from Course'),
    ]

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='enrollment_events'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='enrollment_events'
    )
    event_type = models.CharField(
        max_length=30,
        choices=EVENT_TYPES
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional context (e.g., referrer, session_id)"
    )

    class Meta:
        ordering = ['student', 'course', 'timestamp']
        indexes = [
            models.Index(fields=['student', 'course', 'event_type']),
            models.Index(fields=['course', 'event_type', '-timestamp']),
            models.Index(fields=['-timestamp']),
        ]

    def __str__(self):
        return f"{self.student.username} - {self.event_type} - {self.course.title}"
```

**Use Case**: "Calculate conversion rate from first view to enrollment for each course."

---

### 5. ChatActivity - Real-time Chat Engagement Metrics

**Purpose**: Track chat participation to measure student engagement and community activity.

```python
from django.db import models
from django.contrib.auth import get_user_model
from courses.models import Course

User = get_user_model()


class ChatActivity(models.Model):
    """
    Tracks chat activity metrics per course per user.
    Aggregates from the existing Message model for analytics.
    """
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='chat_activity'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='chat_activity'
    )
    date = models.DateField(
        help_text="Date of activity (daily aggregation)"
    )
    messages_sent = models.PositiveIntegerField(
        default=0,
        help_text="Number of messages sent on this date"
    )
    total_characters = models.PositiveIntegerField(
        default=0,
        help_text="Total characters in messages (measure of engagement depth)"
    )
    first_message_at = models.TimeField(
        null=True,
        blank=True,
        help_text="Time of first message (for activity pattern analysis)"
    )
    last_message_at = models.TimeField(
        null=True,
        blank=True,
        help_text="Time of last message"
    )

    class Meta:
        unique_together = ['student', 'course', 'date']
        ordering = ['student', 'course', '-date']
        indexes = [
            models.Index(fields=['course', '-date']),
            models.Index(fields=['student', '-date']),
            models.Index(fields=['-date']),
        ]
        verbose_name_plural = 'Chat activities'

    def __str__(self):
        return f"{self.student.username} in {self.course.title} on {self.date} ({self.messages_sent} messages)"
```

**Use Case**: "Identify most active chat participants per course for potential student ambassador program."

---

### 6. UserSession - Login and Activity Session Tracking

**Purpose**: Track user login sessions, duration, and activity patterns to measure engagement and retention.

```python
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class UserSession(models.Model):
    """
    Tracks user login sessions and activity patterns.
    Helps measure user engagement, retention, and identify at-risk students.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='analytics_sessions'
    )
    session_key = models.CharField(
        max_length=40,
        unique=True,
        help_text="Django session key"
    )
    started_at = models.DateTimeField(auto_now_add=True)
    last_activity_at = models.DateTimeField(
        auto_now=True,
        help_text="Last recorded activity in this session"
    )
    ended_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the user logged out or session expired"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True
    )
    user_agent = models.TextField(
        blank=True,
        help_text="Browser/device info"
    )

    # Activity metrics
    pages_viewed = models.PositiveIntegerField(
        default=0,
        help_text="Number of pages viewed in this session"
    )
    courses_accessed = models.ManyToManyField(
        'courses.Course',
        blank=True,
        related_name='session_accesses',
        help_text="Courses accessed during this session"
    )

    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['user', '-started_at']),
            models.Index(fields=['session_key']),
            models.Index(fields=['-started_at']),
            models.Index(fields=['-last_activity_at']),
        ]

    def __str__(self):
        return f"{self.user.username} session from {self.started_at}"

    @property
    def duration_seconds(self):
        """Calculate session duration"""
        end_time = self.ended_at or self.last_activity_at
        if end_time and self.started_at:
            delta = end_time - self.started_at
            return delta.total_seconds()
        return 0

    @property
    def duration_minutes(self):
        """Session duration in minutes"""
        return round(self.duration_seconds / 60, 2)

    @property
    def is_active(self):
        """Whether this session is still active"""
        return self.ended_at is None
```

**Use Case**: "Calculate average session duration for students in high-performing vs low-performing courses."

---

### 7. LearningStreak - Gamification and Motivation Tracking

**Purpose**: Track consecutive days of learning activity to encourage daily engagement and celebrate student consistency.

```python
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class LearningStreak(models.Model):
    """
    Tracks learning streaks for gamification.
    A streak is active when a student accesses course content on consecutive days.
    """
    student = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='learning_streak',
        primary_key=True
    )
    current_streak_days = models.PositiveIntegerField(
        default=0,
        help_text="Current consecutive days of activity"
    )
    longest_streak_days = models.PositiveIntegerField(
        default=0,
        help_text="Longest streak ever achieved"
    )
    last_activity_date = models.DateField(
        null=True,
        blank=True,
        help_text="Last date with learning activity"
    )
    streak_started_at = models.DateField(
        null=True,
        blank=True,
        help_text="When the current streak started"
    )
    total_active_days = models.PositiveIntegerField(
        default=0,
        help_text="Total number of days with any learning activity"
    )

    class Meta:
        ordering = ['-current_streak_days']

    def __str__(self):
        return f"{self.student.username}: {self.current_streak_days} day streak"

    def update_streak(self, activity_date=None):
        """
        Update streak based on new activity.
        Call this whenever a student accesses course content.
        """
        if activity_date is None:
            activity_date = timezone.now().date()

        if self.last_activity_date is None:
            # First activity ever
            self.current_streak_days = 1
            self.longest_streak_days = 1
            self.streak_started_at = activity_date
            self.total_active_days = 1
        elif activity_date == self.last_activity_date:
            # Same day, no change
            return
        elif (activity_date - self.last_activity_date).days == 1:
            # Consecutive day, increment streak
            self.current_streak_days += 1
            self.total_active_days += 1
            if self.current_streak_days > self.longest_streak_days:
                self.longest_streak_days = self.current_streak_days
        elif (activity_date - self.last_activity_date).days > 1:
            # Streak broken, reset
            self.current_streak_days = 1
            self.streak_started_at = activity_date
            self.total_active_days += 1

        self.last_activity_date = activity_date
        self.save()

    @property
    def is_active_today(self):
        """Check if streak is active today"""
        if self.last_activity_date:
            return self.last_activity_date == timezone.now().date()
        return False

    @property
    def streak_at_risk(self):
        """Check if streak will break tomorrow without activity"""
        if self.last_activity_date and self.current_streak_days > 0:
            days_since_activity = (timezone.now().date() - self.last_activity_date).days
            return days_since_activity == 0  # Last activity was today, at risk tomorrow
        return False
```

**Use Case**: "Send push notification to students whose streak is at risk of breaking."

---

## Aggregated Metrics Tables

### 1. DailyCourseMetrics - Pre-aggregated Daily Course Performance

**Purpose**: Store pre-calculated daily metrics per course for fast dashboard queries without scanning millions of event rows.

```python
from django.db import models
from courses.models import Course


class DailyCourseMetrics(models.Model):
    """
    Daily rollup of course performance metrics.
    Populated by a nightly Celery task that aggregates raw event data.
    """
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='daily_metrics'
    )
    date = models.DateField(
        help_text="Date these metrics represent"
    )

    # View metrics
    total_views = models.PositiveIntegerField(
        default=0,
        help_text="Total CourseView records for this date"
    )
    unique_visitors = models.PositiveIntegerField(
        default=0,
        help_text="Distinct users/sessions who viewed the course"
    )
    authenticated_views = models.PositiveIntegerField(
        default=0,
        help_text="Views from logged-in users"
    )
    anonymous_views = models.PositiveIntegerField(
        default=0,
        help_text="Views from non-authenticated visitors"
    )

    # Enrollment metrics
    new_enrollments = models.PositiveIntegerField(
        default=0,
        help_text="New enrollments on this date"
    )
    total_enrolled_students = models.PositiveIntegerField(
        default=0,
        help_text="Cumulative total enrolled students up to this date"
    )

    # Engagement metrics
    active_students = models.PositiveIntegerField(
        default=0,
        help_text="Students who accessed course content on this date"
    )
    avg_time_spent_seconds = models.PositiveIntegerField(
        default=0,
        help_text="Average time spent per active student"
    )
    total_content_interactions = models.PositiveIntegerField(
        default=0,
        help_text="Total ContentInteraction records"
    )

    # Completion metrics
    modules_completed = models.PositiveIntegerField(
        default=0,
        help_text="Number of modules marked complete on this date"
    )
    courses_completed = models.PositiveIntegerField(
        default=0,
        help_text="Students who completed all modules on this date"
    )

    # Chat metrics
    chat_messages = models.PositiveIntegerField(
        default=0,
        help_text="Chat messages sent on this date"
    )
    active_chat_users = models.PositiveIntegerField(
        default=0,
        help_text="Distinct users who sent messages"
    )

    class Meta:
        unique_together = ['course', 'date']
        ordering = ['course', '-date']
        indexes = [
            models.Index(fields=['course', '-date']),
            models.Index(fields=['-date']),
            models.Index(fields=['date', '-new_enrollments']),  # Top courses by enrollment
        ]
        verbose_name_plural = 'Daily course metrics'

    def __str__(self):
        return f"{self.course.title} - {self.date}"

    @property
    def view_to_enrollment_rate(self):
        """Conversion rate from views to enrollments"""
        if self.total_views > 0:
            return round((self.new_enrollments / self.total_views) * 100, 2)
        return 0

    @property
    def student_engagement_rate(self):
        """Percentage of enrolled students who were active"""
        if self.total_enrolled_students > 0:
            return round((self.active_students / self.total_enrolled_students) * 100, 2)
        return 0
```

**Use Case**: "Show me a 30-day trend chart of daily active students for Course X."

**Population Strategy**: Run a Celery beat task every night at 1 AM to aggregate previous day's data:

```python
# courses/tasks.py
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Avg, Sum
from .models import DailyCourseMetrics, CourseView, EnrollmentEvent, ContentInteraction


@shared_task
def aggregate_daily_course_metrics():
    """
    Aggregate yesterday's course metrics.
    Run this as a Celery beat task daily at 1 AM.
    """
    yesterday = timezone.now().date() - timedelta(days=1)

    from courses.models import Course
    for course in Course.objects.all():
        # Aggregate views
        views = CourseView.objects.filter(
            course=course,
            viewed_at__date=yesterday
        )
        total_views = views.count()
        unique_visitors = views.values('user', 'session_id').distinct().count()
        authenticated_views = views.filter(user__isnull=False).count()

        # Aggregate enrollments
        new_enrollments = EnrollmentEvent.objects.filter(
            course=course,
            event_type='enrolled',
            timestamp__date=yesterday
        ).count()

        # Calculate total enrolled up to yesterday
        total_enrolled = course.students.count()

        # Aggregate engagement
        interactions = ContentInteraction.objects.filter(
            content__module__course=course,
            timestamp__date=yesterday
        )
        active_students = interactions.values('student').distinct().count()

        # Calculate average time spent
        time_stats = interactions.aggregate(
            avg_time=Avg('time_spent_seconds')
        )

        # Create or update metric record
        DailyCourseMetrics.objects.update_or_create(
            course=course,
            date=yesterday,
            defaults={
                'total_views': total_views,
                'unique_visitors': unique_visitors,
                'authenticated_views': authenticated_views,
                'anonymous_views': total_views - authenticated_views,
                'new_enrollments': new_enrollments,
                'total_enrolled_students': total_enrolled,
                'active_students': active_students,
                'avg_time_spent_seconds': int(time_stats['avg_time'] or 0),
                'total_content_interactions': interactions.count(),
                # ... other fields
            }
        )
```

---

### 2. WeeklyStudentMetrics - Student Performance Rollup

**Purpose**: Weekly student performance summary for progress reports and retention analysis.

```python
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class WeeklyStudentMetrics(models.Model):
    """
    Weekly rollup of student activity and performance.
    Used for progress reports, retention analysis, and at-risk student identification.
    """
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='weekly_metrics'
    )
    week_start_date = models.DateField(
        help_text="Monday of the week these metrics represent"
    )

    # Engagement metrics
    active_days = models.PositiveIntegerField(
        default=0,
        help_text="Number of days with learning activity (0-7)"
    )
    total_time_spent_seconds = models.PositiveIntegerField(
        default=0,
        help_text="Total time spent across all courses"
    )
    courses_accessed = models.PositiveIntegerField(
        default=0,
        help_text="Number of distinct courses accessed"
    )

    # Progress metrics
    modules_started = models.PositiveIntegerField(
        default=0,
        help_text="New modules started this week"
    )
    modules_completed = models.PositiveIntegerField(
        default=0,
        help_text="Modules completed this week"
    )
    courses_completed = models.PositiveIntegerField(
        default=0,
        help_text="Full courses completed this week"
    )

    # Content interaction metrics
    videos_watched = models.PositiveIntegerField(
        default=0,
        help_text="Number of videos completed"
    )
    files_downloaded = models.PositiveIntegerField(
        default=0,
        help_text="Number of files downloaded"
    )

    # Social metrics
    chat_messages_sent = models.PositiveIntegerField(
        default=0,
        help_text="Chat messages sent this week"
    )

    # Streak metrics
    learning_streak_days = models.PositiveIntegerField(
        default=0,
        help_text="Snapshot of learning streak at end of week"
    )

    class Meta:
        unique_together = ['student', 'week_start_date']
        ordering = ['student', '-week_start_date']
        indexes = [
            models.Index(fields=['student', '-week_start_date']),
            models.Index(fields=['-week_start_date']),
            models.Index(fields=['week_start_date', '-modules_completed']),
        ]
        verbose_name_plural = 'Weekly student metrics'

    def __str__(self):
        return f"{self.student.username} - Week of {self.week_start_date}"

    @property
    def avg_daily_minutes(self):
        """Average minutes per active day"""
        if self.active_days > 0:
            return round((self.total_time_spent_seconds / 60) / self.active_days, 2)
        return 0

    @property
    def is_at_risk(self):
        """Flag students at risk of dropping out"""
        # At risk if less than 2 active days and no modules completed
        return self.active_days < 2 and self.modules_completed == 0

    @property
    def engagement_score(self):
        """
        Calculate engagement score (0-100).
        Weighted formula: active_days (40%) + completion (30%) + social (30%)
        """
        active_score = (self.active_days / 7) * 40
        completion_score = min(self.modules_completed * 10, 30)
        social_score = min(self.chat_messages_sent * 2, 30)
        return round(active_score + completion_score + social_score, 2)
```

**Use Case**: "Identify all students with engagement_score < 30 for retention email campaign."

---

### 3. MonthlyInstructorMetrics - Instructor Dashboard Metrics

**Purpose**: Monthly rollup of instructor course performance for instructor dashboard and payouts.

```python
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class MonthlyInstructorMetrics(models.Model):
    """
    Monthly rollup of instructor performance across all their courses.
    Used for instructor dashboards, performance reviews, and revenue attribution.
    """
    instructor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='monthly_instructor_metrics'
    )
    month_start_date = models.DateField(
        help_text="First day of the month these metrics represent"
    )

    # Course metrics
    total_courses = models.PositiveIntegerField(
        default=0,
        help_text="Total active courses by this instructor"
    )
    new_courses_created = models.PositiveIntegerField(
        default=0,
        help_text="Courses created this month"
    )

    # Enrollment metrics
    total_enrollments = models.PositiveIntegerField(
        default=0,
        help_text="Total cumulative enrollments across all courses"
    )
    new_enrollments = models.PositiveIntegerField(
        default=0,
        help_text="New enrollments this month"
    )

    # Engagement metrics
    total_course_views = models.PositiveIntegerField(
        default=0,
        help_text="Total views across all instructor courses"
    )
    active_students = models.PositiveIntegerField(
        default=0,
        help_text="Distinct students who accessed course content this month"
    )
    avg_completion_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.0,
        help_text="Average course completion rate (%)"
    )

    # Revenue metrics (if applicable)
    total_revenue = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.0,
        help_text="Total revenue generated this month"
    )

    # Student satisfaction (if reviews implemented)
    avg_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Average course rating (1-5 scale)"
    )
    total_reviews = models.PositiveIntegerField(
        default=0,
        help_text="Number of reviews received this month"
    )

    class Meta:
        unique_together = ['instructor', 'month_start_date']
        ordering = ['instructor', '-month_start_date']
        indexes = [
            models.Index(fields=['instructor', '-month_start_date']),
            models.Index(fields=['-month_start_date']),
        ]
        verbose_name_plural = 'Monthly instructor metrics'

    def __str__(self):
        return f"{self.instructor.username} - {self.month_start_date.strftime('%B %Y')}"

    @property
    def avg_enrollments_per_course(self):
        """Average enrollments per course"""
        if self.total_courses > 0:
            return round(self.total_enrollments / self.total_courses, 2)
        return 0

    @property
    def revenue_per_enrollment(self):
        """Average revenue per enrollment"""
        if self.new_enrollments > 0:
            return round(float(self.total_revenue) / self.new_enrollments, 2)
        return 0
```

**Use Case**: "Generate monthly instructor performance report for payouts."

---

## Django Implementation Guide

### Tracking Integration Points

#### 1. Course View Tracking (courses/views.py)

```python
# courses/views.py
from analytics.models import CourseView
from django.utils import timezone


class CourseDetailView(DetailView):
    model = Course
    template_name = 'courses/course/detail.html'

    def get_object(self):
        course = super().get_object()

        # Track course view
        CourseView.objects.create(
            course=course,
            user=self.request.user if self.request.user.is_authenticated else None,
            session_id=self.request.session.session_key or 'anonymous',
            referrer=self.request.META.get('HTTP_REFERER', ''),
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )

        return course

    def get_client_ip(self):
        """Extract client IP from request"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip
```

#### 2. Module Progress Tracking (students/views.py)

```python
# students/views.py
from analytics.models import ModuleProgress, LearningStreak
from django.utils import timezone


class StudentCourseDetailView(LoginRequiredMixin, DetailView):
    model = Course
    template_name = 'students/course/detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.get_object()

        if 'module_id' in self.kwargs:
            module = course.modules.get(id=self.kwargs['module_id'])
            context['module'] = module

            # Track module access
            progress, created = ModuleProgress.objects.get_or_create(
                student=self.request.user,
                module=module,
                defaults={'status': 'in_progress', 'started_at': timezone.now()}
            )

            if created:
                # First time accessing this module
                progress.status = 'in_progress'
                progress.started_at = timezone.now()
            else:
                # Update last accessed time
                progress.last_accessed_at = timezone.now()

            progress.save()

            # Update learning streak
            streak, _ = LearningStreak.objects.get_or_create(
                student=self.request.user
            )
            streak.update_streak()

            # Store in Redis for quick access (existing functionality)
            key = f'student:{self.request.user.id}:course:{course.id}:last_module'
            r.set(key, module.id)

        return context
```

#### 3. Content Interaction Tracking (JavaScript + API)

Create a JavaScript tracking snippet that sends heartbeat events:

```javascript
// static/js/analytics.js
class ContentTracker {
    constructor(contentId, contentType) {
        this.contentId = contentId;
        this.contentType = contentType;
        this.sessionId = this.getSessionId();
        this.startTime = Date.now();
        this.lastHeartbeat = Date.now();
        this.isActive = true;

        // Track initial view
        this.trackEvent('view');

        // Start heartbeat (send time spent every 30 seconds)
        this.heartbeatInterval = setInterval(() => {
            if (this.isActive) {
                this.sendHeartbeat();
            }
        }, 30000);

        // Track when user leaves
        window.addEventListener('beforeunload', () => {
            this.sendHeartbeat();
        });

        // Detect tab visibility changes
        document.addEventListener('visibilitychange', () => {
            this.isActive = !document.hidden;
        });
    }

    trackEvent(eventType, metadata = {}) {
        fetch('/api/analytics/content-interaction/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken()
            },
            body: JSON.stringify({
                content_id: this.contentId,
                interaction_type: eventType,
                session_id: this.sessionId,
                ...metadata
            })
        });
    }

    sendHeartbeat() {
        const timeSpent = Math.floor((Date.now() - this.lastHeartbeat) / 1000);
        this.trackEvent('heartbeat', { time_spent_seconds: timeSpent });
        this.lastHeartbeat = Date.now();
    }

    trackCompletion() {
        this.trackEvent('complete', { is_completed: true });
    }

    // Video-specific tracking
    trackVideoProgress(currentTime, duration) {
        this.trackEvent('pause', {
            video_position_seconds: Math.floor(currentTime),
            video_duration_seconds: Math.floor(duration)
        });
    }

    getSessionId() {
        // Get Django session ID from cookie
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'sessionid') {
                return value;
            }
        }
        return 'unknown';
    }

    getCsrfToken() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return value;
            }
        }
        return '';
    }
}

// Usage in course content template
document.addEventListener('DOMContentLoaded', () => {
    const contentId = document.getElementById('content-container').dataset.contentId;
    const contentType = document.getElementById('content-container').dataset.contentType;
    const tracker = new ContentTracker(contentId, contentType);

    // For videos
    const videoElement = document.querySelector('video');
    if (videoElement) {
        videoElement.addEventListener('ended', () => {
            tracker.trackCompletion();
        });

        videoElement.addEventListener('pause', () => {
            tracker.trackVideoProgress(videoElement.currentTime, videoElement.duration);
        });
    }
});
```

Backend API endpoint:

```python
# analytics/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from .models import ContentInteraction
from courses.models import Content


class ContentInteractionAPIView(APIView):
    """
    API endpoint for tracking content interactions.
    Called by JavaScript tracking code.
    """

    def post(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=401)

        content_id = request.data.get('content_id')
        interaction_type = request.data.get('interaction_type')
        session_id = request.data.get('session_id')

        try:
            content = Content.objects.get(id=content_id)
        except Content.DoesNotExist:
            return Response({'error': 'Content not found'}, status=404)

        # Create interaction record
        interaction = ContentInteraction.objects.create(
            student=request.user,
            content=content,
            interaction_type=interaction_type,
            session_id=session_id,
            time_spent_seconds=request.data.get('time_spent_seconds', 0),
            video_position_seconds=request.data.get('video_position_seconds'),
            video_duration_seconds=request.data.get('video_duration_seconds'),
            is_completed=request.data.get('is_completed', False)
        )

        # If completed, update module progress
        if interaction.is_completed:
            self.update_module_progress(request.user, content)

        return Response({'status': 'tracked'}, status=200)

    def update_module_progress(self, student, content):
        """Check if all content in module is completed"""
        from analytics.models import ModuleProgress

        module = content.module
        total_content = module.contents.count()
        completed_content = ContentInteraction.objects.filter(
            student=student,
            content__module=module,
            is_completed=True
        ).values('content').distinct().count()

        if total_content == completed_content:
            # All content completed, mark module as completed
            progress = ModuleProgress.objects.filter(
                student=student,
                module=module
            ).first()

            if progress and progress.status != 'completed':
                progress.status = 'completed'
                progress.completed_at = timezone.now()
                progress.save()
```

#### 4. Enrollment Event Tracking with Signals

```python
# analytics/signals.py
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from courses.models import Course
from .models import EnrollmentEvent
from django.utils import timezone


@receiver(m2m_changed, sender=Course.students.through)
def track_enrollment(sender, instance, action, pk_set, **kwargs):
    """
    Track when students enroll or unenroll from courses.
    Triggered by changes to Course.students M2M relationship.
    """
    if action == 'post_add':
        # Student(s) enrolled
        for student_id in pk_set:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            student = User.objects.get(pk=student_id)

            EnrollmentEvent.objects.create(
                student=student,
                course=instance,
                event_type='enrolled',
                timestamp=timezone.now()
            )

    elif action == 'post_remove':
        # Student(s) unenrolled
        for student_id in pk_set:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            student = User.objects.get(pk=student_id)

            EnrollmentEvent.objects.create(
                student=student,
                course=instance,
                event_type='unenrolled',
                timestamp=timezone.now()
            )


# In analytics/apps.py
from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'analytics'

    def ready(self):
        import analytics.signals
```

#### 5. Chat Activity Aggregation with Celery

```python
# analytics/tasks.py
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from chat.models import Message
from .models import ChatActivity


@shared_task
def aggregate_daily_chat_activity():
    """
    Aggregate yesterday's chat activity.
    Run daily at 1 AM via Celery beat.
    """
    yesterday = timezone.now().date() - timedelta(days=1)

    # Get all messages from yesterday
    messages = Message.objects.filter(
        sent_on__date=yesterday
    ).select_related('user', 'course')

    # Group by user and course
    from collections import defaultdict
    activity_data = defaultdict(lambda: {
        'messages': [],
        'total_chars': 0,
        'times': []
    })

    for message in messages:
        key = (message.user_id, message.course_id)
        activity_data[key]['messages'].append(message)
        activity_data[key]['total_chars'] += len(message.content)
        activity_data[key]['times'].append(message.sent_on.time())

    # Create ChatActivity records
    for (user_id, course_id), data in activity_data.items():
        ChatActivity.objects.update_or_create(
            student_id=user_id,
            course_id=course_id,
            date=yesterday,
            defaults={
                'messages_sent': len(data['messages']),
                'total_characters': data['total_chars'],
                'first_message_at': min(data['times']),
                'last_message_at': max(data['times'])
            }
        )
```

#### 6. Session Tracking Middleware

```python
# analytics/middleware.py
from django.utils import timezone
from .models import UserSession


class SessionTrackingMiddleware:
    """
    Middleware to track user sessions and activity.
    Records session start, updates activity, tracks page views.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.session.session_key:
            self.track_session(request)

        response = self.get_response(request)
        return response

    def track_session(self, request):
        session_key = request.session.session_key

        # Get or create session record
        session, created = UserSession.objects.get_or_create(
            session_key=session_key,
            defaults={
                'user': request.user,
                'started_at': timezone.now(),
                'ip_address': self.get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:500]
            }
        )

        if not created:
            # Update last activity and page view count
            session.last_activity_at = timezone.now()
            session.pages_viewed += 1
            session.save(update_fields=['last_activity_at', 'pages_viewed'])

        # Track which course is being accessed
        if 'course_id' in request.resolver_match.kwargs:
            course_id = request.resolver_match.kwargs['course_id']
            from courses.models import Course
            try:
                course = Course.objects.get(id=course_id)
                session.courses_accessed.add(course)
            except Course.DoesNotExist:
                pass

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


# Add to settings/base.py MIDDLEWARE
MIDDLEWARE = [
    # ... other middleware
    'analytics.middleware.SessionTrackingMiddleware',
]
```

---

## Reporting Queries

### Query 1: Top 10 Most Viewed Courses This Month

```python
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from analytics.models import DailyCourseMetrics

# Get first day of current month
today = timezone.now().date()
month_start = today.replace(day=1)

top_courses = DailyCourseMetrics.objects.filter(
    date__gte=month_start,
    date__lte=today
).values(
    'course__title',
    'course__id'
).annotate(
    total_views=Sum('total_views'),
    total_enrollments=Sum('new_enrollments')
).order_by('-total_views')[:10]

for course in top_courses:
    print(f"{course['course__title']}: {course['total_views']} views, {course['total_enrollments']} enrollments")
```

### Query 2: Course Completion Rate by Subject

```python
from django.db.models import Count, Q
from courses.models import Course, Subject
from analytics.models import ModuleProgress

# For each subject, calculate completion rate
subjects = Subject.objects.all()

for subject in subjects:
    courses = subject.courses.all()

    # Get total modules across all courses in subject
    total_modules = sum(course.modules.count() for course in courses)

    # Get completed modules
    completed_modules = ModuleProgress.objects.filter(
        module__course__subject=subject,
        status='completed'
    ).count()

    if total_modules > 0:
        completion_rate = (completed_modules / total_modules) * 100
        print(f"{subject.title}: {completion_rate:.2f}% completion rate")
```

### Query 3: Average Time to Complete a Course

```python
from django.db.models import Avg, F
from django.db.models.functions import ExtractEpoch
from analytics.models import EnrollmentEvent

# Calculate average days from enrollment to course completion
completion_times = EnrollmentEvent.objects.filter(
    event_type='course_completed'
).annotate(
    enrollment_event=EnrollmentEvent.objects.filter(
        student=F('student'),
        course=F('course'),
        event_type='enrolled'
    ).values('timestamp')[:1]
).annotate(
    days_to_complete=ExtractEpoch(F('timestamp') - F('enrollment_event')) / 86400
).aggregate(
    avg_days=Avg('days_to_complete')
)

print(f"Average time to complete a course: {completion_times['avg_days']:.1f} days")

# Alternative: using raw SQL for clarity
from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT
            course_id,
            c.title,
            AVG(EXTRACT(EPOCH FROM (completed.timestamp - enrolled.timestamp)) / 86400) as avg_days
        FROM analytics_enrollmentevent enrolled
        JOIN analytics_enrollmentevent completed
            ON enrolled.student_id = completed.student_id
            AND enrolled.course_id = completed.course_id
        JOIN courses_course c ON enrolled.course_id = c.id
        WHERE enrolled.event_type = 'enrolled'
        AND completed.event_type = 'course_completed'
        AND completed.timestamp > enrolled.timestamp
        GROUP BY course_id, c.title
        ORDER BY avg_days
    """)

    results = cursor.fetchall()
    for course_id, title, avg_days in results:
        print(f"{title}: {avg_days:.1f} days average")
```

### Query 4: Daily Active Users Trend (Last 30 Days)

```python
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
from analytics.models import ContentInteraction

# Get last 30 days
end_date = timezone.now().date()
start_date = end_date - timedelta(days=30)

# Count distinct active users per day
daily_active_users = ContentInteraction.objects.filter(
    timestamp__date__gte=start_date,
    timestamp__date__lte=end_date
).values('timestamp__date').annotate(
    dau=Count('student', distinct=True)
).order_by('timestamp__date')

for day in daily_active_users:
    print(f"{day['timestamp__date']}: {day['dau']} active users")

# Calculate 7-day moving average
import pandas as pd
df = pd.DataFrame(list(daily_active_users))
df['dau_7day_avg'] = df['dau'].rolling(window=7).mean()
```

### Query 5: Drop-off Point Analysis (Which Module Do Students Quit?)

```python
from django.db.models import Count, Q
from courses.models import Course
from analytics.models import ModuleProgress

def analyze_course_dropoff(course_id):
    """
    Analyze where students drop off in a course.
    Returns completion rate for each module.
    """
    course = Course.objects.get(id=course_id)
    total_students = course.students.count()

    if total_students == 0:
        print("No students enrolled")
        return

    print(f"\n=== Drop-off Analysis for '{course.title}' ===")
    print(f"Total enrolled students: {total_students}\n")

    for module in course.modules.all().order_by('order'):
        # Count students who started this module
        started = ModuleProgress.objects.filter(
            module=module,
            status__in=['in_progress', 'completed']
        ).count()

        # Count students who completed this module
        completed = ModuleProgress.objects.filter(
            module=module,
            status='completed'
        ).count()

        # Calculate rates
        start_rate = (started / total_students) * 100 if total_students > 0 else 0
        completion_rate = (completed / started) * 100 if started > 0 else 0

        print(f"Module {module.order}: {module.title}")
        print(f"  Started: {started}/{total_students} ({start_rate:.1f}%)")
        print(f"  Completed: {completed}/{started} ({completion_rate:.1f}%)")
        print(f"  Drop-off: {started - completed} students")
        print()

# Usage
analyze_course_dropoff(1)
```

### Query 6: Instructor Performance Dashboard Data

```python
from django.db.models import Count, Avg, Sum
from django.utils import timezone
from datetime import timedelta
from courses.models import Course
from analytics.models import DailyCourseMetrics, ModuleProgress

def instructor_dashboard(instructor_id):
    """
    Generate comprehensive instructor performance metrics.
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    instructor = User.objects.get(id=instructor_id)

    # Get all instructor courses
    courses = Course.objects.filter(owner=instructor)

    # Last 30 days
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)

    # Aggregate metrics
    metrics = DailyCourseMetrics.objects.filter(
        course__in=courses,
        date__gte=start_date,
        date__lte=end_date
    ).aggregate(
        total_views=Sum('total_views'),
        total_enrollments=Sum('new_enrollments'),
        avg_engagement_rate=Avg('student_engagement_rate')
    )

    # Calculate overall completion rate
    total_modules = sum(course.modules.count() for course in courses)
    completed_modules = ModuleProgress.objects.filter(
        module__course__in=courses,
        status='completed'
    ).count()

    completion_rate = (completed_modules / total_modules * 100) if total_modules > 0 else 0

    return {
        'instructor_name': instructor.get_full_name() or instructor.username,
        'total_courses': courses.count(),
        'total_students': sum(course.students.count() for course in courses),
        'views_last_30_days': metrics['total_views'] or 0,
        'enrollments_last_30_days': metrics['total_enrollments'] or 0,
        'avg_engagement_rate': metrics['avg_engagement_rate'] or 0,
        'overall_completion_rate': completion_rate
    }

# Usage
dashboard_data = instructor_dashboard(1)
for key, value in dashboard_data.items():
    print(f"{key}: {value}")
```

### Query 7: Student Engagement Score Calculation

```python
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta
from analytics.models import ModuleProgress, ContentInteraction, ChatActivity, LearningStreak

def calculate_student_engagement_score(student_id, course_id=None):
    """
    Calculate comprehensive engagement score (0-100) for a student.
    Optionally filter by specific course.

    Scoring breakdown:
    - Activity frequency (30 points): Based on active days and streak
    - Content completion (30 points): Based on modules/courses completed
    - Time investment (20 points): Based on time spent
    - Social engagement (20 points): Based on chat participation
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    student = User.objects.get(id=student_id)

    # Last 30 days
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)

    # Filter by course if specified
    course_filter = {'content__module__course_id': course_id} if course_id else {}
    module_filter = {'module__course_id': course_id} if course_id else {}
    chat_filter = {'course_id': course_id} if course_id else {}

    # 1. Activity Frequency (30 points)
    active_days = ContentInteraction.objects.filter(
        student=student,
        timestamp__date__gte=start_date,
        **course_filter
    ).dates('timestamp', 'day').count()

    streak = LearningStreak.objects.filter(student=student).first()
    streak_days = streak.current_streak_days if streak else 0

    activity_score = min((active_days / 30) * 20 + (streak_days / 7) * 10, 30)

    # 2. Content Completion (30 points)
    total_modules = ModuleProgress.objects.filter(
        student=student,
        **module_filter
    ).count()

    completed_modules = ModuleProgress.objects.filter(
        student=student,
        status='completed',
        **module_filter
    ).count()

    completion_rate = (completed_modules / total_modules) if total_modules > 0 else 0
    completion_score = completion_rate * 30

    # 3. Time Investment (20 points)
    total_time = ContentInteraction.objects.filter(
        student=student,
        timestamp__date__gte=start_date,
        **course_filter
    ).aggregate(total=Sum('time_spent_seconds'))['total'] or 0

    # Aim for 10 hours (36000 seconds) in 30 days as "full engagement"
    time_score = min((total_time / 36000) * 20, 20)

    # 4. Social Engagement (20 points)
    chat_messages = ChatActivity.objects.filter(
        student=student,
        date__gte=start_date,
        **chat_filter
    ).aggregate(total=Sum('messages_sent'))['total'] or 0

    # Aim for 50 messages in 30 days as "full engagement"
    social_score = min((chat_messages / 50) * 20, 20)

    # Total score
    total_score = activity_score + completion_score + time_score + social_score

    return {
        'student': student.username,
        'total_score': round(total_score, 2),
        'activity_score': round(activity_score, 2),
        'completion_score': round(completion_score, 2),
        'time_score': round(time_score, 2),
        'social_score': round(social_score, 2),
        'active_days': active_days,
        'streak_days': streak_days,
        'completed_modules': completed_modules,
        'total_modules': total_modules,
        'time_spent_hours': round(total_time / 3600, 2),
        'chat_messages': chat_messages
    }

# Usage
score = calculate_student_engagement_score(student_id=1, course_id=5)
print(f"Engagement Score: {score['total_score']}/100")
print(f"  Activity: {score['activity_score']}/30")
print(f"  Completion: {score['completion_score']}/30")
print(f"  Time: {score['time_score']}/20")
print(f"  Social: {score['social_score']}/20")
```

---

## Data Retention & Privacy

### GDPR Compliance Strategy

**Principle 1: Data Minimization**
- Collect only essential analytics data
- Don't store personally identifiable information (PII) beyond user ID
- Anonymize IP addresses to country/region level after initial collection

**Principle 2: Purpose Limitation**
- All analytics data used solely for platform improvement and student success
- Never sold or shared with third parties
- Clear privacy policy explaining data usage

**Principle 3: Storage Limitation**
- **Raw event data**: Retain for 90 days, then delete
- **Aggregated metrics**: Retain for 2 years (no PII)
- **User-requested deletion**: Anonymize within 30 days

### Retention Policy Implementation

```python
# analytics/management/commands/cleanup_analytics.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from analytics.models import (
    CourseView, ContentInteraction, EnrollmentEvent,
    UserSession, ChatActivity
)


class Command(BaseCommand):
    help = 'Clean up old analytics data based on retention policy'

    def handle(self, *args, **options):
        # Delete raw events older than 90 days
        cutoff_date = timezone.now() - timedelta(days=90)

        deleted_views = CourseView.objects.filter(
            viewed_at__lt=cutoff_date
        ).delete()[0]

        deleted_interactions = ContentInteraction.objects.filter(
            timestamp__lt=cutoff_date
        ).delete()[0]

        deleted_sessions = UserSession.objects.filter(
            started_at__lt=cutoff_date
        ).delete()[0]

        # Anonymize IP addresses older than 90 days
        CourseView.objects.filter(
            viewed_at__lt=cutoff_date,
            ip_address__isnull=False
        ).update(ip_address=None)

        UserSession.objects.filter(
            started_at__lt=cutoff_date,
            ip_address__isnull=False
        ).update(ip_address=None)

        self.stdout.write(
            self.style.SUCCESS(
                f'Deleted {deleted_views} course views, '
                f'{deleted_interactions} interactions, '
                f'{deleted_sessions} sessions'
            )
        )

        # Aggregated data cleanup (2 years)
        aggregated_cutoff = timezone.now().date() - timedelta(days=730)

        from analytics.models import DailyCourseMetrics
        deleted_metrics = DailyCourseMetrics.objects.filter(
            date__lt=aggregated_cutoff
        ).delete()[0]

        self.stdout.write(
            self.style.SUCCESS(
                f'Deleted {deleted_metrics} aggregated metric records'
            )
        )
```

Run this command via cron or Celery beat:

```python
# In celerybeat_schedule
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'cleanup-analytics-daily': {
        'task': 'analytics.tasks.cleanup_analytics_data',
        'schedule': crontab(hour=3, minute=0),  # 3 AM daily
    },
}
```

### User Data Anonymization

```python
# analytics/utils.py
from django.contrib.auth import get_user_model
from analytics.models import (
    CourseView, ContentInteraction, EnrollmentEvent,
    ModuleProgress, ChatActivity, UserSession,
    WeeklyStudentMetrics, LearningStreak
)

User = get_user_model()


def anonymize_user_analytics(user_id):
    """
    Anonymize all analytics data for a specific user.
    Called when user requests data deletion (GDPR right to be forgotten).
    """
    # Delete personal progress data
    ModuleProgress.objects.filter(student_id=user_id).delete()
    LearningStreak.objects.filter(student_id=user_id).delete()
    WeeklyStudentMetrics.objects.filter(student_id=user_id).delete()

    # Anonymize event data (set user to NULL but keep events for aggregates)
    CourseView.objects.filter(user_id=user_id).update(user=None)
    ContentInteraction.objects.filter(student_id=user_id).update(student=None)
    EnrollmentEvent.objects.filter(student_id=user_id).update(student=None)
    ChatActivity.objects.filter(student_id=user_id).update(student=None)

    # Delete session data (contains IP addresses)
    UserSession.objects.filter(user_id=user_id).delete()

    return True
```

---

## Migration Strategy

### Step 1: Create Analytics App

```bash
cd config_educa
python manage.py startapp analytics
```

Add to `INSTALLED_APPS` in `settings/base.py`:

```python
INSTALLED_APPS = [
    # ... existing apps
    'analytics.apps.AnalyticsConfig',
]
```

### Step 2: Create Models Incrementally

Create models in this order to avoid dependency issues:

**Phase 1: Core Event Models (Week 1)**
- CourseView
- EnrollmentEvent
- ModuleProgress

**Phase 2: Content Tracking (Week 2)**
- ContentInteraction
- UserSession
- LearningStreak

**Phase 3: Social & Aggregates (Week 3)**
- ChatActivity
- DailyCourseMetrics
- WeeklyStudentMetrics
- MonthlyInstructorMetrics

### Step 3: Run Migrations

```bash
python manage.py makemigrations analytics
python manage.py migrate analytics
```

### Step 4: Integrate Tracking Code

Add tracking code to views progressively:
1. Start with CourseView tracking (simplest)
2. Add ModuleProgress tracking
3. Implement JavaScript content tracking
4. Add signals for enrollment
5. Deploy middleware for sessions

### Step 5: Backfill Historical Data (Optional)

If you have historical enrollment data in `Course.students`:

```python
# analytics/management/commands/backfill_enrollments.py
from django.core.management.base import BaseCommand
from courses.models import Course
from analytics.models import EnrollmentEvent
from django.utils import timezone


class Command(BaseCommand):
    help = 'Backfill enrollment events from existing Course.students data'

    def handle(self, *args, **options):
        for course in Course.objects.all():
            for student in course.students.all():
                # Create historical enrollment event
                # Use course created date as enrollment timestamp (approximation)
                EnrollmentEvent.objects.get_or_create(
                    student=student,
                    course=course,
                    event_type='enrolled',
                    defaults={
                        'timestamp': course.created,
                        'metadata': {'source': 'backfill'}
                    }
                )

        self.stdout.write(self.style.SUCCESS('Backfill complete'))
```

---

## Performance Considerations

### Index Strategy

All models include strategic indexes:
- **Time-series queries**: Index on timestamp/date fields (descending)
- **Foreign key lookups**: Composite indexes on (student, course, timestamp)
- **Aggregation queries**: Indexes on grouping fields (course, date)

### Database Partitioning for Large Tables

For platforms with 100K+ students, partition time-series tables by month:

```python
# analytics/models.py (PostgreSQL-specific)
from django.db import models


class ContentInteraction(models.Model):
    # ... fields ...

    class Meta:
        indexes = [
            models.Index(fields=['student', 'content', '-timestamp']),
        ]
        # PostgreSQL partitioning (requires raw SQL)
        # See: https://www.postgresql.org/docs/current/ddl-partitioning.html
```

SQL to create partitioned table:

```sql
-- Create parent table
CREATE TABLE analytics_contentinteraction_partitioned (
    LIKE analytics_contentinteraction INCLUDING ALL
) PARTITION BY RANGE (timestamp);

-- Create monthly partitions
CREATE TABLE analytics_contentinteraction_2025_01
    PARTITION OF analytics_contentinteraction_partitioned
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE analytics_contentinteraction_2025_02
    PARTITION OF analytics_contentinteraction_partitioned
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
-- ... continue for each month
```

### Read Replica for Analytics Queries

Configure a read replica in `settings/prod.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB'),
        'USER': os.environ.get('POSTGRES_USER'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD'),
        'HOST': 'db',
        'PORT': 5432,
    },
    'analytics_replica': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB'),
        'USER': os.environ.get('POSTGRES_USER'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD'),
        'HOST': 'db-replica',  # Read replica host
        'PORT': 5432,
    }
}

# Database router for analytics
class AnalyticsRouter:
    """
    Route analytics reads to replica database.
    """
    analytics_models = [
        'CourseView', 'ContentInteraction', 'EnrollmentEvent',
        'ModuleProgress', 'ChatActivity', 'UserSession',
        'DailyCourseMetrics', 'WeeklyStudentMetrics'
    ]

    def db_for_read(self, model, **hints):
        if model._meta.model_name in self.analytics_models:
            return 'analytics_replica'
        return 'default'

    def db_for_write(self, model, **hints):
        # All writes go to primary
        return 'default'

DATABASE_ROUTERS = ['analytics.routers.AnalyticsRouter']
```

### Caching Frequently Accessed Metrics

Cache expensive dashboard queries with Redis:

```python
# analytics/views.py
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page


class InstructorDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'analytics/instructor_dashboard.html'

    @method_decorator(cache_page(60 * 15))  # Cache for 15 minutes
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Try cache first
        cache_key = f'instructor_metrics_{self.request.user.id}'
        metrics = cache.get(cache_key)

        if not metrics:
            # Calculate metrics (expensive query)
            metrics = instructor_dashboard(self.request.user.id)
            # Cache for 15 minutes
            cache.set(cache_key, metrics, 60 * 15)

        context['metrics'] = metrics
        return context
```

---

## Summary

This analytics database schema provides comprehensive tracking across the Educto platform:

**7 Core Event Models**: CourseView, ModuleProgress, ContentInteraction, EnrollmentEvent, ChatActivity, UserSession, LearningStreak

**3 Aggregated Tables**: DailyCourseMetrics, WeeklyStudentMetrics, MonthlyInstructorMetrics

**Key Benefits**:
- **Actionable insights** for instructors (completion rates, drop-off points)
- **Motivation & gamification** for students (streaks, progress tracking)
- **Strategic data** for admins (retention, popular courses, platform health)
- **GDPR compliant** with clear retention policies and anonymization
- **Scalable** with indexes, partitioning, and read replicas
- **Practical** Django ORM queries for common reporting needs

**Implementation Timeline**:
- Week 1: Core models + basic tracking
- Week 2: Content tracking + JavaScript integration
- Week 3: Aggregation tasks + dashboards
- Week 4: Testing, optimization, GDPR compliance

This schema balances granular tracking with performance, privacy with insights, and complexity with maintainability. It's production-ready for a platform with 10K+ students and 1K+ courses.
