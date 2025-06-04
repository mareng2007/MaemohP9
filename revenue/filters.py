import django_filters
from django import forms
from django.db.models import Q
from .models import RevenueJob, AccountsReceivable

class RevenueJobFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(
        method='filter_q',
        label='ค้นหา',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ค้นหา...'}),
    )
    status = django_filters.ChoiceFilter(
        choices=RevenueJob._meta.get_field('status').choices,
        label='สถานะ',
        empty_label='ทั้งหมด',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = RevenueJob
        fields = ['q', 'status']

    def filter_q(self, queryset, name, value):
        return queryset.filter(Q(description__icontains=value) | Q(job_code__icontains=value))


class AccountsReceivableFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(
        method='filter_q',
        label='ค้นหา',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ค้นหา...'}),
    )
    status = django_filters.ChoiceFilter(
        choices=AccountsReceivable._meta.get_field('status').choices,
        label='สถานะ',
        empty_label='ทั้งหมด',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = AccountsReceivable
        fields = ['q', 'status']

    def filter_q(self, queryset, name, value):
        return queryset.filter(
            Q(invoice_number__icontains=value) |
            Q(revenue_job__job_code__icontains=value) |
            Q(revenue_job__description__icontains=value)
        )
