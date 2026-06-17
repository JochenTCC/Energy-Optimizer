# profile_manager.py
import os
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Tuple
import loxone_client
import pv_forecast
import config

def generate_consumption_profile() -> bool:
    """Lädt aktuelle Logdaten und berechnet die Profil-CSV neu."""
    local_csv = loxone_client.fetch_loxone_csv_file()
    if not local_csv or not os.path.exists(local_csv):
        print("⚠️ Profil-Update abgebrochen: Logdatei konnte nicht geladen werden.")
        return False

    try:
        df = pd.read_csv(local_csv, sep=';', names=['timestamp', 'label', 'value'], header=None)
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df.dropna(subset=['timestamp', 'value'], inplace=True)

        df['Month'] = df['timestamp'].dt.month
        df['Weekday'] = df['timestamp'].dt.weekday
        df['Hour'] = df['timestamp'].dt.hour
        
        profile = df.groupby(['Month', 'Weekday', 'Hour'])['value'].mean().reset_index()
        profile.rename(columns={'value': 'Consumption'}, inplace=True)
        profile['Consumption'] = profile['Consumption'].round(3)
        
        profile.to_csv('consumption_profiles.csv', index=False, sep=';')
        print("✅ 'consumption_profiles.csv' erfolgreich neu berechnet!")
        return True
    except Exception as e:
        print(f"🚨 Fehler bei der Profilberechnung: {e}")
        return False

def check_and_update_profile_if_new_month() -> None:
    """Überprüft, ob ein neuer Monat begonnen hat, und triggert ggf. das Profil-Update."""
    profile_path = 'consumption_profiles.csv'
    should_update = False
    
    if not os.path.exists(profile_path):
        print("ℹ️ Kein Verbrauchsprofil gefunden. Initialisiere erste Berechnung...")
        should_update = True
    else:
        # Prüfen, ob die Datei aus einem älteren Monat stammt
        file_time = os.path.getmtime(profile_path)
        file_date = datetime.fromtimestamp(file_time)
        current_date = datetime.now()
        
        if file_date.month != current_date.month or file_date.year != current_date.year:
            print(f"ℹ️ Neuer Monat erkannt (Letztes Profil von: {file_date.strftime('%d.%m.%Y')}).")
            should_update = True
            
    if should_update:
        generate_consumption_profile()

def _load_consumption_profile(target_hours: List) -> List[float]:
    """Lädt das Verbrauchsprofil für die Zielstunden."""
    profile_path = 'consumption_profiles.csv'
    forecast_consumption = []
    global_hour_defaults = {h: 0.5 for h in range(24)}

    if os.path.exists(profile_path):
        try:
            df_profiles = pd.read_csv(profile_path, sep=';')
            lookup = df_profiles.set_index(['Month', 'Weekday', 'Hour'])['Consumption'].to_dict()
            hour_fallback = df_profiles.groupby('Hour')['Consumption'].mean().to_dict()
            
            for dt in target_hours:
                key = (dt.month, dt.weekday(), dt.hour)
                if key in lookup:
                    forecast_consumption.append(float(lookup[key]))
                elif dt.hour in hour_fallback:
                    forecast_consumption.append(float(hour_fallback[dt.hour]))
                else:
                    forecast_consumption.append(global_hour_defaults.get(dt.hour, 0.5))
                    
        except Exception as e:
            print(f"🚨 Fehler beim Verarbeiten des Verbrauchsprofils: {e}. Nutze statische Defaults.")
            forecast_consumption = [global_hour_defaults[dt.hour] for dt in target_hours]
    else:
        print("ℹ️ Keine 'consumption_profiles.csv' vorhanden. Nutze Standard-Verbrauchswerte.")
        forecast_consumption = [global_hour_defaults[dt.hour] for dt in target_hours]

    return forecast_consumption


def _build_optimization_matrix(market_data: list, forecast_consumption: list, forecast_pv: list) -> list:
    """Erstellt die Optimierungs-Matrix mit Preis-, Verbrauchs- und PV-Daten."""
    optimization_matrix = []
    
    fix_aufschlag = getattr(config, 'FIX_AUFSCHLAG_CENT')
    netzverlust = getattr(config, 'NETZVERLUST_FAKTOR')
    mwst_faktor = getattr(config, 'MWST_AUSTRIA_FAKTOR')

    for i, item in enumerate(market_data[:24]):    
        hour = item['hour']
        
        try:
            epex_price_cent = float(item['price_buy'])
            brutto_price_cent = (epex_price_cent * netzverlust + fix_aufschlag) * mwst_faktor
            brutto_price_cent = round(brutto_price_cent, 4)
        except (TypeError, ValueError) as e:
            print(f"🚨 Fehler bei Brutto-Berechnung für Stunde {hour}: {e}. Nutze Rohwert.")
            brutto_price_cent = item['price_buy']

        optimization_matrix.append({
            "hour": hour,
            "k_act": brutto_price_cent,
            "expected_p_act": forecast_consumption[i],
            "expected_p_pv": forecast_pv[i]
        })
    
    return optimization_matrix[:24]


def get_forecast_vectors(market_data) -> Tuple[List[float], List[float], List[dict]]:
    """
    Lädt das passende historische Verbrauchsprofil und die PV-Prognose 
    für die NÄCHSTEN 24 STUNDEN (rollierender Horizont ab der aktuellen Stunde).
    
    Returns:
        Tuple[List[float], List[float], List[dict]]: (Verbrauchs_Vektor, PV_Vektor, Optimierungs_Matrix) jeweils exakt 24 Elemente.
    """
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    target_hours = [now + timedelta(hours=i) for i in range(24)]
    
    forecast_consumption = _load_consumption_profile(target_hours)
    forecast_pv = pv_forecast.get_hourly_pv_forecast()
    optimization_matrix = _build_optimization_matrix(market_data, forecast_consumption, forecast_pv)

    return forecast_consumption[:24], forecast_pv[:24], optimization_matrix[:24]
