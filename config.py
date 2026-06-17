# config.py
import os
import json
from dotenv import load_dotenv

# Sensible Daten aus .env laden
load_dotenv()

CONFIG_JSON_PATH = "config.json"

# 1. Prüfen, ob die JSON-Datei existiert
if not os.path.exists(CONFIG_JSON_PATH):
    raise FileNotFoundError(f"Kritischer Fehler: Die Konfigurationsdatei '{CONFIG_JSON_PATH}' wurde nicht gefunden!")

# 2. JSON-Datei einlesen
try:
    with open(CONFIG_JSON_PATH, "r", encoding="utf-8") as f:
        _raw_config = json.load(f)
except json.JSONDecodeError as e:
    raise ValueError(f"Kritischer Fehler: '{CONFIG_JSON_PATH}' enthält ungültiges JSON: {e}")

# Hilfsfunktion für strikten Zugriff (Fail-Fast)
def _get_strict(d, keys_path):
    """Durchläuft ein geschachteltes Dictionary. Wirft KeyError, wenn ein Pfad fehlt."""
    current = d
    for k in keys_path:
        if not isinstance(current, dict) or k not in current:
            raise KeyError(f"Kritischer Konfigurationsfehler: Der Parameter '{'.'.join(keys_path)}' fehlt in {CONFIG_JSON_PATH}!")
        current = current[k]
    return current

# =========================================================================
# SENSIBLE INFRASTRUKTUR-DATEN (.env)
# =========================================================================
LOXONE_IP = os.getenv("LOXONE_IP")
LOXONE_USER = os.getenv("LOXONE_USER")
LOXONE_PASS = os.getenv("LOXONE_PASS")

if not all([LOXONE_IP, LOXONE_USER, LOXONE_PASS]):
    missing = [k for k in ["LOXONE_IP", "LOXONE_USER", "LOXONE_PASS"] if not os.getenv(k)]
    raise ValueError(f"Kritischer Fehler: Fehlende sensible Daten in der .env: {', '.join(missing)}")

# =========================================================================
# STATISCHE PARAMETER (Aus config.json gemappt)
# =========================================================================
AWATTAR_URL = _get_strict(_raw_config, ["awattar", "url"])
FIX_AUFSCHLAG_CENT = _get_strict(_raw_config, ["awattar", "fix_aufschlag_cent"])
NETZVERLUST_FAKTOR = _get_strict(_raw_config, ["awattar", "netzverlust_faktor"])
MWST_AUSTRIA_FAKTOR = _get_strict(_raw_config, ["awattar", "mwst_austria_faktor"])

GLOBAL_TIMEOUT = _get_strict(_raw_config, ["system", "global_timeout"])
LOOP_TIMEOUT = _get_strict(_raw_config, ["system", "loop_timeout"])

LOXONE_SOC_NAME = _get_strict(_raw_config, ["loxone_blocks", "soc_name"])
LOXONE_PV_COUNTER_NAME = _get_strict(_raw_config, ["loxone_blocks", "pv_counter_name"])
LOXONE_LOG_FILENAME = _get_strict(_raw_config, ["loxone_blocks", "log_filename"])
PV_TUNING_LOG_FILE = _get_strict(_raw_config, ["loxone_blocks", "pv_tuning_log_file"])

# =========================================================================
# DYNAMISCHE PARAMETER (Aus config.json / runtime_settings)
# =========================================================================
K_PUSH_CENT = _get_strict(_raw_config, ["runtime_settings", "k_push_cent"])
PV_TILT = _get_strict(_raw_config, ["runtime_settings", "pv_tilt"])
PV_AZIMUTH = _get_strict(_raw_config, ["runtime_settings", "pv_azimuth"])
PV_KWP = _get_strict(_raw_config, ["runtime_settings", "pv_kwp"])

BATTERY_MAX_POWER_KW = _get_strict(_raw_config, ["runtime_settings", "battery_max_power_kw"])
BATTERY_EFFICIENCY = _get_strict(_raw_config, ["runtime_settings", "battery_efficiency"])
BATTERY_CAPACITY_KWH = _get_strict(_raw_config, ["runtime_settings", "battery_capacity_kwh"])
BATTERY_MIN_SOC = _get_strict(_raw_config, ["runtime_settings", "battery_min_soc"])
BATTERY_MAX_SOC = _get_strict(_raw_config, ["runtime_settings", "battery_max_soc"])

LATITUDE = _get_strict(_raw_config, ["runtime_settings", "latitude"])
LONGITUDE = _get_strict(_raw_config, ["runtime_settings", "longitude"])


# =========================================================================
# SCHREIB-SCHNITTSTELLE FÜR APP.PY
# =========================================================================
def update_runtime_settings(new_settings: dict):
    """
    Überschreibt dynamische Parameter in der JSON-Datei und aktualisiert 
    sie direkt im geladenen Modul-Namespace, damit der Hauptloop sofort 
    mit den neuen Werten arbeitet (Behebt den Groß-/Kleinschreibungs-Konflikt).
    """
    # Datei frisch lesen, um Race-Conditions zu minimieren
    with open(CONFIG_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    for key, value in new_settings.items():
        # BEHOBEN: Case-insensitive Suche nach dem passenden Key in den JSON runtime_settings
        target_key = None
        for json_key in data["runtime_settings"].keys():
            if json_key.lower() == key.lower():
                target_key = json_key
                break
                
        if target_key is None:
            raise KeyError(f"Sicherheitsfehler: '{key}' ist kein konfigurierbarer Laufzeit-Parameter!")
        
        # In den JSON-Datensatz mit dem exakten Key-Format aus der Datei schreiben
        data["runtime_settings"][target_key] = value
        
        # Direkt im globalen Namespace dieses Moduls aktualisieren (Großbuchstaben für Python)
        global_key = key.upper()
        globals()[global_key] = value

    # Validierte Daten sauber in die config.json zurückschreiben
    with open(CONFIG_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)