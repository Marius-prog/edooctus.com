from django.test import TestCase
from django.urls import reverse


class ComponentsDebugViewTests(TestCase):
    def test_debug_view_returns_200(self):
        response = self.client.get(reverse("shared:components_debug"))
        self.assertEqual(response.status_code, 200)

    def test_debug_view_uses_components_debug_template(self):
        response = self.client.get(reverse("shared:components_debug"))
        self.assertTemplateUsed(response, "shared/_components_debug.html")
