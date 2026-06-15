import requests
from datetime import datetime
import config

def get_hourly_pv_forecast():
    """
    Holt die stündliche PV-Prognose für den heutigen Tag über die Forecast.Solar API.
    Gibt eine Liste mit 24 Werten (kW) für die Stunden 0-23 zurück.
    """
    # Parameter aus der config laden
    lat = getattr(config, 'LATITUDE', 47.41)
    lon = getattr(config, 'LONGITUDE', 9.74)
    tilt = getattr(config, 'PV_TILT', 18)
    azimuth = getattr(config, 'PV_AZIMUTH', 28)
    kwp = getattr(config, 'PV_KWP', 6.0)

    # API-URL für die stündliche Abschätzung (Kostenlose Nutzung ohne Key)
    url = f"https://api.forecast.solar/estimate/{lat}/{lon}/{tilt}/{azimuth}/{kwp}"
    
    # 24-Stunden-Vektor mit 0.0 kW vorinitialisieren
    pv_vector = [0.0] * 24
    today_str = datetime.now().strftime("%Y-%m-%d")

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Das Feld 'watts' enthält die stündlichen Leistungswerte
        hourly_watts = data.get('result', {}).get('watts', {})
        
        for timestamp_str, watts in hourly_watts.items():
            # Prüfen, ob der Datenpunkt von heute ist (Format: "2026-06-15 08:00:00")
            if timestamp_str.startswith(today_str):
                dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                hour = dt.hour
                
                # Umrechnung von Watt in Kilowatt (kW) und runden
                pv_vector[hour] = round(watts / 1000.0, 3)
                
        print(f"✅ PV-Ertragsprognose live abgerufen (Tages-Maximum: {max(pv_vector)} kW).")
        return pv_vector

    except Exception as e:
        print(f"⚠️ Fehler beim PV-Forecast-Abruf ({e}). Nutze statischen Standard-Sonnenverlauf.")
        # Robuster Fallback-Vektor, falls die API limitiert oder offline ist
        return [0.0, 0.0, 0.0, 0.0, 0.0, 0.1, 0.5, 1.2, 2.5, 4.0, 5.2, 5.8, 
                5.5, 4.8, 3.5, 2.1, 1.0, 0.3, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

if __name__ == "__main__":
    # Kleiner Selbsttest, wenn man die Datei direkt ausführt
    print("Testlauf PV-Prognose-Vektor:")
    print(get_hourly_pv_forecast())