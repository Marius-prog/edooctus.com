"""Request-metadata helpers for the honeypot.

`client_ip` mirrors the X-Forwarded-For handling needed behind nginx; the privacy
app reads REMOTE_ADDR directly, but honeypot traffic arrives proxied so we honour
the forwarded chain (left-most entry = original client).
"""
import hashlib

from django.conf import settings


def client_ip(request) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip() or None
    return request.META.get("REMOTE_ADDR") or None


def user_agent(request) -> str:
    return request.META.get("HTTP_USER_AGENT", "")[:500]


def referer(request) -> str:
    return request.META.get("HTTP_REFERER", "")[:500]


def hash_password(raw: str) -> str:
    """Salted SHA-256 of an attacker-submitted password. Never store plaintext."""
    if not raw:
        return ""
    salt = getattr(settings, "SECRET_KEY", "")
    return hashlib.sha256(f"{salt}{raw}".encode("utf-8")).hexdigest()
