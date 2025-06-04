from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('stripe/', views.create_stripe_payment, name='create_stripe_payment'),
    path('paypal/', views.create_paypal_payment, name='create_paypal_payment'),
]
