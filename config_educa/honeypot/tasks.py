"""Async alert dispatch for honeypot events (mirrors notifications/tasks.py)."""
from celery import shared_task
from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail


@shared_task(name="honeypot.dispatch_alert")
def dispatch_alert(event_id: int) -> bool:
    """Email the security list and notify superusers in-app about one event."""
    from .models import HoneypotEvent

    try:
        event = HoneypotEvent.objects.get(pk=event_id)
    except HoneypotEvent.DoesNotExist:
        return False

    subject = f"[Educto Security] Honeypot: {event.get_event_type_display()}"
    body = (
        "A honeypot lure was triggered.\n\n"
        f"Type:     {event.get_event_type_display()}\n"
        f"Path:     {event.path}\n"
        f"Method:   {event.method}\n"
        f"Source IP:{event.ip_address}\n"
        f"User-Agent:{event.user_agent}\n"
        f"Username: {event.attempted_username or '-'}\n"
        f"When:     {event.created:%Y-%m-%d %H:%M:%S} UTC\n\n"
        "Review the honeypot dashboard for context."
    )

    emails = [e for e in getattr(settings, "SECURITY_ALERT_EMAILS", []) if e]
    if emails:
        send_mail(
            subject, body,
            getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@educto.io"),
            emails, fail_silently=True,
        )

    try:
        from notifications.models import notify, CHANNEL_IN_APP
        for u in User.objects.filter(is_superuser=True, is_active=True):
            notify(u, "security_alert", title=subject, body=body,
                   link="/honeypot/dashboard/", channel=CHANNEL_IN_APP,
                   metadata={"event_id": event.id, "ip": event.ip_address})
    except Exception:  # pragma: no cover — notifications optional
        pass

    return True


@shared_task(name="honeypot.analyze")
def analyze_recent(hours: int = 1) -> dict:
    """Hourly aggregation hook (beat). Returns a small summary for logs/metrics."""
    from datetime import timedelta
    from django.db.models import Count
    from django.utils import timezone
    from .models import HoneypotEvent

    since = timezone.now() - timedelta(hours=hours)
    qs = HoneypotEvent.objects.filter(created__gte=since)
    return {
        "window_hours": hours,
        "events": qs.count(),
        "unique_ips": qs.values("ip_address").distinct().count(),
        "by_type": list(qs.values("event_type").annotate(n=Count("id")).order_by("-n")),
    }
