# app.py
import json
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import importlib
import os
import time

# Bestehende Projektmodule importieren
import config
import loxone_client
import awattar_client
import profile_manager
import optimizer
import pv_tuner  # Adaptives PV-Tuning-Modul einbinden

st.set_page_config(
    page_title="Ernie Energy Control Center",
    page_icon="🔋",
    layout="wide"
)

def update_config_file(kwp, tilt, azimuth, k_push):
    """Schreibt Parameter direkt in die JSON-Datei (Docker Bind-Mount kompatibel)."""
    settings_path = "runtime_settings.json"
    
    data = {
        "PV_KWP": float(kwp),
        "PV_TILT": int(tilt),
        "PV_AZIMUTH": int(azimuth),
        "K_PUSH": float(k_push)
    }
    
    try:
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        st.success("✅ Parameter erfolgreich in 'runtime_settings.json' gespeichert!")
        importlib.reload(config)
    except Exception as e:
        st.error(f"🚨 Fehler beim Speichern der Konfiguration: {e}")

def render_parameter_input():
    """
    Kapselt die Eingabe der System-Parameter in der Sidebar.
    Liest Live-Fallbacks aus der Konfigurationsdatei.
    """
    st.sidebar.header("⚙️ System-Parameter")
    
    # Aktuelle Werte aus config laden (nutzt dynamische Properties)
    current_kwp = getattr(config, 'PV_KWP', 9.4)
    current_tilt = getattr(config, 'PV_TILT', 18)
    current_azimuth = getattr(config, 'PV_AZIMUTH', 28)
    current_k_push = getattr(config, 'K_PUSH', 3.7)
    
    with st.sidebar.form("config_form"):
        kwp = st.number_input("PV Leistung (kWp)", min_value=0.0, value=float(current_kwp), step=0.1)
        tilt = st.number_input("Dachneigung (°)", min_value=0, max_value=90, value=int(current_tilt))
        azimuth = st.number_input("Ausrichtung (Azimut °)", min_value=-180, max_value=180, value=int(current_azimuth), help="0=Süd, -90=Ost, 90=West")
        k_push = st.number_input("Einspeisevergütung (Cent/kWh)", min_value=0.0, value=float(current_k_push), step=0.1)
        
        submit_btn = st.form_submit_button("Speichern & Aktualisieren")
        if submit_btn:
            update_config_file(kwp, tilt, azimuth, k_push)
            st.rerun()

def render_optimization_chart(df):
    """
    Kapselt das Zeichnen der Plotly-Grafik auf einer einzelnen, synchronisierten X-Achse.
    Der Strompreis wird als rote Treppenfunktion dargestellt.
    """
    # 1. Dynamische Farbliste basierend auf dem Steuerbefehl generieren
    bar_colors = []
    for cmd in df["Steuerbefehl"]:
        if "Zwangsladen" in cmd:
            bar_colors.append("forestgreen")  # Grün bei erzwungenem Laden
        elif "Entladesperre" in cmd or "Entladen" in cmd:
            bar_colors.append("crimson")      # Rot bei Entladesperre / Eingriff
        else:
            bar_colors.append("dodgerblue")   # Blau bei normalem Eigenverbrauch (Automatik)

    # 2. Plotly Grafik erstellen
    fig = go.Figure()

    # --- BALKEN: Geplante Batterie-Aktion ---
    fig.add_trace(go.Bar(
        x=df["Uhrzeit"], 
        y=df["Geplante Batterie-Aktion (kW)"],
        name="Batterie-Aktion (kW)",
        marker=dict(color=bar_colors),
        opacity=0.75,
        offset=0.05,         # Startet knapp rechts vom Stunden-Tick
        width=0.9,           # Füllt 90% des Stunden-Slots aus
        offsetgroup="bars",
        yaxis="y"
    ))

    # --- LINIE: Strompreis als rote Treppe (Stufenfunktion) ---
    fig.add_trace(go.Scatter(
        x=df["Uhrzeit"],
        y=df["Strompreis (Cent/kWh)"],
        name="Strompreis (Cent/kWh)",
        mode="lines",
        line=dict(color="red", width=3, shape="hv"),
        yaxis="y2"
    ))

    # --- LINIE: Simulierter SoC (bleibt linear/gestrichelt) ---
    fig.add_trace(go.Scatter(
        x=df["Uhrzeit"],
        y=df["Simulierter SoC (%)"],
        name="Simulierter SoC (%)",
        mode="lines",
        line=dict(color="gold", width=2.5, dash="dash"),
        yaxis="y2"
    ))

    # Layout Definition
    fig.update_layout(
        title="Optimierungs-Vorschau & Simulation (Nächste 24h)",
        xaxis=dict(
            title="Uhrzeit (Stundenslots / Intervalle)",
            type="category"
        ),
        barmode="overlay",
        yaxis=dict(title="Leistung (kW)", side="left"),
        yaxis2=dict(title="Preis (Cent/kWh) / SoC (%)", side="right", overlaying="y", showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=80, b=40)
    )
    
    # Behebung der Warnung: use_container_width=True durch width='stretch' ersetzt
    st.plotly_chart(fig, width='stretch')

