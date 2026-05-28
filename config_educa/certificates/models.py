from django.db import models
from django.contrib.auth.models import User
from courses.models import Course
from django.utils import timezone
import uuid


class Certificate(models.Model):
    """Course completion certificate"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='certificates')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='certificates')
    certificate_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    issued_at = models.DateTimeField(default=timezone.now)
    completion_date = models.DateField(auto_now_add=True)
    grade = models.CharField(max_length=10, blank=True, help_text="e.g., A, B+, Pass")

    # Verification
    verification_code = models.CharField(max_length=50, unique=True, editable=False)
    is_valid = models.BooleanField(default=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_reason = models.TextField(blank=True)

    # Analytics
    download_count = models.IntegerField(default=0)
    last_downloaded = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['user', 'course']
        ordering = ['-issued_at']
        indexes = [
            models.Index(fields=['user', '-issued_at']),
            models.Index(fields=['certificate_id']),
            models.Index(fields=['verification_code']),
        ]
        verbose_name = 'Certificate'
        verbose_name_plural = 'Certificates'

    def __str__(self):
        return f"Certificate: {self.user.username} - {self.course.title}"

    def save(self, *args, **kwargs):
        if not self.verification_code:
            self.verification_code = self.generate_verification_code()
        super().save(*args, **kwargs)

    @staticmethod
    def generate_verification_code():
        """Generate unique verification code"""
        import random
        import string
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
            if not Certificate.objects.filter(verification_code=code).exists():
                return code

    def revoke(self, reason=''):
        """Revoke certificate"""
        self.is_valid = False
        self.revoked_at = timezone.now()
        self.revoked_reason = reason
        self.save()

    def track_download(self):
        """Track certificate download"""
        self.download_count += 1
        self.last_downloaded = timezone.now()
        self.save(update_fields=['download_count', 'last_downloaded'])


class CertificateTemplate(models.Model):
    """Custom certificate templates"""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    html_template = models.TextField(help_text="HTML template with placeholders")
    css_styles = models.TextField(blank=True, help_text="Custom CSS for certificate")
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', 'name']
        verbose_name = 'Certificate Template'
        verbose_name_plural = 'Certificate Templates'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Ensure only one default template"""
        if self.is_default:
            CertificateTemplate.objects.filter(is_default=True).update(is_default=False)
        super().save(*args, **kwargs)
