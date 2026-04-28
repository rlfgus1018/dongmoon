from django.test import TestCase
from django.urls import reverse


class CoreViewTests(TestCase):
    def test_home_page_loads(self) -> None:
        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "dongmoon")

    def test_health_check(self) -> None:
        response = self.client.get(reverse("core:health"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
