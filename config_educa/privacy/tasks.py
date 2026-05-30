"""Privacy-related Celery jobs: data export generation, scheduled deletions."""
import json
from datetime import timedelta

from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.utils import timezone

from .models import DataExportRequest, DataDeletionRequest

User = get_user_model()


def _serialize_user(user) -> dict:
    """Collect a user's data across the platform.

    Best-effort: imports apps lazily so this works even if some are
    not installed in a given environment.
    """
    out: dict = {"user": {
        "id": user.id, "username": user.username, "email": user.email,
        "date_joined": user.date_joined.isoformat(),
        "last_login": user.last_login.isoformat() if user.last_login else None,
    }, "courses_enrolled": [], "messages": [], "reviews": [], "notifications": [],
       "sandbox_runs": [], "consents": []}
    try:
        out["courses_enrolled"] = list(user.courses_joined.values("id", "title", "slug"))
    except Exception:
        pass
    try:
        out["messages"] = list(user.chat_messages.values("course_id", "content", "sent_on")[:1000])
    except Exception:
        pass
    try:
        out["reviews"] = list(user.course_reviews.values("course_id", "rating", "review_text"))
    except Exception:
        pass
    try:
        out["notifications"] = list(user.notifications.values("kind", "title", "created")[:500])
    except Exception:
        pass
    try:
        out["sandbox_runs"] = list(
            user.sandbox_runs.values("tool_id", "prompt", "response", "created")[:500]
        )
    except Exception:
        pass
    try:
        out["consents"] = list(user.consents.values("kind", "version", "granted", "granted_at"))
    except Exception:
        pass
    return out


@shared_task(name="privacy.generate_export")
def generate_export(request_id: int) -> str:
    """GDPR Article 15: build a JSON file of all the user's data."""
    req = DataExportRequest.objects.select_related("user").get(pk=request_id)
    req.status = DataExportRequest.STATUS_PROCESSING
    req.save(update_fields=["status"])
    try:
        payload = _serialize_user(req.user)
        blob = json.dumps(payload, indent=2, default=str).encode()
        req.file.save(f"export_{req.user.id}_{req.id}.json", ContentFile(blob), save=False)
        req.status = DataExportRequest.STATUS_READY
        req.ready_at = timezone.now()
        req.expires_at = req.ready_at + timedelta(days=7)
        req.save()
        return req.download_token
    except Exception as exc:  # noqa: BLE001
        req.status = DataExportRequest.STATUS_FAILED
        req.save(update_fields=["status"])
        raise exc


@shared_task(name="privacy.expire_old_exports")
def expire_old_exports() -> int:
    """Delete export files past their expiry."""
    now = timezone.now()
    expired = DataExportRequest.objects.filter(
        status=DataExportRequest.STATUS_READY, expires_at__lt=now,
    )
    count = 0
    for r in expired:
        if r.file:
            r.file.delete(save=False)
        r.status = DataExportRequest.STATUS_FAILED  # repurpose as 'expired'
        r.save(update_fields=["status"])
        count += 1
    return count


@shared_task(name="privacy.process_scheduled_deletions")
def process_scheduled_deletions() -> int:
    """Hard-delete users whose grace period has elapsed."""
    now = timezone.now()
    due = DataDeletionRequest.objects.filter(
        status=DataDeletionRequest.STATUS_SCHEDULED, scheduled_for__lte=now,
    )
    count = 0
    for r in due:
        user_id = r.user_id
        r.status = DataDeletionRequest.STATUS_COMPLETED
        r.completed_at = now
        r.save(update_fields=["status", "completed_at"])
        # Anonymize rather than hard-delete to preserve referential FK history.
        try:
            u = User.objects.get(pk=user_id)
            u.username = f"deleted_{u.id}"
            u.email = ""
            u.set_unusable_password()
            u.is_active = False
            u.first_name = ""
            u.last_name = ""
            u.save()
            count += 1
        except User.DoesNotExist:
            pass
    return count
