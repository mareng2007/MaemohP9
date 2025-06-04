from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core import mail

from core.models import EmailActivation, OTP, UserProfile


@override_settings(
    SECRET_KEY="testsecret",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DATABASES={
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    },
)
class CoreFlowTests(TestCase):
    def setUp(self):
        self.client = Client()

    def _register_user(self):
        url = reverse("core:register")
        data = {
            "username": "tester",
            "email": "tester@example.com",
            "password1": "StrongPass123",
            "password2": "StrongPass123",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        user = User.objects.get(username="tester")
        self.assertFalse(user.is_active)
        self.assertTrue(UserProfile.objects.filter(user=user).exists())
        self.assertTrue(EmailActivation.objects.filter(user=user).exists())
        self.assertEqual(len(mail.outbox), 1)
        return user, EmailActivation.objects.get(user=user)

    def test_registration_and_activation(self):
        user, activation = self._register_user()

        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        url = reverse("core:activate", kwargs={"uidb64": uidb64, "token": activation.token})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

        user.refresh_from_db()
        activation.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertTrue(activation.is_used)

    def test_login_with_otp_flow(self):
        user, activation = self._register_user()

        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        self.client.get(reverse("core:activate", kwargs={"uidb64": uidb64, "token": activation.token}))

        login_url = reverse("core:login")
        response = self.client.post(login_url, {"username": "tester", "password": "StrongPass123"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("core:login_verify_otp"))

        otp = OTP.objects.latest("created_at")
        self.assertFalse(otp.is_used)
        self.assertIn("pre_2fa_user_id", self.client.session)

        verify_url = reverse("core:login_verify_otp")
        response = self.client.post(verify_url, {"email": user.email, "code": otp.code})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("core:home"))

        otp.refresh_from_db()
        self.assertTrue(otp.is_used)
        response = self.client.get(reverse("core:home"))
        self.assertTrue(response.wsgi_request.user.is_authenticated)
