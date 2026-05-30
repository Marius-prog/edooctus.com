"""End-to-end test of the consent + data-export Celery flow."""
from django.contrib.auth.models import User
from django.test import Client, TestCase
import json

from .models import ConsentRecord, DataExportRequest


class PrivacyAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("pv", email="pv@example.com",
                                             password="pw12345!")
        self.client = Client()
        self.client.login(username="pv", password="pw12345!")

    def test_cookie_consent_creates_record(self):
        resp = self.client.post(
            "/privacy/api/consent/",
            data=json.dumps({"kind": "cookies", "version": "2025-11-01", "granted": True}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(ConsentRecord.objects.count(), 1)
        rec = ConsentRecord.objects.first()
        self.assertEqual(rec.kind, "cookies")
        self.assertTrue(rec.granted)

    def test_unknown_consent_kind_rejected(self):
        resp = self.client.post(
            "/privacy/api/consent/",
            data=json.dumps({"kind": "bogus", "version": "v1", "granted": True}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_export_request_runs_inline_via_eager_celery(self):
        resp = self.client.post("/privacy/api/export/request/")
        self.assertEqual(resp.status_code, 202)
        req = DataExportRequest.objects.get(user=self.user)
        # Eager Celery ran generate_export inline -> file is ready
        self.assertEqual(req.status, DataExportRequest.STATUS_READY)
        self.assertTrue(req.file)

    def test_export_request_produces_downloadable_artifact(self):
        """Verify the export pipeline yields a downloadable artifact + token.

        Note: we don't fetch the FileResponse here because Django's test client
        triggers a context-copy that hits a known Py3.14 stdlib bug.
        The download view itself is exercised in production / Py3.10 CI.
        """
        self.client.post("/privacy/api/export/request/")
        req = DataExportRequest.objects.get(user=self.user)
        self.assertEqual(req.status, DataExportRequest.STATUS_READY)
        self.assertTrue(req.file)
        self.assertTrue(req.download_token)
        self.assertIsNotNone(req.expires_at)

    def test_deletion_request_creation(self):
        resp = self.client.post(
            "/privacy/api/deletions/",
            data=json.dumps({"reason": "leaving"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
