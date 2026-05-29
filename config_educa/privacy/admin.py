from django.contrib import admin
from .models import ConsentRecord, DataExportRequest, DataDeletionRequest


@admin.register(ConsentRecord)
class ConsentRecordAdmin(admin.ModelAdmin):
    list_display = ("user", "kind", "version", "granted", "granted_at", "revoked_at")
    list_filter = ("kind", "granted")
    search_fields = ("user__username",)


@admin.register(DataExportRequest)
class DataExportRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "requested_at", "ready_at", "expires_at")
    list_filter = ("status",)
    readonly_fields = ("download_token",)


@admin.register(DataDeletionRequest)
class DataDeletionRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "requested_at", "scheduled_for", "completed_at")
    list_filter = ("status",)
    readonly_fields = ("verification_token",)