def main():
    st.title("🔋 Ernie Energy Control Center")
    st.markdown("Willkommen im Dashboard zur intelligenten Kostenoptimierung deines Batteriespeichers.")

    # 1. Parameter-Eingabemaske rendern
    render_parameter_input()

    # Live SoC abrufen
    current_soc = loxone_client.fetch_loxone_soc()
    if current_soc is None:
        current_soc = 50.0
        st.sidebar.warning("⚠️ Live SoC konnte nicht geladen werden. Nutze Default-Wert (50%).")
    else:
        st.sidebar.metric(label="🔋 Aktueller Batterie SoC", value=f"{current_soc}%")

    # 2. Marktdaten beschaffen
    st.subheader("📈 Last- & Preisverlauf")
    market_data = awattar_client.fetch_awattar_prices()
    
    if not market_data:
        st.error("🚨 Fehler beim Abrufen der aWATTar-Marktdaten. Diagramm kann nicht gerendert werden.")
        return

    # 3. Simulations-Matrix für das Interface aufbauen
    import pv_forecast
    try:
        forecast_pv = pv_forecast.get_hourly_pv_forecast()
    except Exception:
        forecast_pv = [0.0] * 24

    global_hour_defaults = {
        0: 0.3, 1: 0.3, 2: 0.3, 3: 0.3, 4: 0.3, 5: 0.4,
        6: 0.6, 7: 1.2, 8: 1.0, 9: 0.8, 10: 0.7, 11: 1.5,
        12: 1.8, 13: 1.0, 14: 0.8, 15: 0.7, 16: 0.9, 17: 1.5,
        18: 2.0, 19: 1.8, 20: 1.2, 21: 0.8, 22: 0.5, 23: 0.4
    }

    matrix = []
    for i, item in enumerate(market_data[:24]):    
        hour = item['hour']
        matrix.append({
            "hour": hour,
            "k_act": item['price_buy'],
            "expected_p_act": global_hour_defaults.get(hour, 0.5),
            "expected_p_pv": forecast_pv[i] if i < len(forecast_pv) else 0.0
        })

    # 4. Zeithorizont-Simulation durchrechnen
    chart_rows = []
    sim_soc = current_soc
    battery_capacity_kwh = 10.0
    max_soc_limit = 100.0
    min_soc_limit = 5.0

    for i, row in enumerate(matrix):
        h = row["hour"]
        price = row["k_act"]
        p_pv = row["expected_p_pv"]
        p_cons = row["expected_p_act"]
        net_pv_surplus = p_pv - p_cons
        
        # Korrektur: Unpacking erweitert um den 3. Rückgabewert (target_soc)
        mode, target_power, target_soc = optimizer.heuristic_optimizer(matrix[i:], h, sim_soc)
        
        if mode == 1:
            batt_action = target_power
            action_text = "Zwangsladen aktiv"
        elif mode == 2:
            batt_action = max(0.0, net_pv_surplus)
            action_text = "Entladesperre aktiv"
        else:
            batt_action = net_pv_surplus
            action_text = "Automatikbetrieb"
            
        old_soc = sim_soc
        soc_change = (batt_action / battery_capacity_kwh) * 100
        sim_soc += soc_change
        
        if sim_soc > max_soc_limit:
            actual_charge_pct = max_soc_limit - old_soc
            batt_action = (actual_charge_pct / 100) * battery_capacity_kwh
            sim_soc = max_soc_limit
        elif sim_soc < min_soc_limit:
            actual_discharge_pct = old_soc - min_soc_limit
            batt_action = -((actual_discharge_pct / 100) * battery_capacity_kwh)
            sim_soc = min_soc_limit
            
        chart_rows.append({
            "Uhrzeit": f"{h:02d}:00",
            "Geplante Batterie-Aktion (kW)": round(batt_action, 2),
            "Strompreis (Cent/kWh)": round(price, 2),
            "Simulierter SoC (%)": round(sim_soc, 1),
            "Steuerbefehl": action_text
        })

    df = pd.DataFrame(chart_rows)

    # 5. Grafik-Funktion aufrufen
    render_optimization_chart(df)

    # 6. Datentabelle Details ausgeben
    st.subheader("📋 Simulations-Details (Nächste 24 Stunden)")
    st.markdown("Hier sind die exakten mathematischen Stundenslots aufgelistet, die als Grundlage für den Chart dienen:")
    
    # Behebung der Warnung: use_container_width=True durch width='stretch' ersetzt
    st.dataframe(df, width='stretch')

    # 7. Automatischer Intervall-Refresh
    st.markdown("---")
    refresh_minutes = int(getattr(config, 'LOOP_TIMEOUT', 720) / 60)
    st.caption(f"🔄 Automatischer Daten-Refresh aktiv. Nächste Aktualisierung in {refresh_minutes} Minuten...")

if __name__ == "__main__":
    main()