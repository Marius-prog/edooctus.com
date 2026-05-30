"""Seed minimal fixtures for Playwright E2E suite.

Usage:
    python manage.py seed_e2e

Idempotent \u2014 safe to run multiple times.
"""
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seed fixtures (test user, AI tool, sample course) for E2E tests."

    def handle(self, *args, **opts):
        # 1. Test user
        u, created = User.objects.get_or_create(
            username="e2e_user", defaults={"email": "e2e@example.com"},
        )
        if created:
            u.set_password("e2e_pass!")
            u.save()
            self.stdout.write(self.style.SUCCESS("Created e2e_user"))
        else:
            self.stdout.write("e2e_user already exists")

        # 2. AI tool
        try:
            from ai_tools.models import AITool
            AITool.objects.get_or_create(
                slug="echo",
                defaults=dict(name="Echo", provider="local",
                              default_model="echo", is_active=True),
            )
            self.stdout.write(self.style.SUCCESS("Seeded ai_tools.AITool[slug=echo]"))
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f"AI tools seed skipped: {exc}"))

        # 3. Sample course (so home page has content)
        try:
            from courses.models import Course, Subject
            subj, _ = Subject.objects.get_or_create(
                slug="e2e", defaults={"title": "E2E Sample Subject"},
            )
            Course.objects.get_or_create(
                slug="e2e-course",
                defaults=dict(owner=u, subject=subj, title="E2E Sample Course",
                              overview="A sample course used by Playwright tests."),
            )
            self.stdout.write(self.style.SUCCESS("Seeded sample course"))
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f"Course seed skipped: {exc}"))

        self.stdout.write(self.style.SUCCESS("E2E seed complete."))
