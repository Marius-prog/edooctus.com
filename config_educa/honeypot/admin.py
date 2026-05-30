from django.contrib import admin

from .models import DecoyAccount, HoneypotEvent


@admin.register(HoneypotEvent)
class HoneypotEventAdmin(admin.ModelAdmin):
    list_display = ("created", "event_type", "ip_address", "path",
                    "attempted_username", "method")
    list_filter = ("event_type", "created")
    search_fields = ("ip_address", "path", "attempted_username", "user_agent")
    date_hierarchy = "created"
    ordering = ("-created",)

    def has_add_permission(self, request):  # append-only via lures, not by hand
        return False

    def has_change_permission(self, request, obj=None):
        return False  # read-only log


@admin.register(DecoyAccount)
class DecoyAccountAdmin(admin.ModelAdmin):
    list_display = ("username", "display_role", "email", "created")
    search_fields = ("username", "email")
