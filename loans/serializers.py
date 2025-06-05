from rest_framework import serializers
from .models import BankLoan

class BankLoanSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankLoan
        fields = [
            'id',
            'loan_type',
            'agreement_date',
            'principal_amount',
            'interest_rate',
            'outstanding_balance',
            'status'
        ]
        read_only_fields = ['outstanding_balance', 'status']
