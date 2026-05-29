from django.test import TestCase
from django.urls import reverse


class SecuritySettingsTests(TestCase):
    """S5: base settings must default to a safe (non-debug) posture."""

    def test_base_defaults_debug_off(self):
        from config_educa.settings import base
        self.assertFalse(base.DEBUG, "base.py must default DEBUG=False; local.py opts in.")

    def test_production_entrypoints_default_to_prod(self):
        from pathlib import Path
        base_dir = Path(__file__).resolve().parent.parent / "config_educa"
        for name in ("wsgi.py", "asgi.py"):
            src = (base_dir / name).read_text()
            self.assertIn("config_educa.settings.prod", src,
                          f"{name} should default DJANGO_SETTINGS_MODULE to prod")


class ComponentsDebugViewTests(TestCase):
    def test_debug_view_returns_200(self):
        response = self.client.get(reverse("shared:components_debug"))
        self.assertEqual(response.status_code, 200)

    def test_debug_view_uses_components_debug_template(self):
        response = self.client.get(reverse("shared:components_debug"))
        self.assertTemplateUsed(response, "shared/_components_debug.html")

    def test_debug_page_shows_metric_tile_section(self):
        response = self.client.get(reverse("shared:components_debug"))
        self.assertContains(response, "METRIC TILE")
        self.assertContains(response, 'class="text-display"')

    def test_debug_page_shows_breadcrumb_section(self):
        response = self.client.get(reverse("shared:components_debug"))
        self.assertContains(response, "BREADCRUMB")
        self.assertContains(response, "▸")


from django.contrib.auth.models import User
from django.test import override_settings
from django.urls import reverse


@override_settings(USE_FOUNDRY_UI=True)
class FoundryAccessibilityTests(TestCase):
    """M6: Foundry shell exposes the right ARIA / a11y plumbing."""

    def setUp(self):
        self.url = reverse("shared:components_debug")

    def test_skip_link_present(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'href="#main"')

    def test_main_landmark_present(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'id="main"')

    def test_topbar_has_aria_label_on_command_palette(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'aria-label="Open command palette"')

    def test_sidebar_has_navigation_landmark(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'aria-label="Primary navigation"')

    def test_aria_live_region_present(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'aria-live="polite"')

    def test_html_lang_set(self):
        response = self.client.get(self.url)
        self.assertContains(response, '<html lang="en"')


@override_settings(USE_FOUNDRY_UI=True)
class FoundryResponsiveTests(TestCase):
    """M6: Layouts use Tailwind responsive breakpoints (collapse on mobile)."""

    def setUp(self):
        self.debug_url = reverse("shared:components_debug")

    def test_sidebar_has_mobile_drawer_classes(self):
        # Sidebar should hide on mobile (<md) and show as overlay/drawer
        response = self.client.get(self.debug_url)
        # Either it's hidden by default on small screens, or has a drawer trigger
        self.assertTrue(
            "max-md:hidden" in response.content.decode() or
            "md:flex" in response.content.decode() or
            'id="sidebar-drawer-toggle"' in response.content.decode(),
            "Sidebar should declare a mobile breakpoint or drawer toggle",
        )


from unittest import mock


@override_settings(
    USE_FOUNDRY_UI=True,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class FoundryPlayerResponsiveTests(TestCase):
    """M6: 3-pane player stacks on mobile."""

    @classmethod
    def setUpTestData(cls):
        from courses.models import Course, Subject, Module
        cls.student = User.objects.create_user(username="respstu", password="pw12345!")
        cls.owner = User.objects.create_user(username="respinstr", password="pw12345!")
        cls.subject = Subject.objects.create(title="Resp", slug="m6-resp")
        cls.course = Course.objects.create(
            owner=cls.owner, subject=cls.subject,
            title="Resp Course", slug="m6-resp", overview="resp",
        )
        cls.course.students.add(cls.student)
        Module.objects.create(course=cls.course, title="A module", description="x")

    @mock.patch("students.views.r")
    def test_player_uses_responsive_grid(self, mock_redis):
        mock_redis.get.return_value = None
        self.client.login(username="respstu", password="pw12345!")
        url = reverse("student_course_detail", args=[self.course.id])
        response = self.client.get(url)
        body = response.content.decode()
        # Should declare a responsive grid: stacked on mobile, three-pane on md+
        self.assertIn("grid-cols-1", body)
        self.assertIn("md:grid-cols-[240px_1fr_280px]", body)
