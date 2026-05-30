"""Async notification dispatch via Celery."""
from celery import shared_task
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings

from .models import Notification


@shared_task(name="notifications.send_email")
def send_email_notification(notification_id: int) -> bool:
    """Dispatch an email-channel Notification through Django's mail backend."""
    try:
        n = Notification.objects.select_related("user").get(pk=notification_id)
    except Notification.DoesNotExist:
        return False
    if n.channel != "email" or not n.user.email:
        return False
    send_mail(
        subject=n.title,
        message=n.body or n.title,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@educto.io"),
        recipient_list=[n.user.email],
        fail_silently=True,
    )
    return True


@shared_task(name="notifications.broadcast")
def broadcast_notification(user_ids: list[int], kind: str, title: str, body: str = "",
                           link: str = "") -> int:
    """Create in-app notifications for many users at once."""
    created = 0
    for uid in user_ids:
        try:
            u = User.objects.get(pk=uid)
        except User.DoesNotExist:
            continue
        Notification.objects.create(
            user=u, kind=kind, title=title, body=body, link=link, channel="in_app"
        )
        created += 1
    return created
