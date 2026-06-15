import os
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime
import pandas as pd
import config

# ==============================================================================
# 1. LIVE-ABFRAGEN (Loxone & Awattar)
# ==============================================================================

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

def fetch_loxone_soc():
    """Holt den aktuellen Batterie-SoC live aus dem Loxone Miniserver."""
    url = f"http://{config.LOXONE_IP}/jdev/sps/io/{config.LOXONE_SOC_NAME}"
    
    try:
        response = requests.get(
            url, 
            auth=HTTPBasicAuth(config.LOXONE_USER, config.LOXONE_PASS),
            timeout=5
        )
        response.raise_for_status()
        data = response.json()
        
        raw_value = data['LL']['value']
        # Bereinigung des Loxone-Formats (z.B. "99.0 %" -> "99.0")
        clean_value = raw_value.replace('%', '').strip()
        return float(clean_value)
        
    except Exception as e:
        print(f"🚨 Fehler beim Abrufen des Loxone SoC ({config.LOXONE_SOC_NAME}): {e}")
        return None

# ==============================================================================
# 2. AUTOMATISCHES PROFIL-UPDATE (Einmalig pro Monat)
# ==============================================================================

from ftplib import FTP
import os
import config

def fetch_loxone_csv_file(local_path='live_consumption.csv'):
    """Lädt die CSV-Logdatei über das echte FTP-Protokoll vom Miniserver herunter."""
    # Nutzt 'Verbrauch.csv' als Standard, falls nicht anders in der config.py definiert
    remote_filename = getattr(config, 'LOXONE_LOG_FILENAME', 'Verbrauch.csv')
    
    print(f"🌐 FTP-Aktualisierung gestartet: Verbinde mit Miniserver ({config.LOXONE_IP})...")
    try:
        # FTP-Verbindung aufbauen
        ftp = FTP(config.LOXONE_IP, timeout=10)
        ftp.login(user=config.LOXONE_USER, passwd=config.LOXONE_PASS)
        
        # In den log-Ordner auf der SD-Karte wechseln
        ftp.cwd('log')
        
        # Datei binär herunterladen
        print(f"📥 Downloade '{remote_filename}' via FTP...")
        with open(local_path, 'wb') as f:
            ftp.retrbinary(f"RETR {remote_filename}", f.write)
            
        # Verbindung sauber trennen
        ftp.quit()
        print("✅ FTP-Download erfolgreich abgeschlossen.")
        return local_path
        
    except Exception as e:
        print(f"🚨 Fehler beim Loxone-FTP-Download: {e}")
        print("💡 Hinweis: Prüfe, ob die IP, der FTP-Port (21) im Netzwerk offen ist und die FTP-Rechte für den User aktiv sind.")
        return None
    
def generate_consumption_profile():
    """Lädt aktuelle Logdaten (neues Format) und berechnet die Profil-CSV neu."""
    local_csv = fetch_loxone_csv_file()
    if not local_csv or not os.path.exists(local_csv):
        print("⚠️ Profil-Update abgebrochen: Logdatei konnte nicht geladen werden.")
        return False

    try:
        # ANPASSUNG AN NEUE SYNTAX:
        # Keine Header-Zeile (header=None), Punkt als Dezimaltrenner, Namen manuell vergeben
        df = pd.read_csv(
            local_csv, 
            sep=';', 
            names=['timestamp', 'label', 'value'], 
            header=None
        )
        
        # Zeitstempel konvertieren (Format YYYY-MM-DD HH:MM:SS wird automatisch erkannt)
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        
        # Zeilen löschen, die kein gültiges Datum oder keinen Wert haben (z.B. Leerzeilen)
        df.dropna(subset=['timestamp', 'value'], inplace=True)

        # Zeit-Features extrahieren
        df['Month'] = df['timestamp'].dt.month
        df['Weekday'] = df['timestamp'].dt.weekday
        df['Hour'] = df['timestamp'].dt.hour
        
        # Aggregation auf Stunden-Mittelwerte basierend auf der Spalte 'value'
        profile = df.groupby(['Month', 'Weekday', 'Hour'])['value'].mean().reset_index()
        profile.rename(columns={'value': 'Consumption'}, inplace=True)
        profile['Consumption'] = profile['Consumption'].round(3)
        
        # Profil lokal speichern
        profile.to_csv('consumption_profiles.csv', index=False, sep=';')
        print("✅ 'consumption_profiles.csv' erfolgreich für diesen Monat neu berechnet!")
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
        # Änderungsdatum der lokalen Profil-CSV prüfen
        mtime = os.path.getmtime(profile_path)
        file_date = datetime.fromtimestamp(mtime)
        
        # Wenn Datei aus einem anderen Monat/Jahr stammt -> Update
        if file_date.month != now.month or file_date.year != now.year:
            print(f"📅 Neuer Monat erkannt (Letztes Profil von: {file_date.strftime('%d.%m.%Y')}).")
            should_update = True
            
    if should_update:
        generate_consumption_profile()

# ==============================================================================
# 3. PROFIL-AUSLESUNG & OPTIMIERUNG
# ==============================================================================

