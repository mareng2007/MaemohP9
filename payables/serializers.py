from rest_framework import serializers
from .models import Vendor, AccountsPayable, SiteOperationExpense, SupplierCredit
from decimal import Decimal

class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = ['id', 'name', 'category', 'payment_terms', 'tax_withholding_percent']


class AccountsPayableSerializer(serializers.ModelSerializer):
    vendor = serializers.PrimaryKeyRelatedField(queryset=Vendor.objects.all())

    class Meta:
        model = AccountsPayable
        fields = [
            'id',
            'vendor',
            'invoice_number',
            'invoice_date',
            'due_date',
            'amount',
            'year',
            'paid_amount',
            'status',
        ]

    def create(self, validated_data):
        ap = super().create(validated_data)
        return ap

    def update(self, instance, validated_data):
        ap = super().update(instance, validated_data)
        # อัปเดตสถานะตาม paid_amount
        if ap.paid_amount >= ap.amount:
            ap.status = 'Paid'
        elif ap.paid_amount > Decimal('0.00'):
            ap.status = 'Partial'
        else:
            ap.status = 'Unpaid'
        ap.save(update_fields=['paid_amount', 'status'])
        return ap


class SiteOperationExpenseSerializer(serializers.ModelSerializer):
    vendor = serializers.PrimaryKeyRelatedField(
        queryset=Vendor.objects.all(),
        required=False,
        allow_null=True
    )
    ap_reference = serializers.PrimaryKeyRelatedField(
        queryset=AccountsPayable.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = SiteOperationExpense
        fields = [
            'id',
            'date',
            'expense_category',
            'vendor',
            'pr_po_reference',
            'ap_reference',
            'amount',
            'tax_withheld',
            'net_amount',
            'status',
        ]

    def create(self, validated_data):
        expense = super().create(validated_data)
        ap_ref = validated_data.get('ap_reference')
        if ap_ref:
            # ถ้ามี AP Reference → เพิ่ม paid_amount ใน AP และอัปเดตสถานะ AP
            total_site_amount = expense.net_amount
            ap_ref.paid_amount += total_site_amount
            if ap_ref.paid_amount >= ap_ref.amount:
                ap_ref.status = 'Paid'
            else:
                ap_ref.status = 'Partial'
            ap_ref.save(update_fields=['paid_amount', 'status'])
            expense.status = 'AP_Invoiced'
            expense.save(update_fields=['status'])
        return expense

    def update(self, instance, validated_data):
        expense = super().update(instance, validated_data)
        ap_ref = validated_data.get('ap_reference', instance.ap_reference)
        if ap_ref:
            total_site_amount = instance.net_amount
            ap_ref.paid_amount += total_site_amount
            if ap_ref.paid_amount >= ap_ref.amount:
                ap_ref.status = 'Paid'
            else:
                ap_ref.status = 'Partial'
            ap_ref.save(update_fields=['paid_amount', 'status'])
            expense.status = 'AP_Invoiced'
            expense.save(update_fields=['status'])
        return expense


class SupplierCreditSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplierCredit
        fields = ['id', 'supplier_name', 'credit_limit', 'used_amount', 'created_on', 'updated_on']
        read_only_fields = ['used_amount', 'created_on', 'updated_on']

