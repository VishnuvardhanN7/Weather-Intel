"""Optional integration tests that exercise the live FastAPI app + database.

These intentionally hit real PostgreSQL (DATABASE_URL from backend/.env) and
only run when explicitly enabled, so the CI/deploy environment controls them:

    $env:RUN_API_INTEGRATION = "1"
    pytest tests/test_api_integration.py -q

Covers the requirement checklist: public browsing, admin-only enforcement,
DB-backed media with authenticated access, notification preferences.
"""

import io
import os
import unittest

RUN_INTEGRATION = os.environ.get("RUN_API_INTEGRATION") == "1"


def _make_valid_png() -> bytes:
    from PIL import Image
    import io as _io

    buf = _io.BytesIO()
    Image.new("RGB", (1, 1), (0, 0, 0)).save(buf, format="PNG")
    return buf.getvalue()


# 1x1 PNG generated at import time so upload tests pass Pillow integrity checks.
VALID_PNG = _make_valid_png()


@unittest.skipUnless(RUN_INTEGRATION, "RUN_API_INTEGRATION=1 is required")
class ApiIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from app.main import app

        cls.client = TestClient(app)
        cls.prefix = f"it_{os.getpid()}"

    def _register_and_login(self):
        username = f"{self.prefix}_citizen"
        password = "TestPass123!x"
        r = self.client.post("/api/auth/register", json={
            "username": username,
            "email": f"{username}@example.com",
            "password": password,
            "full_name": "Integration Citizen",
        })
        # Already registered from a prior run is fine.
        self.assertIn(r.status_code, (201, 400), r.text)
        r = self.client.post("/api/auth/login", data={
            "username": username,
            "password": password,
        })
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def test_01_public_events_endpoint_requires_no_auth(self):
        r = self.client.get("/api/weather?per_page=5")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIn("data", r.json())
        self.assertIn("pagination", r.json())

    def test_02_citizen_report_with_db_media_and_authenticated_access(self):
        auth = self._register_and_login()
        headers = {"Authorization": f"Bearer {auth['access_token']}"}

        files = {"files": ("evidence.png", io.BytesIO(VALID_PNG), "image/png")}
        data = {
            "title": "Integration test report - waterlogging",
            "description": "Heavy rain caused waterlogging at the integration test location.",
            "city": "Delhi",
        }
        r = self.client.post("/api/weather/citizen-report", data=data, files=files, headers=headers)
        self.assertEqual(r.status_code, 201, r.text)
        event = r.json()
        self.assertTrue(event.get("media"), "event should expose media metadata")

        first_media = event["media"][0]
        self.assertIsNotNone(first_media.get("id"))

        # Media content must NOT be served anonymously.
        anon = self.client.get(first_media["url"])
        self.assertEqual(anon.status_code, 401)

        # Authenticated access works.
        authed = self.client.get(first_media["url"], headers=headers)
        self.assertEqual(authed.status_code, 200)
        self.assertEqual(authed.content, VALID_PNG)

    def test_03_citizen_cannot_delete_events(self):
        auth = self._register_and_login()
        headers = {"Authorization": f"Bearer {auth['access_token']}"}
        r = self.client.delete("/api/weather/999999", headers=headers)
        # Admin-only: citizen must be blocked before resolving the event.
        self.assertEqual(r.status_code, 403, r.text)

    def test_04_notification_preferences_roundtrip(self):
        auth = self._register_and_login()
        headers = {"Authorization": f"Bearer {auth['access_token']}"}
        r = self.client.put("/api/notifications/preferences", json={
            "notification_consent": True,
            "notification_lat": 28.6139,
            "notification_lng": 77.2090,
            "notification_radius_km": 50,
        }, headers=headers)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(r.json()["notification_consent"])

        r = self.client.get("/api/notifications/unread-count", headers=headers)
        self.assertEqual(r.status_code, 200)
        self.assertIn("unread_count", r.json())


if __name__ == "__main__":
    unittest.main()