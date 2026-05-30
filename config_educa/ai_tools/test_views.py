"""HTMX sandbox + DRF API smoke tests for ai_tools."""
import sys
import unittest

from django.contrib.auth.models import User
from django.test import Client, TestCase

from .models import AITool, SandboxRun, UsageQuota

skip_if_py314_templates = unittest.skipIf(
    sys.version_info >= (3, 14),
    "Django 4.2 template-context copy broken on Python 3.14",
)


class AIToolsViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("aiv", password="pw12345!")
        cls.tool = AITool.objects.create(
            name="Echo", slug="echo", provider="local", default_model="echo",
        )

    def setUp(self):
        self.client = Client()
        self.client.login(username="aiv", password="pw12345!")

    @skip_if_py314_templates
    def test_htmx_sandbox_run_renders_partial(self):
        resp = self.client.post(
            "/ai/sandbox/run/",
            {"tool": self.tool.id, "prompt": "hello world"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"fake:echo", resp.content)  # avoid Py3.14 context-copy bug
        self.assertEqual(SandboxRun.objects.count(), 1)

    @skip_if_py314_templates
    def test_htmx_sandbox_run_rejects_empty(self):
        resp = self.client.post(
            "/ai/sandbox/run/",
            {"tool": self.tool.id, "prompt": ""},
        )
        self.assertEqual(resp.status_code, 400)

    @skip_if_py314_templates
    def test_htmx_sandbox_run_returns_429_on_quota(self):
        UsageQuota.objects.create(
            user=self.user, monthly_run_limit=1, runs_this_period=1,
        )
        resp = self.client.post(
            "/ai/sandbox/run/",
            {"tool": self.tool.id, "prompt": "blocked"},
        )
        self.assertEqual(resp.status_code, 429)

    def test_drf_run_endpoint(self):
        resp = self.client.post(
            "/ai/api/runs/run/",
            data={"tool": self.tool.id, "prompt": "hi"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["status"], "ok")

    def test_quota_endpoint(self):
        self.client.post(
            "/ai/api/runs/run/",
            data={"tool": self.tool.id, "prompt": "x"},
            content_type="application/json",
        )
        resp = self.client.get("/ai/api/runs/quota/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["runs_this_period"], 1)