def get_forecast_vectors():
    """Lädt das passende historische Verbrauchsprofil für das heutige Datum."""
    profile_path = 'consumption_profiles.csv'
    try:
        now = datetime.now()
        current_month = now.month
        current_weekday = now.weekday()
        
        df_profiles = pd.read_csv(profile_path, sep=';')
        
        # 1. Versuch: Exakter Monat + exakter Wochentag
        filtered = df_profiles[(df_profiles['Month'] == current_month) & (df_profiles['Weekday'] == current_weekday)].sort_values(by='Hour')
        
        # Fallback 1: Falls Wochentag im Monat fehlt -> Durchschnitt des aktuellen Monats
        if filtered.empty:
            filtered = df_profiles[df_profiles['Month'] == current_month].groupby('Hour')['Consumption'].mean().reset_index()
            
        # Fallback 2: Am Monatsanfang -> Nimm den Gesamtschnitt aller verfügbaren Daten
        if filtered.empty:
            filtered = df_profiles.groupby('Hour')['Consumption'].mean().reset_index()
            
        forecast_consumption = filtered['Consumption'].tolist()
        
        # Fallback auf Standardwerte, falls die Liste unvollständig ist
        if len(forecast_consumption) < 24:
            forecast_consumption = forecast_consumption + [0.5] * (24 - len(forecast_consumption))
            
        # PV-Erzeugung (Vorläufiger Mock-Wert)
        mock_pv = [0.0, 0.0, 0.0, 0.0, 0.0, 0.1, 0.5, 1.2, 2.5, 4.0, 5.2, 5.8, 
                   5.5, 4.8, 3.5, 2.1, 1.0, 0.3, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
                   
        return forecast_consumption[:24], mock_pv
        
    except Exception as e:
        print(f"⚠️ Fehler beim Laden des Verbrauchsprofils ({e}). Nutze statische Fallback-Werte.")
        return [0.5] * 24, [0.0] * 24

def heuristic_optimizer(matrix, current_hour, current_soc):
    """Berechnet den Modus und die Ladeleistung basierend auf Preisschwellenwerten."""
    all_prices = sorted([row['k_act'] for row in matrix])
    if not all_prices:
        return 0, 0.0
        
    k_avg = sum(all_prices) / len(all_prices)
    cutoff_low = all_prices[4]   # Günstigste ~20%
    cutoff_high = all_prices[-5] # Teuerste ~20%
    
    current_row = next((row for row in matrix if row['hour'] == current_hour), None)
    if not current_row:
        return 0, 0.0
        
    current_price = current_row['k_act']
    mode = 0
    target_power = 0.0
    
    print(f"\n--- Optimierungs-Entscheidung für {current_hour}:00 Uhr ---")
    print(f"Aktueller Preis: {current_price} Cent/kWh | Tag-Schnitt: {k_avg:.2f} Cent/kWh")
    print(f"Aktueller Live-SoC: {current_soc}%")
    
    if current_price <= cutoff_low and current_soc < 90:
        mode = 1
        target_power = 2.5
        print("-> Entscheidung: ZWANGSLADEN")
    elif current_price < k_avg and current_soc < 60:
        future_rows = [row for row in matrix if current_hour < row['hour'] <= current_hour + 6]
        incoming_spike = any(row['k_act'] >= cutoff_high for row in future_rows)
        if incoming_spike:
            mode = 2
            target_power = 0.0
            print("-> Entscheidung: ENTLADESPERRE")
    else:
        print("-> Entscheidung: AUTOMATIK")
        
    return mode, target_power

# ==============================================================================
# 4. MAIN ORCHESTRIERUNG
# ==============================================================================

def main():
    print("--- Energy Optimizer Live-Abfrage ---")
    
    # 1. Prüfen, ob ein neues Verbrauchsprofil vom Miniserver geholt werden muss
    check_and_update_profile_if_new_month()
    
    # 2. Aktuellen SoC aus Loxone holen
    current_soc = fetch_loxone_soc()
    if current_soc is None:
        print("Optimierung abgebrochen: Kein Zugriff auf Loxone SoC.")
        return

    # 3. Awattar Preise holen
    market_data = fetch_awattar_prices()
    if not market_data:
        print("Optimierung abgebrochen: Keine Awattar-Preise empfangen.")
        return
        
    # 4. Prognose-Vektoren laden (jetzt dynamisch aus dem berechneten Profil)
    forecast_consumption, forecast_pv = get_forecast_vectors()
    
    # Matrix aufbauen
    optimization_matrix = []
    for item in market_data[:24]:
        hour = item['hour']
        optimization_matrix.append({
            "hour": hour,
            "k_act": item['price_buy'],
            "expected_p_act": forecast_consumption[hour],
            "expected_p_pv": forecast_pv[hour]
        })

    # 5. Aktuelle Stunde ermitteln
    current_hour = datetime.now().hour
    
    # 6. Optimierung ausführen
    mode, target_power = heuristic_optimizer(optimization_matrix, current_hour, current_soc)
    
    print("\n--- Berechnete Werte für Loxone ---")
    print(f"MODE: {mode}")
    print(f"TARGET_POWER: {target_power} kW")

if __name__ == "__main__":
    main()