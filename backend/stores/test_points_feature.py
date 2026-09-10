from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from stores.models import Store, UserPoints, PointHistory
from django.test import TestCase


class PointsFeatureTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("pointuser")
        self.token = Token.objects.create(user=self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_initial_points_are_zero(self):
        response = self.client.get("/api/user/points/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_points"], 0)
        self.assertEqual(len(response.data["recent_history"]), 0)

    def test_create_store_awards_3_points(self):
        response = self.client.post("/api/stores/", {"name": "Points Store", "address": "Tokyo"})
        self.assertEqual(response.status_code, 201)
        store_id = response.data["id"]

        response = self.client.get("/api/user/points/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_points"], 3)
        self.assertEqual(len(response.data["recent_history"]), 1)
        self.assertEqual(response.data["recent_history"][0]["points"], 3)
        self.assertEqual(response.data["recent_history"][0]["store_name"], "Points Store")
        self.assertEqual(response.data["recent_history"][0]["action"], "New store (+3p)")

        self.assertTrue(UserPoints.objects.filter(user=self.user, points=3).exists())
        self.assertTrue(PointHistory.objects.filter(user=self.user, store_id=store_id, points=3).exists())

    def test_update_store_awards_1_point(self):
        response = self.client.post("/api/stores/", {"name": "Update Store", "address": "Tokyo"})
        store_id = response.data["id"]

        response = self.client.patch(f"/api/stores/{store_id}/", {"address": "Osaka"})
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/api/user/points/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_points"], 4)
        self.assertEqual(len(response.data["recent_history"]), 2)
        self.assertEqual(response.data["recent_history"][0]["points"], 1)
        self.assertEqual(response.data["recent_history"][0]["action"], "Edit store (+1p)")

    def test_points_are_per_user(self):
        user2 = User.objects.create_user("pointuser2")
        token2 = Token.objects.create(user=user2)

        self.client.post("/api/stores/", {"name": "User1 Store", "address": "Tokyo"})

        client2 = APIClient()
        client2.credentials(HTTP_AUTHORIZATION=f"Token {token2.key}")
        client2.post("/api/stores/", {"name": "User2 Store", "address": "Osaka"})

        response = self.client.get("/api/user/points/")
        self.assertEqual(response.data["total_points"], 3)

        response = client2.get("/api/user/points/")
        self.assertEqual(response.data["total_points"], 3)
