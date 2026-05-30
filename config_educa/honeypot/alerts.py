"""Record honeypot events and fan out alerts (throttled per source IP)."""
from datetime import timedelta

from django.utils import timezone

from .models import HoneypotEvent
from .utils import client_ip, user_agent, referer, hash_password

ALERT_WINDOW = timedelta(hours=1)


def record_event(request, event_type, *, attempted_username="",
                 attempted_password="", metadata=None) -> HoneypotEvent:
    """Persist a single honeypot interaction. Never stores plaintext passwords."""
    return HoneypotEvent.objects.create(
        event_type=event_type,
        path=request.path[:500],
        method=request.method,
        ip_address=client_ip(request),
        user_agent=user_agent(request),
        referer=referer(request),
        attempted_username=(attempted_username or "")[:254],
        attempted_password_hash=hash_password(attempted_password or ""),
        metadata=metadata or {},
    )


def _recently_alerted(event: HoneypotEvent) -> bool:
    """True if we already alerted on this IP within the throttle window."""
    if not event.ip_address:
        return False
    since = timezone.now() - ALERT_WINDOW
    return (
        HoneypotEvent.objects
        .filter(ip_address=event.ip_address, created__gte=since)
        .exclude(pk=event.pk)
        .exists()
    )


def record_and_alert(request, event_type, **kwargs) -> HoneypotEvent:
    """Record an event and, unless throttled, dispatch staff alerts.

    Fail-open: alert dispatch never raises into the request path.
    """
    event = record_event(request, event_type, **kwargs)
    if not _recently_alerted(event):
        try:
            from .tasks import dispatch_alert
            dispatch_alert.delay(event.id)
        except Exception:  # pragma: no cover — broker down must not break lures
            pass
    return event
