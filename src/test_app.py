import copy
import unittest

from fastapi.testclient import TestClient

import app as api


class AdminApiTests(unittest.TestCase):
    def setUp(self):
        self.activities_snapshot = copy.deepcopy(api.activities)
        self.original_config = (
            api.ADMIN_USERNAME,
            api.ADMIN_PASSWORD,
            api.ADMIN_ROLE,
            api.ADMIN_COOKIE_SECURE,
        )
        api.ADMIN_USERNAME = "staff"
        api.ADMIN_PASSWORD = "test-password"
        api.ADMIN_ROLE = "admin"
        api.ADMIN_COOKIE_SECURE = False
        api.admin_sessions.clear()
        api.activity_log.clear()
        api.recent_registrations.clear()
        self.client = TestClient(api.app)

    def tearDown(self):
        api.activities.clear()
        api.activities.update(self.activities_snapshot)
        api.admin_sessions.clear()
        api.activity_log.clear()
        api.recent_registrations.clear()
        (
            api.ADMIN_USERNAME,
            api.ADMIN_PASSWORD,
            api.ADMIN_ROLE,
            api.ADMIN_COOKIE_SECURE,
        ) = self.original_config
        self.client.close()

    def sign_in(self):
        return self.client.post(
            "/admin/login",
            json={"username": "staff", "password": "test-password"},
        )

    def test_public_activity_list_hides_participant_emails(self):
        response = self.client.get("/activities")

        self.assertEqual(response.status_code, 200)
        chess_club = response.json()["Chess Club"]
        self.assertNotIn("participants", chess_club)
        self.assertEqual(chess_club["participant_count"], 2)
        self.assertNotIn("michael@mergington.edu", response.text)

    def test_admin_endpoints_and_unregister_require_login(self):
        self.assertEqual(self.client.get("/admin/dashboard").status_code, 401)
        response = self.client.delete(
            "/activities/Chess%20Club/unregister",
            params={"email": "michael@mergington.edu"},
        )
        self.assertEqual(response.status_code, 401)

        self.assertEqual(self.sign_in().status_code, 200)
        self.assertEqual(self.client.get("/admin/dashboard").status_code, 200)
        response = self.client.delete(
            "/activities/Chess%20Club/unregister",
            params={"email": "michael@mergington.edu"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("michael@mergington.edu", api.activities["Chess Club"]["participants"])

    def test_admin_can_manage_activities_dashboard_and_audit_log(self):
        self.assertEqual(self.sign_in().status_code, 200)
        created = self.client.post(
            "/admin/activities",
            json={
                "name": "Robotics Lab",
                "description": "Build and program robots",
                "schedule": "Mondays after school",
                "max_participants": 12,
            },
        )
        self.assertEqual(created.status_code, 201)

        registered = self.client.post(
            "/activities/Robotics%20Lab/signup",
            params={"email": "student@mergington.edu"},
        )
        self.assertEqual(registered.status_code, 200)
        dashboard = self.client.get("/admin/dashboard").json()
        self.assertEqual(dashboard["activity_count"], len(api.activities))
        self.assertEqual(dashboard["recent_registrations"][0]["email"], "student@mergington.edu")

        updated = self.client.patch(
            "/admin/activities/Robotics%20Lab",
            json={"name": "Robotics Club", "max_participants": 15},
        )
        self.assertEqual(updated.status_code, 200)
        archived = self.client.post("/admin/activities/Robotics%20Club/archive")
        self.assertEqual(archived.status_code, 200)
        self.assertNotIn("Robotics Club", self.client.get("/activities").json())

        log = self.client.get("/admin/activity-log").json()
        self.assertEqual(
            {entry["action"] for entry in log},
            {"login", "activity_created", "activity_updated", "activity_archived"},
        )

    def test_organizer_cannot_archive_or_read_administrator_audit_log(self):
        api.ADMIN_ROLE = "organizer"
        self.assertEqual(self.sign_in().status_code, 200)

        self.assertEqual(
            self.client.post("/admin/activities/Chess%20Club/archive").status_code,
            403,
        )
        self.assertEqual(self.client.get("/admin/activity-log").status_code, 403)

    def test_logout_revokes_session_and_invalid_credentials_are_rejected(self):
        self.assertEqual(
            self.client.post(
                "/admin/login",
                json={"username": "staff", "password": "wrong-password"},
            ).status_code,
            401,
        )
        self.assertEqual(self.sign_in().status_code, 200)
        self.assertEqual(self.client.post("/admin/logout").status_code, 200)
        self.assertEqual(self.client.get("/admin/session").status_code, 401)


if __name__ == "__main__":
    unittest.main()