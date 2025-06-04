from rest_framework import serializers
from .models import (
    BankAccount,
    PostFinanceFacility,
    PNLoanUsage,
    ITDLoan,
    CashTransaction,
    ProjectCashAccount,
    CashFlowForecast,
    CommitteeMember,
    PaymentRequest,
    PaymentRequestItem,
    Vote,
    LCRequest,
    SwiftMessage,
    TRRequest,
    PNTicket,
    CashPayment
)
from payables.models import AccountsPayable, SiteOperationExpense, SupplierCredit
from revenue.models import RevenueJob, AccountsReceivable
from django.contrib.auth.models import User
from decimal import Decimal

#
# —— BankAccount ——
#
class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = ['id', 'name', 'bank_name', 'account_number', 'balance']


#
# —— PostFinanceFacility + PNLoanUsage ——
#
class PostFinanceFacilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = PostFinanceFacility
        fields = [
            'id',
            'facility_name',
            'start_date',
            'end_date',
            'credit_limit',
            'used_amount',
            'approved_on',
            'created_by'
        ]
        read_only_fields = ['used_amount', 'created_by']

    def create(self, validated_data):
        # บันทึกผู้ใช้งานปัจจุบันเป็น created_by
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class PNLoanUsageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PNLoanUsage
        fields = [
            'id',
            'facility',
            'revenue_job',
            'date',
            'approved_amount',
            'received_amount',
            'bank_interest_fee',
            'repayment_amount',
            'repayment_date',
            'status'
        ]
        read_only_fields = ['status']

    def validate(self, data):
        facility = data['facility']
        approved = data['approved_amount']
        if facility.used_amount + approved > facility.credit_limit:
            raise serializers.ValidationError("วงเงิน PostFinance ไม่เพียงพอ")
        return data

    def create(self, validated_data):
        facility = validated_data['facility']
        # อัปเดตยอด used_amount ก่อนบันทึก
        facility.used_amount += validated_data['approved_amount']
        facility.save(update_fields=['used_amount'])
        return super().create(validated_data)


#
# —— ITDLoan ——
#
class ITDLoanSerializer(serializers.ModelSerializer):
    remaining_balance = serializers.SerializerMethodField()

    class Meta:
        model = ITDLoan
        fields = [
            'id',
            'loan_name',
            'total_amount',
            'received_amount',
            'used_amount',
            'remaining_balance',
            'created_by',
            'created_on'
        ]
        read_only_fields = ['created_by', 'created_on', 'remaining_balance']

    def get_remaining_balance(self, obj):
        return obj.remaining_balance()

    def create(self, validated_data):
        # บันทึกผู้ใช้งานปัจจุบันเป็น created_by
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


#
# —— CashTransaction ——
#
class CashTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashTransaction
        fields = [
            'id',
            'transaction_date',
            'transaction_type',
            'related_id',
            'amount',
            'is_inflow',
            'description',
            'bank_account'
        ]

    def create(self, validated_data):
        """
        1. สร้าง CashTransaction
        2. ถ้ามี bank_account → ปรับยอด balance ใน BankAccount
        3. อัปเดต ProjectCashAccount (opening/closing balance) อัตโนมัติ
        """
        from .models import ProjectCashAccount

        tx = super().create(validated_data)
        bank_acc = validated_data.get('bank_account')
        amount = validated_data['amount']
        is_inflow = validated_data['is_inflow']
        tx_date = validated_data['transaction_date']

        # 2. ปรับยอด balance ใน BankAccount ถ้ามี
        if bank_acc:
            if is_inflow:
                bank_acc.balance += amount
            else:
                bank_acc.balance -= amount
            bank_acc.save(update_fields=['balance'])

        # 3. อัปเดต ProjectCashAccount
        try:
            acct = ProjectCashAccount.objects.get(date=tx_date)
        except ProjectCashAccount.DoesNotExist:
            from datetime import timedelta
            prev_day = tx_date - timedelta(days=1)
            try:
                prev_acct = ProjectCashAccount.objects.get(date=prev_day)
                opening = prev_acct.closing_balance
            except ProjectCashAccount.DoesNotExist:
                opening = Decimal('0.00')
            acct = ProjectCashAccount.objects.create(
                date=tx_date,
                opening_balance=opening,
                closing_balance=opening
            )

        if is_inflow:
            acct.closing_balance += amount
        else:
            acct.closing_balance -= amount
        acct.save(update_fields=['closing_balance'])

        return tx


class ProjectCashAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectCashAccount
        fields = ['id', 'date', 'opening_balance', 'closing_balance', 'remarks']


#
# —— CashFlowForecast ——
#
class CashFlowForecastSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashFlowForecast
        fields = [
            'id',
            'forecast_month',
            'projected_cash_inflow',
            'projected_cash_outflow',
            'net_cash_flow',
            'scenario',
            'assumptions'
        ]


