from django.db import models
from decimal import Decimal
from django.utils import timezone

class BankLoan(models.Model):
    """
    สินเชื่อธนาคาร (Pre-Finance, Working Capital, Hire Purchase)
    """
    LOAN_TYPE_CHOICES = [
        ('Pre-Finance', 'Pre-Finance'),
        ('Working Capital', 'Working Capital'),
        ('Hire Purchase', 'Hire Purchase'),
    ]
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Closed', 'Closed'),
    ]

    loan_type = models.CharField(max_length=20, choices=LOAN_TYPE_CHOICES)
    agreement_date = models.DateField(default=timezone.now)
    principal_amount = models.DecimalField(max_digits=16, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)  # ต่อปี
    outstanding_balance = models.DecimalField(max_digits=16, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')

    def __str__(self):
        return f"{self.loan_type} ({self.principal_amount})"

