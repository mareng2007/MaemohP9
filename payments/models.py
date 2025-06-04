from django.conf import settings
from django.db import models
from django.utils import timezone

class Payment(models.Model):
    PROVIDER_STRIPE = 'Stripe'
    PROVIDER_PAYPAL = 'PayPal'
    PROVIDER_CHOICES = [
        (PROVIDER_STRIPE, 'Stripe'),
        (PROVIDER_PAYPAL, 'PayPal'),
    ]
    STATUS_PENDING = 'Pending'
    STATUS_COMPLETED = 'Completed'
    STATUS_FAILED = 'Failed'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_FAILED, 'Failed'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payments')
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='THB')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.provider} {self.amount} {self.currency}"