#
# —— CommitteeMember ——
#
class CommitteeMemberSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = CommitteeMember
        fields = ['id', 'user', 'department']


#
# —— PaymentRequest & Items ——
#
class PaymentRequestItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentRequestItem
        fields = [
            'id',
            'payment_request',
            'description',
            'related_ap',
            'related_expense_category',
            'related_lcrequest',
            'related_suppliercredit',
            'amount',
            'payment_type',
            'vote_count',
            'chosen'
        ]
        read_only_fields = ['vote_count', 'chosen']


class PaymentRequestSerializer(serializers.ModelSerializer):
    items = PaymentRequestItemSerializer(many=True)

    class Meta:
        model = PaymentRequest
        fields = [
            'id',
            'title',
            'description',
            'created_by',
            'created_on',
            'scheduled_date',
            'total_amount',
            'status',
            'items'
        ]
        read_only_fields = ['created_by', 'created_on', 'total_amount', 'status']

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        validated_data['created_by'] = self.context['request'].user
        pr = PaymentRequest.objects.create(**validated_data)

        total = Decimal('0.00')
        for item_data in items_data:
            # สร้าง PaymentRequestItem ทีละรายการ
            item = PaymentRequestItem.objects.create(payment_request=pr, **item_data)
            total += item.amount

            # ถ้า payment_type == 'LC' → สร้าง LCRequest ล่วงหน้า (status='Pending_ProfReview')
            if item.payment_type == 'LC':
                from .models import LCRequest
                LCRequest.objects.create(
                    payment_item=item,
                    bank_account=None,
                    lc_amount=item.amount,
                    status='Pending_ProfReview'
                )
            # ถ้า payment_type == 'PN' → สร้าง PNTicket ล่วงหน้า (status='Pending')
            if item.payment_type == 'PN':
                from .models import PNTicket
                PNTicket.objects.create(
                    payment_item=item,
                    status='Pending'
                )
            # ถ้า payment_type == 'ITDLoan' → ตรวจวงเงินแล้วไม่ต้องสร้าง CashTransaction ตรงนี้ (สร้างตอน Execute)
            # ถ้า payment_type == 'SupplierCredit' → ตรวจวงเงินแล้วไม่ต้องสร้าง CashTransaction ตรงนี้ (สร้างตอน Execute)

        pr.total_amount = total
        pr.save(update_fields=['total_amount'])
        return pr

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if items_data is not None:
            # ลบรายการเก่า → สร้างใหม่ทั้งหมด → คำนวณ total ใหม่
            instance.items.all().delete()
            total = Decimal('0.00')
            for item_data in items_data:
                item = PaymentRequestItem.objects.create(payment_request=instance, **item_data)
                total += item.amount

                if item.payment_type == 'LC':
                    from .models import LCRequest
                    LCRequest.objects.create(
                        payment_item=item,
                        bank_account=None,
                        lc_amount=item.amount,
                        status='Pending_ProfReview'
                    )
                if item.payment_type == 'PN':
                    from .models import PNTicket
                    PNTicket.objects.create(
                        payment_item=item,
                        status='Pending'
                    )
                # ITDLoan / SupplierCredit → สร้าง CashTransaction ระหว่าง Execute

            instance.total_amount = total
            instance.save(update_fields=['total_amount'])
        return instance


class VoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vote
        fields = ['id', 'member', 'item', 'voted_on']


#
# —— LCRequest / SwiftMessage / TRRequest ——
#
class LCRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LCRequest
        fields = [
            'id',
            'payment_item',
            'request_date',
            'bank_account',
            'lc_amount',
            'lc_number',
            'expiry_date',
            'status'
        ]
        read_only_fields = ['request_date', 'lc_number', 'status', 'expiry_date']


class SwiftMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SwiftMessage
        fields = ['id', 'lc_request', 'sent_date', 'content']
        read_only_fields = ['sent_date']


class TRRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = TRRequest
        fields = [
            'id',
            'lc_request',
            'tr_number',
            'tr_amount',
            'interest_rate',
            'created_on',
            'status'
        ]
        read_only_fields = ['created_on', 'status']


#
# —— PNTicket & CashPayment ——
#
class PNTicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = PNTicket
        fields = [
            'id',
            'payment_item',
            'request_date',
            'ticket_number',
            'approved_on',
            'status'
        ]
        read_only_fields = ['request_date', 'ticket_number', 'approved_on', 'status']


class CashPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashPayment
        fields = [
            'id',
            'payment_item',
            'request_date',
            'check_number',
            'issued_on',
            'status'
        ]
        read_only_fields = ['request_date', 'check_number', 'issued_on', 'status']
