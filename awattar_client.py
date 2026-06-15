import requests
from datetime import datetime
import config

def fetch_awattar_prices():
    """Holt die aktuellen Marktpreise von Awattar."""
    try:
        response = requests.get(config.AWATTAR_URL)
        response.raise_for_status()
        data = response.json()
        
        prices = []
        for entry in data['data']:
            dt = datetime.fromtimestamp(entry['start_timestamp'] / 1000)
            price_cent = entry['marketprice'] / 10
            prices.append({
                "timestamp": dt,
                "hour": dt.hour,
                "price_buy": round(price_cent, 2)
            })
        return prices
    except Exception as e:
        print(f"🚨 Fehler beim Abrufen der Awattar-Preise: {e}")
        return None