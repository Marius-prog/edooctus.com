from django.contrib.auth.models import User
from django.core import mail
from django.template import Context, Template
from django.test import TestCase, override_settings

from .models import DecoyAccount, HoneypotEvent
from .utils import hash_password


class FakeAdminLoginTests(TestCase):
    def test_get_renders_decoy_login_no_event(self):
        resp = self.client.get("/admin/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Django administration")
        self.assertEqual(HoneypotEvent.objects.count(), 0)

    def test_post_logs_event_and_never_authenticates(self):
        resp = self.client.post("/admin/", {"username": "attacker", "password": "hunter2"})
        self.assertEqual(resp.status_code, 200)  # always "fails", re-renders
        self.assertFalse(resp.wsgi_request.user.is_authenticated)
        ev = HoneypotEvent.objects.get()
        self.assertEqual(ev.event_type, HoneypotEvent.FAKE_ADMIN_LOGIN)
        self.assertEqual(ev.attempted_username, "attacker")
        # password stored only as a hash, never plaintext
        self.assertNotIn("hunter2", ev.attempted_password_hash)
        self.assertEqual(ev.attempted_password_hash, hash_password("hunter2"))

    def test_post_with_decoy_username_flags_decoy_account_login(self):
        DecoyAccount.objects.create(username="root", display_role="System")
        self.client.post("/admin/", {"username": "root", "password": "x"})
        ev = HoneypotEvent.objects.get()
        self.assertEqual(ev.event_type, HoneypotEvent.DECOY_ACCOUNT_LOGIN)


class DecoyEndpointTests(TestCase):
    def test_env_file_lure(self):
        resp = self.client.get("/.env")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "SECRET_KEY")
        self.assertEqual(HoneypotEvent.objects.get().event_type, HoneypotEvent.EXPOSED_FILE)

    def test_api_users_lure_returns_decoys_only(self):
        DecoyAccount.objects.create(username="admin", display_role="Superuser")
        resp = self.client.get("/api/v1/users")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["count"], 1)
        self.assertEqual(HoneypotEvent.objects.get().event_type, HoneypotEvent.DECOY_ENDPOINT)

    def test_tripwire_logs_and_404s(self):
        resp = self.client.get("/honeypot/tripwire/abc123/")
        self.assertEqual(resp.status_code, 404)
        ev = HoneypotEvent.objects.get()
        self.assertEqual(ev.event_type, HoneypotEvent.TRIPWIRE)
        self.assertEqual(ev.metadata.get("token"), "abc123")


class ProbeMiddlewareTests(TestCase):
    def test_probe_path_logged_and_blocked(self):
        resp = self.client.get("/.git/config")
        self.assertEqual(resp.status_code, 404)
        ev = HoneypotEvent.objects.get()
        self.assertEqual(ev.event_type, HoneypotEvent.EXPOSED_FILE)
        self.assertTrue(ev.metadata.get("probe"))

    def test_legitimate_path_is_untouched(self):
        """CRITICAL no-regression: a normal request creates no event, 200 as before."""
        resp = self.client.get("/accounts/login/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(HoneypotEvent.objects.count(), 0)


@override_settings(SECURITY_ALERT_EMAILS=["sec@educto.io"], CELERY_TASK_ALWAYS_EAGER=True)
class AlertingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.super1 = User.objects.create_superuser("hsuper", "s@x.io", "pw12345!")
        cls.normal = User.objects.create_user("hnormal", password="pw12345!")

    def test_alert_sends_email_and_inapp_to_superusers(self):
        self.client.post("/admin/", {"username": "attacker", "password": "x"})
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Honeypot", mail.outbox[0].subject)
        self.assertEqual(mail.outbox[0].to, ["sec@educto.io"])
        self.assertEqual(
            self.super1.notifications.filter(kind="security_alert").count(), 1
        )
        self.assertEqual(self.normal.notifications.count(), 0)

    def test_repeat_from_same_ip_is_throttled(self):
        self.client.post("/admin/", {"username": "a", "password": "x"})
        self.client.post("/admin/", {"username": "b", "password": "y"})
        self.assertEqual(HoneypotEvent.objects.count(), 2)  # both logged
        self.assertEqual(len(mail.outbox), 1)  # only first alerted


class DashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user("hstaff", password="pw12345!", is_staff=True)
        cls.normal = User.objects.create_user("huser", password="pw12345!")

    def test_anonymous_redirected(self):
        self.assertEqual(self.client.get("/honeypot/dashboard/").status_code, 302)

    def test_non_staff_redirected(self):
        self.client.force_login(self.normal)
        self.assertEqual(self.client.get("/honeypot/dashboard/").status_code, 302)

    def test_staff_sees_dashboard(self):
        self.client.force_login(self.staff)
        resp = self.client.get("/honeypot/dashboard/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "THREAT INTEL")


class TripwireTagTests(TestCase):
    def test_tag_renders_hidden_nofollow_link(self):
        out = Template("{% load honeypot_tags %}{% honeypot_tripwire %}").render(Context())
        self.assertIn('rel="nofollow"', out)
        self.assertIn("/honeypot/tripwire/", out)
        self.assertIn("left:-9999px", out)
        self.assertIn('aria-hidden="true"', out)
