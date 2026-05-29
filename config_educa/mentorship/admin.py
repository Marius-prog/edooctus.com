from django.contrib import admin
from .models import MentorProfile, MentorshipRequest, MentorshipSession


@admin.register(MentorProfile)
class MentorProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "is_accepting", "max_active_mentees", "avg_rating", "total_sessions")
    list_filter = ("is_accepting",)


@admin.register(MentorshipRequest)
class MentorshipRequestAdmin(admin.ModelAdmin):
    list_display = ("mentee", "mentor", "status", "created", "responded_at")
    list_filter = ("status",)


@admin.register(MentorshipSession)
class MentorshipSessionAdmin(admin.ModelAdmin):
    list_display = ("pairing", "scheduled_at", "duration_minutes", "completed")
    list_filter = ("completed",)
