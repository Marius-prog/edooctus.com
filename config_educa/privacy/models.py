"""GDPR / CCPA compliance models.

- Consent records (versioned cookie + ToS + marketing consent)
- DataExportRequest (right to access — Article 15 GDPR)
- DataDeletionRequest (right to erasure — Article 17 GDPR)
"""
import secrets
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class ConsentRecord(models.Model):
    """Versioned consent. New version of TOS/privacy policy \u2192 new record."""

    KIND_CHOICES = [
        ("tos", "Terms of Service"),
        ("privacy", "Privacy Policy"),
        ("cookies", "Cookie Consent"),
        ("marketing", "Marketing Communications"),
        ("data_processing", "Data Processing (GDPR)"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="consents")
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    version = models.CharField(max_length=20, help_text="e.g. '2024-10-01' or 'v3'.")
    granted = models.BooleanField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    granted_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-granted_at"]
        indexes = [
            models.Index(fields=["user", "kind", "-granted_at"]),
            models.Index(fields=["kind", "version"]),
        ]

    def __str__(self):
        return f"{self.user} - {self.kind} v{self.version} = {self.granted}"

    def revoke(self):
        self.revoked_at = timezone.now()
        self.granted = False
        self.save(update_fields=["revoked_at", "granted"])

    @classmethod
    def latest(cls, user, kind: str):
        return cls.objects.filter(user=user, kind=kind).order_by("-granted_at").first()


class DataExportRequest(models.Model):
    """GDPR Art. 15: user can request all their data."""

    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_READY = "ready"
    STATUS_DOWNLOADED = "downloaded"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_READY, "Ready"),
        (STATUS_DOWNLOADED, "Downloaded"),
        (STATUS_FAILED, "Failed"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="data_exports")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_PENDING)
    requested_at = models.DateTimeField(auto_now_add=True)
    ready_at = models.DateTimeField(null=True, blank=True)
    downloaded_at = models.DateTimeField(null=True, blank=True)
    file = models.FileField(upload_to="privacy/exports/", null=True, blank=True)
    download_token = models.CharField(max_length=64, unique=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-requested_at"]

    def save(self, *args, **kwargs):
        if not self.download_token:
            self.download_token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Export {self.user} ({self.status})"


class DataDeletionRequest(models.Model):
    """GDPR Art. 17: right to erasure / 'be forgotten'."""

    STATUS_PENDING = "pending"
    STATUS_VERIFIED = "verified"
    STATUS_SCHEDULED = "scheduled"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELED = "canceled"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending verification"),
        (STATUS_VERIFIED, "Verified"),
        (STATUS_SCHEDULED, "Scheduled"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELED, "Canceled"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="deletion_requests")
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_PENDING)
    verification_token = models.CharField(max_length=64, unique=True, blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    scheduled_for = models.DateTimeField(null=True, blank=True,
                                         help_text="Grace period before hard-delete.")
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-requested_at"]

    def save(self, *args, **kwargs):
        if not self.verification_token:
            self.verification_token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Deletion {self.user} ({self.status})"


# -- Service ------------------------------------------------------------------

def record_consent(user, kind: str, version: str, granted: bool,
                   ip_address: str = "", user_agent: str = "") -> ConsentRecord:
    return ConsentRecord.objects.create(
        user=user, kind=kind, version=version, granted=granted,
        ip_address=ip_address or None, user_agent=user_agent,
    )


def has_active_consent(user, kind: str) -> bool:
    rec = ConsentRecord.latest(user, kind)
    return bool(rec and rec.granted and rec.revoked_at is None)
