from django.contrib.auth.models import User
from django.test import TestCase

from .models import Notification, NotificationPreference, notify, unread_count


class NotificationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("nu", password="pw12345!")

    def test_notify_creates_in_app_by_default(self):
        n = notify(self.user, "system", "Welcome!", "Hi there")
        self.assertIsNotNone(n)
        self.assertEqual(n.channel, "in_app")
        self.assertEqual(unread_count(self.user), 1)

    def test_mark_read_updates_state(self):
        n = notify(self.user, "system", "x")
        n.mark_read()
        self.assertTrue(n.is_read)
        self.assertIsNotNone(n.read_at)
        self.assertEqual(unread_count(self.user), 0)

    def test_email_respects_preference(self):
        prefs, _ = NotificationPreference.objects.get_or_create(user=self.user)
        prefs.email_enabled = False
        prefs.save()
        n = notify(self.user, "system", "no", channel="email")
        self.assertIsNone(n)

    def test_kind_specific_preference(self):
        prefs, _ = NotificationPreference.objects.get_or_create(user=self.user)
        prefs.forum_replies = False
        prefs.save()
        self.assertIsNone(notify(self.user, "forum_reply", "ignored"))
        self.assertIsNotNone(notify(self.user, "system", "ok"))

    def test_metadata_persisted(self):
        n = notify(self.user, "badge_earned", "Earned!", metadata={"badge": "first-step"})
        n.refresh_from_db()
        self.assertEqual(n.metadata["badge"], "first-step")
