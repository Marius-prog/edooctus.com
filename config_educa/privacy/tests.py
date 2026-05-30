from django.contrib.auth.models import User
from django.test import TestCase

from .models import (
    ConsentRecord, DataExportRequest, DataDeletionRequest,
    record_consent, has_active_consent,
)


class ConsentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("pv", password="pw12345!")

    def test_record_consent_and_check(self):
        record_consent(self.user, "tos", "2025-01-01", granted=True)
        self.assertTrue(has_active_consent(self.user, "tos"))
        self.assertFalse(has_active_consent(self.user, "marketing"))

    def test_revoke(self):
        rec = record_consent(self.user, "marketing", "v1", granted=True)
        rec.revoke()
        self.assertFalse(has_active_consent(self.user, "marketing"))

    def test_latest_consent_wins(self):
        record_consent(self.user, "privacy", "v1", granted=True)
        record_consent(self.user, "privacy", "v2", granted=False)
        latest = ConsentRecord.latest(self.user, "privacy")
        self.assertEqual(latest.version, "v2")
        self.assertFalse(has_active_consent(self.user, "privacy"))


class DataExportTests(TestCase):
    def test_token_auto_generated(self):
        u = User.objects.create_user("e", password="pw12345!")
        r = DataExportRequest.objects.create(user=u)
        self.assertGreater(len(r.download_token), 20)

    def test_status_default(self):
        u = User.objects.create_user("e2", password="pw12345!")
        r = DataExportRequest.objects.create(user=u)
        self.assertEqual(r.status, DataExportRequest.STATUS_PENDING)


class DataDeletionTests(TestCase):
    def test_verification_token_generated(self):
        u = User.objects.create_user("d", password="pw12345!")
        r = DataDeletionRequest.objects.create(user=u, reason="leaving")
        self.assertGreater(len(r.verification_token), 20)
        self.assertEqual(r.status, DataDeletionRequest.STATUS_PENDING)
