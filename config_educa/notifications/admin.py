from django.contrib import admin
from .models import Notification, NotificationPreference


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "kind", "title", "channel", "is_read", "created")
    list_filter = ("kind", "channel", "is_read")
    search_fields = ("user__username", "title", "body")


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "email_enabled", "push_enabled", "in_app_enabled", "marketing")
