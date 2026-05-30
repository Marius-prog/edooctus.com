from django.contrib.auth.models import User
from django.test import TestCase

from .models import AITool, PromptTemplate, SandboxRun, UsageQuota
from .services import run_prompt, QuotaExceeded


class AIToolTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("aiu", password="pw12345!")
        cls.tool = AITool.objects.create(
            name="Echo", slug="echo", provider=AITool.PROVIDER_LOCAL, default_model="echo"
        )

    def test_template_render(self):
        t = PromptTemplate.objects.create(
            tool=self.tool, title="Hi", body="Hello {{name}}!",
            variables=[{"name": "name", "label": "Name"}],
        )
        self.assertEqual(t.render({"name": "World"}), "Hello World!")

    def test_sandbox_run_records_tokens_and_quota(self):
        run = run_prompt(self.user, self.tool, "Say hi")
        self.assertEqual(run.status, SandboxRun.STATUS_OK)
        self.assertTrue(run.response.startswith("[fake:"))
        q = UsageQuota.objects.get(user=self.user)
        self.assertEqual(q.runs_this_period, 1)
        self.assertGreater(q.tokens_this_period, 0)

    def test_quota_blocks_run(self):
        UsageQuota.objects.create(
            user=self.user, monthly_run_limit=1, runs_this_period=1,
        )
        with self.assertRaises(QuotaExceeded):
            run_prompt(self.user, self.tool, "Should fail")

    def test_template_use_count_increments(self):
        tpl = PromptTemplate.objects.create(tool=self.tool, title="t", body="x")
        run_prompt(self.user, self.tool, "go", template=tpl)
        tpl.refresh_from_db()
        self.assertEqual(tpl.use_count, 1)
