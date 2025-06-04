from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User, Group
from decimal import Decimal

from revenue.models import RevenueJob, AccountsReceivable


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
class RevenueCRUDTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.group = Group.objects.create(name="revenue_access")
        self.user = User.objects.create_user("revuser", password="pass123", is_active=True)
        self.user.groups.add(self.group)
        self.client.login(username="revuser", password="pass123")

    def test_revenuejob_crud(self):
        create_data = {
            "date": "2025-01-01",
            "job_code": "Job1",
            "description": "Test Job",
            "volume": "10.00",
            "income_amount": "1000.00",
            "status": "Pending",
        }
        resp = self.client.post("/revenue/api/jobs/", create_data)
        self.assertEqual(resp.status_code, 201)
        job_id = resp.json()["id"]
        self.assertEqual(RevenueJob.objects.count(), 1)

        resp = self.client.get(f"/revenue/api/jobs/{job_id}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["description"], "Test Job")

        resp = self.client.patch(
            f"/revenue/api/jobs/{job_id}/",
            data={"status": "Invoiced"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(RevenueJob.objects.get(id=job_id).status, "Invoiced")

        resp = self.client.delete(f"/revenue/api/jobs/{job_id}/")
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(RevenueJob.objects.count(), 0)

    def test_accountsreceivable_crud(self):
        job = RevenueJob.objects.create(
            date="2025-01-01",
            job_code="Job2",
            description="AR Job",
            volume=Decimal("5.00"),
            income_amount=Decimal("500.00"),
        )
        ar_data = {
            "revenue_job": job.id,
            "invoice_number": "INV001",
            "invoice_date": "2025-01-05",
            "due_date": "2025-02-05",
            "total_amount": "500.00",
            "paid_amount": "0.00",
            "status": "Unpaid",
        }
        resp = self.client.post("/revenue/api/ar/", ar_data)
        self.assertEqual(resp.status_code, 201)
        ar_id = resp.json()["id"]
        self.assertEqual(AccountsReceivable.objects.count(), 1)
        job.refresh_from_db()
        self.assertEqual(job.status, "Invoiced")

        resp = self.client.patch(
            f"/revenue/api/ar/{ar_id}/",
            data={"paid_amount": "500.00"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        ar = AccountsReceivable.objects.get(id=ar_id)
        self.assertEqual(ar.status, "Paid")

        resp = self.client.delete(f"/revenue/api/ar/{ar_id}/")
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(AccountsReceivable.objects.count(), 0)
