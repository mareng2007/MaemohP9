import requests
from bs4 import BeautifulSoup

def fetch_exchange_rates():
    url = 'https://www.xe.com/currencytables/?from=THB'
    response = requests.get(url, timeout=10)
    soup = BeautifulSoup(response.text, 'html.parser')
    rates = {}
    table = soup.find('table')
    if table:
        for row in table.find_all('tr')[1:]:
            cols = row.find_all('td')
            if len(cols) >= 3:
                currency = cols[0].text.strip()
                rate = cols[2].text.strip()
                rates[currency] = rate
    return rates

def fetch_interest_rates():
    url = 'https://www.bot.or.th/th/our-services/interest-rate.html'
    response = requests.get(url, timeout=10)
    soup = BeautifulSoup(response.text, 'html.parser')
    rates = {}
    for row in soup.select('table tr')[1:]:
        cols = row.find_all('td')
        if len(cols) >= 2:
            name = cols[0].text.strip()
            rate = cols[1].text.strip()
            rates[name] = rate
    return rates
