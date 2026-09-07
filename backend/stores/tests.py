import importlib
import os
import sys
from unittest import mock

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.throttling import ScopedRateThrottle

from .access import issue_token
from .models import PaymentMethod, Store, StorePaymentMethod


class UnlockedApiTestCase(APITestCase):
    """Every API call needs the app password, so hand the tests a token."""

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {issue_token()}")


class StoreApiTests(UnlockedApiTestCase):
    def test_create_store_initializes_all_payment_methods(self):
        # Full-width characters check that normalized_name is NFKC folded.
        response = self.client.post(reverse("store-list"), {"name": "Ｔｅｓｔ Ｓｔｏｒｅ", "address": "Tokyo"})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        store = Store.objects.get()
        self.assertEqual(store.normalized_name, "test store")
        self.assertEqual(store.payment_methods.count(), PaymentMethod.objects.filter(is_active=True).count())
        self.assertTrue(store.payment_methods.filter(status=StorePaymentMethod.Status.UNKNOWN).exists())

    def test_create_and_update_payment_status(self):
        method = PaymentMethod.objects.get(code="qr")
        create_response = self.client.post(
            reverse("store-list"),
            {
                "name": "Payment Store",
                "payment_statuses": [{"payment_method_id": method.id, "status": "accepted"}],
            },
        )
        store_id = create_response.data["id"]
        relation = StorePaymentMethod.objects.get(store_id=store_id, payment_method=method)
        self.assertEqual(relation.status, StorePaymentMethod.Status.ACCEPTED)
        self.assertIsNotNone(relation.confirmed_at)

        update_response = self.client.patch(
            reverse("store-detail", args=[store_id]),
            {"payment_statuses": [{"payment_method_id": method.id, "status": "not_accepted"}]},
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        relation.refresh_from_db()
        self.assertEqual(relation.status, StorePaymentMethod.Status.NOT_ACCEPTED)

    def test_search_stores_by_name_and_address(self):
        Store.objects.create(name="Station Supermarket", address="Shibuya")
        Store.objects.create(name="Seaside Cafe", address="Kamakura")

        name_response = self.client.get(reverse("store-list"), {"search": "Supermarket"})
        address_response = self.client.get(reverse("store-list"), {"search": "Kamakura"})

        self.assertEqual(len(name_response.data), 1)
        self.assertEqual(name_response.data[0]["name"], "Station Supermarket")
        self.assertEqual(len(address_response.data), 1)
        self.assertEqual(address_response.data[0]["name"], "Seaside Cafe")

    def test_create_store_with_coordinates(self):
        response = self.client.post(
            reverse("store-list"),
            {
                "name": "Riverside Cafe",
                "address": "Da Nang",
                "latitude": "16.081259",
                "longitude": "108.222577",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["latitude"], "16.081259")
        self.assertEqual(response.data["longitude"], "108.222577")

    def test_rejects_only_one_coordinate(self):
        response = self.client.post(
            reverse("store-list"),
            {"name": "Riverside Cafe", "latitude": "16.081259"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejects_duplicate_payment_method_inputs(self):
        method = PaymentMethod.objects.first()
        response = self.client.post(
            reverse("store-list"),
            {
                "name": "Duplicate Store",
                "payment_statuses": [
                    {"payment_method_id": method.id, "status": "accepted"},
                    {"payment_method_id": method.id, "status": "unknown"},
                ],
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_store_removes_it_and_its_payment_statuses(self):
        store = Store.objects.create(name="Store to delete")
        relation = StorePaymentMethod.objects.create(
            store=store,
            payment_method=PaymentMethod.objects.first(),
            status=StorePaymentMethod.Status.ACCEPTED,
        )

        response = self.client.delete(reverse("store-detail", args=[store.id]))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Store.objects.filter(id=store.id).exists())
        self.assertFalse(StorePaymentMethod.objects.filter(id=relation.id).exists())


class StoreDuplicateTests(UnlockedApiTestCase):
    def test_rejects_same_name_and_address(self):
        Store.objects.create(name="Corner Shop", address="1 Main Street")

        response = self.client.post(
            reverse("store-list"), {"name": "Corner Shop", "address": "1 Main Street"}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Store.objects.filter(name="Corner Shop").count(), 1)

    def test_rejects_same_name_and_address_in_different_case(self):
        Store.objects.create(name="Corner Shop", address="1 Main Street")

        response = self.client.post(
            reverse("store-list"), {"name": "CORNER shop", "address": " 1 Main Street "}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_allows_same_name_at_a_different_address(self):
        Store.objects.create(name="Corner Shop", address="1 Main Street")

        response = self.client.post(
            reverse("store-list"), {"name": "Corner Shop", "address": "2 Market Road"}
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Store.objects.filter(name="Corner Shop").count(), 2)

    def test_allows_same_name_and_blank_address_at_different_coordinates(self):
        Store.objects.create(name="Corner Shop", latitude="16.081259", longitude="108.222577")

        response = self.client.post(
            reverse("store-list"),
            {
                "name": "Corner Shop",
                "latitude": "16.081300",
                "longitude": "108.222600",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Store.objects.filter(name="Corner Shop").count(), 2)

    def test_allows_updating_a_store_without_moving_it(self):
        store = Store.objects.create(name="Corner Shop", address="1 Main Street")

        response = self.client.patch(
            reverse("store-detail", args=[store.id]), {"address": "1 Main Street"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class StoreAdminTests(TestCase):
    def setUp(self):
        User.objects.create_superuser("admin", "admin@example.com", "pass1234")
        self.client.force_login(User.objects.get(username="admin"))

    def test_admin_change_form_adds_rows_for_missing_methods(self):
        methods = list(PaymentMethod.objects.filter(is_active=True))
        store = Store.objects.create(name="Partly Filled Store")
        StorePaymentMethod.objects.create(store=store, payment_method=methods[0], status="accepted")

        response = self.client.get(reverse("admin:stores_store_change", args=[store.id]))

        formset = response.context["inline_admin_formsets"][0].formset
        self.assertEqual(formset.total_form_count(), len(methods))
        self.assertEqual(len(formset.extra_forms), len(methods) - 1)

    def test_admin_rejects_a_duplicate_store(self):
        Store.objects.create(name="Corner Shop", address="1 Main Street")
        methods = list(PaymentMethod.objects.filter(is_active=True))
        prefix = "payment_methods"
        payload = {
            "name": "Corner Shop",
            "address": "1 Main Street",
            f"{prefix}-TOTAL_FORMS": len(methods),
            f"{prefix}-INITIAL_FORMS": 0,
            f"{prefix}-MIN_NUM_FORMS": 0,
            f"{prefix}-MAX_NUM_FORMS": 1000,
        }
        for index, method in enumerate(methods):
            payload[f"{prefix}-{index}-payment_method"] = method.id
            payload[f"{prefix}-{index}-status"] = "unknown"

        response = self.client.post(reverse("admin:stores_store_add"), payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "already exists")
        self.assertEqual(Store.objects.filter(name="Corner Shop").count(), 1)

    def test_admin_store_form_saves_every_payment_method(self):
        methods = list(PaymentMethod.objects.filter(is_active=True))

        add_response = self.client.get(reverse("admin:stores_store_add"))
        self.assertEqual(add_response.context["inline_admin_formsets"][0].formset.total_form_count(), len(methods))

        prefix = "payment_methods"
        payload = {
            "name": "Admin Store",
            "address": "",
            f"{prefix}-TOTAL_FORMS": len(methods),
            f"{prefix}-INITIAL_FORMS": 0,
            f"{prefix}-MIN_NUM_FORMS": 0,
            f"{prefix}-MAX_NUM_FORMS": 1000,
        }
        for index, method in enumerate(methods):
            payload[f"{prefix}-{index}-payment_method"] = method.id
            payload[f"{prefix}-{index}-status"] = "accepted" if index % 2 == 0 else "unknown"

        response = self.client.post(reverse("admin:stores_store_add"), payload)

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        store = Store.objects.get(name="Admin Store")
        self.assertEqual(store.payment_methods.count(), len(methods))
        self.assertEqual(store.payment_methods.filter(status="accepted").count(), len(methods[::2]))



class AppAccessTests(APITestCase):
    def setUp(self):
        # The access endpoint is throttled, and the throttle counter lives in
        # the cache, which outlives a single test.
        cache.clear()

    def test_requests_without_a_token_are_refused(self):
        response = self.client.get(reverse("store-list"))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_wrong_password_is_refused(self):
        response = self.client.post(reverse("app-access"), {"password": "not-the-password"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn("token", response.data)

    def test_password_returns_a_working_token(self):
        response = self.client.post(reverse("app-access"), {"password": settings.APP_PASSWORD})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['token']}")
        self.assertEqual(self.client.get(reverse("store-list")).status_code, status.HTTP_200_OK)

    def test_a_made_up_token_is_refused(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer made.up.token")

        self.assertEqual(self.client.get(reverse("store-list")).status_code, status.HTTP_403_FORBIDDEN)


class AppAccessThrottleTests(APITestCase):
    """A single shared password is one guessing target, so attempts are capped.

    These run against whatever rate the project is actually configured with,
    rather than an overridden one: DRF binds THROTTLE_RATES onto the throttle
    class at import, so override_settings would not reach it anyway.
    """

    def setUp(self):
        cache.clear()
        throttle = ScopedRateThrottle()
        throttle.scope = "app-access"
        self.allowed, _ = throttle.parse_rate(throttle.get_rate())

    def post_wrong_password(self, **extra):
        return self.client.post(reverse("app-access"), {"password": "wrong"}, **extra)

    def test_guessing_stops_once_the_limit_is_reached(self):
        codes = [self.post_wrong_password().status_code for _ in range(self.allowed + 2)]

        self.assertEqual(set(codes[:self.allowed]), {status.HTTP_400_BAD_REQUEST})
        self.assertEqual(set(codes[self.allowed:]), {status.HTTP_429_TOO_MANY_REQUESTS})

    def test_the_correct_password_is_refused_once_throttled(self):
        """Guessing must not stay open just because the guess finally lands."""
        for _ in range(self.allowed):
            self.post_wrong_password()

        response = self.client.post(reverse("app-access"), {"password": settings.APP_PASSWORD})

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_a_forged_forwarded_for_header_does_not_reset_the_count(self):
        """DRF must key off the proxy's entry, not one the client can invent."""
        codes = [
            self.post_wrong_password(HTTP_X_FORWARDED_FOR=f"10.0.0.{i}, 203.0.113.9").status_code
            for i in range(self.allowed + 2)
        ]

        self.assertEqual(set(codes[self.allowed:]), {status.HTTP_429_TOO_MANY_REQUESTS})

    def test_the_rest_of_the_api_is_not_throttled(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {issue_token()}")

        codes = {self.client.get(reverse("store-list")).status_code for _ in range(30)}

        self.assertEqual(codes, {status.HTTP_200_OK})


class RequiredSettingsTests(TestCase):
    """Secrets must come from the environment; there is no usable fallback."""

    def reload_settings(self, **environ):
        """Re-import the settings module the way a fresh server process sees it.

        django.conf.settings already holds its own copy, so reloading the module
        exercises the module-level logic without disturbing the running tests.
        argv is swapped too: under `manage.py test` RUNNING_TESTS would otherwise
        be true and hand back the development stand-ins.
        """
        with mock.patch.dict(os.environ, environ, clear=True), \
                mock.patch.object(sys, "argv", ["gunicorn", "config.wsgi:application"]):
            return importlib.reload(importlib.import_module("config.settings"))

    def test_secrets_are_required_when_debug_is_off(self):
        for missing in ["DJANGO_SECRET_KEY", "APP_PASSWORD"]:
            supplied = {"DJANGO_SECRET_KEY": "x" * 50, "APP_PASSWORD": "a-real-password"}
            del supplied[missing]
            with self.subTest(missing=missing):
                with self.assertRaises(ImproperlyConfigured) as caught:
                    self.reload_settings(DJANGO_DEBUG="false", **supplied)
                self.assertIn(missing, str(caught.exception))

    def test_debug_is_off_unless_asked_for(self):
        module = self.reload_settings(DJANGO_SECRET_KEY="x" * 50, APP_PASSWORD="a-real-password")

        self.assertFalse(module.DEBUG)

    def test_development_still_runs_without_any_environment(self):
        module = self.reload_settings(DJANGO_DEBUG="true")

        self.assertTrue(module.DEBUG)
        self.assertNotEqual(module.APP_PASSWORD, "")

    def tearDown(self):
        # Leave the real settings module in place for whatever runs next.
        importlib.reload(importlib.import_module("config.settings"))
