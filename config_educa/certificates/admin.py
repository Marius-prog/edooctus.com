from django.contrib import admin
from .models import Certificate, CertificateTemplate


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ['user', 'course', 'certificate_id', 'issued_at', 'is_valid', 'download_count']
    list_filter = ['is_valid', 'issued_at']
    search_fields = ['user__username', 'course__title', 'certificate_id', 'verification_code']
    readonly_fields = ['certificate_id', 'verification_code', 'issued_at', 'download_count', 'last_downloaded']
    date_hierarchy = 'issued_at'
    actions = ['revoke_certificates']

    def revoke_certificates(self, request, queryset):
        for cert in queryset:
            cert.revoke('Revoked by admin')
        self.message_user(request, f'{queryset.count()} certificates revoked.')
    revoke_certificates.short_description = 'Revoke selected certificates'


@admin.register(CertificateTemplate)
class CertificateTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_default', 'created_at']
    list_filter = ['is_default']
    search_fields = ['name', 'description']
