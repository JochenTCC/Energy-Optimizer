from ftplib import FTP
import requests
from requests.auth import HTTPBasicAuth
import config

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
        raw_value = response.json()['LL']['value']
        return float(raw_value.replace('%', '').strip())
    except Exception as e:
        print(f"🚨 Fehler beim Abrufen des Loxone SoC ({config.LOXONE_SOC_NAME}): {e}")
        return None

def send_loxone_value(input_name, value):
    """Sendet einen berechneten Wert an einen Virtuellen Eingang in Loxone."""
    url = f"http://{config.LOXONE_IP}/dev/sps/io/{input_name}/{value}"
    try:
        response = requests.get(
            url,
            auth=HTTPBasicAuth(config.LOXONE_USER, config.LOXONE_PASS),
            timeout=5
        )
        response.raise_for_status()
        print(f"   ↳ {input_name} erfolgreich auf {value} gesetzt.")
        return True
    except Exception as e:
        print(f"🚨 Fehler beim Senden an Loxone ({input_name}): {e}")
        return False

def fetch_loxone_csv_file(local_path='live_consumption.csv'):
    """Lädt die CSV-Logdatei über das echte FTP-Protokoll vom Miniserver herunter."""
    remote_filename = getattr(config, 'LOXONE_LOG_FILENAME', 'Verbrauch.csv')
    print(f"🌐 FTP-Aktualisierung gestartet: Verbinde mit Miniserver ({config.LOXONE_IP})...")
    try:
        ftp = FTP(config.LOXONE_IP, timeout=10)
        ftp.login(user=config.LOXONE_USER, passwd=config.LOXONE_PASS)
        ftp.cwd('log')
        
        print(f"📥 Downloade '{remote_filename}' via FTP...")
        with open(local_path, 'wb') as f:
            ftp.retrbinary(f"RETR {remote_filename}", f.write)
            
        ftp.quit()
        print("✅ FTP-Download erfolgreich abgeschlossen.")
        return local_path
    except Exception as e:
        print(f"🚨 Fehler beim Loxone-FTP-Download: {e}")
        return None