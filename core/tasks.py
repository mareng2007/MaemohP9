from celery import shared_task
from .scrapers import fetch_exchange_rates, fetch_interest_rates
from .models import ExchangeRate, InterestRate

@shared_task
def scrape_exchange_rates():
    data = fetch_exchange_rates()
    for currency, rate in data.items():
        ExchangeRate.objects.create(currency=currency, rate=rate)

@shared_task
def scrape_interest_rates():
    data = fetch_interest_rates()
    for name, rate in data.items():
        InterestRate.objects.create(name=name, rate=rate)
