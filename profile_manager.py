import os
import pandas as pd
from datetime import datetime
import loxone_client
import pv_forecast

def generate_consumption_profile():
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

def check_and_update_profile_if_new_month():
    """Prüft das Alter des Profils und triggert bei Monatswechsel ein Update."""
    profile_path = 'consumption_profiles.csv'
    now = datetime.now()
    should_update = False
    
    if not os.path.exists(profile_path):
        print("ℹ️ Kein Verbrauchsprofil gefunden. Initialer Download...")
        should_update = True
    else:
        mtime = os.path.getmtime(profile_path)
        file_date = datetime.fromtimestamp(mtime)
        if file_date.month != now.month or file_date.year != now.year:
            print(f"📅 Neuer Monat erkannt (Letztes Profil von: {file_date.strftime('%d.%m.%Y')}).")
            should_update = True
            
    if should_update:
        generate_consumption_profile()

def get_forecast_vectors():
    """Lädt das passende historische Verbrauchsprofil und die PV-Prognose."""
    profile_path = 'consumption_profiles.csv'
    try:
        now = datetime.now()
        current_month = now.month
        current_weekday = now.weekday()
        
        df_profiles = pd.read_csv(profile_path, sep=';')
        filtered = df_profiles[(df_profiles['Month'] == current_month) & (df_profiles['Weekday'] == current_weekday)].sort_values(by='Hour')
        
        if filtered.empty:
            filtered = df_profiles[df_profiles['Month'] == current_month].groupby('Hour')['Consumption'].mean().reset_index()
        if filtered.empty:
            filtered = df_profiles.groupby('Hour')['Consumption'].mean().reset_index()
            
        forecast_consumption = filtered['Consumption'].tolist()
        if len(forecast_consumption) < 24:
            forecast_consumption = forecast_consumption + [0.5] * (24 - len(forecast_consumption))
            
        # Live PV-Prognose aufrufen
        forecast_pv = pv_forecast.get_hourly_pv_forecast()
        return forecast_consumption[:24], forecast_pv[:24]
        
    except Exception as e:
        print(f"⚠️ Fehler beim Laden des Verbrauchsprofils ({e}). Nutze Fallbacks.")
        return [0.5] * 24, [0.0] * 24