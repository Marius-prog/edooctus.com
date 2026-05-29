"""Honeypot event log + decoy account records.

Append-only threat-intelligence storage. Mirrors the IP/UA capture shape used by
`privacy.models.ConsentRecord`. NEVER stores plaintext passwords — only a salted
SHA-256 hash of whatever an attacker submitted, for correlation across attempts.
"""
from django.db import models


class HoneypotEvent(models.Model):
    """A single recorded interaction with any honeypot lure."""

    FAKE_ADMIN_LOGIN = "fake_admin_login"
    DECOY_ENDPOINT = "decoy_endpoint"
    EXPOSED_FILE = "exposed_file"
    DECOY_ACCOUNT_LOGIN = "decoy_account_login"
    TRIPWIRE = "tripwire"
    EVENT_TYPE_CHOICES = [
        (FAKE_ADMIN_LOGIN, "Fake admin login"),
        (DECOY_ENDPOINT, "Decoy endpoint"),
        (EXPOSED_FILE, "Exposed file probe"),
        (DECOY_ACCOUNT_LOGIN, "Decoy account login"),
        (TRIPWIRE, "Tripwire link"),
    ]

    event_type = models.CharField(max_length=24, choices=EVENT_TYPE_CHOICES)
    path = models.CharField(max_length=500)
    method = models.CharField(max_length=8, default="GET")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    referer = models.CharField(max_length=500, blank=True)
    attempted_username = models.CharField(max_length=254, blank=True)
    # SHA-256 hex digest of the submitted password — never the plaintext.
    attempted_password_hash = models.CharField(max_length=64, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]
        indexes = [
            models.Index(fields=["ip_address", "-created"]),
            models.Index(fields=["event_type", "-created"]),
            models.Index(fields=["-created"]),
        ]

    def __str__(self):
        return f"{self.event_type} from {self.ip_address or '?'} @ {self.path}"


class DecoyAccount(models.Model):
    """A fake high-value account surfaced only on decoy pages.

    Deliberately NOT a Django auth.User — it carries no permissions and can never
    authenticate. Any login attempt whose username matches one of these is a
    high-confidence intrusion signal.
    """

    username = models.CharField(max_length=254, unique=True)
    display_role = models.CharField(max_length=64, default="Administrator")
    email = models.EmailField(blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["username"]

    def __str__(self):
        return f"Decoy: {self.username} ({self.display_role})"
