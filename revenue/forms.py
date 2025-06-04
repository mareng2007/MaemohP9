# revenue/forms.py

from django import forms
from .models import RevenueJob, AccountsReceivable

class RevenueJobForm(forms.ModelForm):
    class Meta:
        model = RevenueJob
        fields = [
            'date', 'job_code', 'description',
            'volume', 'income_amount', 'status'
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'job_code': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'เช่น งานเดือน มกราคม 2568'}),
            'volume': forms.NumberInput(attrs={'class': 'form-control'}),
            'income_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

class AccountsReceivableForm(forms.ModelForm):
    class Meta:
        model = AccountsReceivable
        fields = [
            'revenue_job', 'invoice_number',
            'invoice_date', 'due_date',
            'total_amount', 'paid_amount', 'bank_account', 'status'
        ]
        widgets = {
            'revenue_job': forms.Select(attrs={'class': 'form-select'}),
            'invoice_number': forms.TextInput(attrs={'class': 'form-control'}),
            'invoice_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'due_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'total_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'paid_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'bank_account': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
