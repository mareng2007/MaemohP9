import stripe
import paypalrestsdk
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import Payment

stripe.api_key = getattr(settings, 'STRIPE_API_KEY', '')
paypalrestsdk.configure({
    "mode": "sandbox",
    "client_id": getattr(settings, 'PAYPAL_CLIENT_ID', ''),
    "client_secret": getattr(settings, 'PAYPAL_CLIENT_SECRET', '')
})

@login_required
@require_POST
def create_stripe_payment(request):
    amount = request.POST.get('amount')
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'thb',
                'product_data': {
                    'name': 'Subscription'
                },
                'unit_amount': int(float(amount) * 100),
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url=request.build_absolute_uri('/payments/success/'),
        cancel_url=request.build_absolute_uri('/payments/cancel/'),
    )
    Payment.objects.create(user=request.user, provider=Payment.PROVIDER_STRIPE, amount=amount)
    return JsonResponse({'session_id': session.id})

@login_required
@require_POST
def create_paypal_payment(request):
    amount = request.POST.get('amount')
    payment = paypalrestsdk.Payment({
        "intent": "sale",
        "payer": {
            "payment_method": "paypal"},
        "transactions": [{
            "amount": {
                "total": amount,
                "currency": "THB"},
            "description": "Subscription"}],
        "redirect_urls": {
            "return_url": request.build_absolute_uri('/payments/success/'),
            "cancel_url": request.build_absolute_uri('/payments/cancel/')}
    })
    if payment.create():
        Payment.objects.create(user=request.user, provider=Payment.PROVIDER_PAYPAL, amount=amount)
        approval_url = next(link.href for link in payment.links if link.rel == "approval_url")
        return JsonResponse({'approval_url': approval_url})
    else:
        return JsonResponse({'error': 'payment_failed'}, status=400)
