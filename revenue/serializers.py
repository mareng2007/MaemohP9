# revenue/serializers.py

from rest_framework import serializers
from .models import RevenueJob, AccountsReceivable
from decimal import Decimal

class RevenueJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = RevenueJob
        fields = [
            'id', 'date', 'job_code', 'description',
            'volume', 'income_amount', 'status'
        ]

class AccountsReceivableSerializer(serializers.ModelSerializer):
    revenue_job = serializers.PrimaryKeyRelatedField(queryset=RevenueJob.objects.all())

    class Meta:
        model = AccountsReceivable
        fields = [
            'id', 'revenue_job', 'invoice_number', 'invoice_date',
            'due_date', 'total_amount', 'paid_amount', 'bank_account', 'status'
        ]

    def create(self, validated_data):
        # เมื่อสร้าง AR ให้เปลี่ยน RevenueJob.status เป็น 'Invoiced'
        ar = super().create(validated_data)
        revenue_job = validated_data.get('revenue_job')
        revenue_job.status = 'Invoiced'
        revenue_job.save(update_fields=['status'])
        return ar

    def update(self, instance, validated_data):
        ar = super().update(instance, validated_data)
        # ถ้า paid_amount >= total_amount ให้เปลี่ยน status เป็น 'Paid'
        if ar.paid_amount >= ar.total_amount:
            ar.status = 'Paid'
            ar.save(update_fields=['status'])
        elif ar.paid_amount > Decimal('0.00'):
            ar.status = 'Partial'
            ar.save(update_fields=['status'])
        return ar
