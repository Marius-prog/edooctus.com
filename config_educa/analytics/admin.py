from django.contrib import admin
from .models import (
    CourseView, ModuleProgress, ContentInteraction,
    EnrollmentEvent, UserSession, LearningStreak
)


@admin.register(CourseView)
class CourseViewAdmin(admin.ModelAdmin):
    list_display = ['course', 'user', 'viewed_at', 'referrer']
    list_filter = ['viewed_at', 'course']
    search_fields = ['course__title', 'user__username', 'session_id']
    date_hierarchy = 'viewed_at'
    readonly_fields = ['viewed_at']


@admin.register(ModuleProgress)
class ModuleProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'module', 'status', 'started_at', 'completed_at', 'last_accessed']
    list_filter = ['status', 'last_accessed']
    search_fields = ['user__username', 'module__title']
    date_hierarchy = 'last_accessed'


@admin.register(ContentInteraction)
class ContentInteractionAdmin(admin.ModelAdmin):
    list_display = ['user', 'content', 'interaction_type', 'timestamp', 'completed']
    list_filter = ['interaction_type', 'completed', 'timestamp']
    search_fields = ['user__username', 'content__id']
    date_hierarchy = 'timestamp'


@admin.register(EnrollmentEvent)
class EnrollmentEventAdmin(admin.ModelAdmin):
    list_display = ['user', 'course', 'event_type', 'timestamp']
    list_filter = ['event_type', 'timestamp']
    search_fields = ['user__username', 'course__title']
    date_hierarchy = 'timestamp'


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'started_at', 'last_activity', 'duration_display']
    list_filter = ['started_at']
    search_fields = ['user__username', 'session_key']
    date_hierarchy = 'started_at'

    def duration_display(self, obj):
        return f"{obj.duration_minutes:.1f} min"
    duration_display.short_description = 'Duration'


@admin.register(LearningStreak)
class LearningStreakAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'modules_completed', 'time_spent_minutes']
    list_filter = ['date']
    search_fields = ['user__username']
    date_hierarchy = 'date'
