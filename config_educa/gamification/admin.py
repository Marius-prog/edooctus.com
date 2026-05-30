from django.contrib import admin
from .models import Badge, UserBadge, PointsTransaction


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ("name", "rule_code", "points_reward", "is_active")
    list_filter = ("is_active",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ("user", "badge", "awarded_at")
    list_filter = ("badge",)


@admin.register(PointsTransaction)
class PointsTransactionAdmin(admin.ModelAdmin):
    list_display = ("user", "delta", "reason", "created")
    list_filter = ("reason",)
    search_fields = ("user__username", "reason")
