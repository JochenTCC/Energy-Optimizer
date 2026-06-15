# app.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import importlib
import os

# Bestehende Projektmodule importieren
import config
import loxone_client
import awattar_client
import profile_manager
import optimizer

st.set_page_config(
    page_title="Ernie Energy Control Center",
    page_icon="🔋",
    layout="wide"
)

def update_config_file(kwp, tilt, azimuth, k_push):
    """
    Schreibt die veränderten UI-Parameter dauerhaft zurück in die config.py,
    ohne andere Konfigurationen oder Kommentare zu zerstören.
    """
    config_path = "config.py"
    if not os.path.exists(config_path):
        st.error("🚨 config.py nicht gefunden!")
        return False
        
    with open(config_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    new_lines = []
    updated_keys = set()
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("PV_KWP =") or stripped.startswith("PV_KWP="):
            new_lines.append(f"PV_KWP = {kwp}  # Automatisch über Web-UI aktualisiert\n")
            updated_keys.add("PV_KWP")
        elif stripped.startswith("PV_TILT =") or stripped.startswith("PV_TILT="):
            new_lines.append(f"PV_TILT = {tilt}  # Automatisch über Web-UI aktualisiert\n")
            updated_keys.add("PV_TILT")
        elif stripped.startswith("PV_AZIMUTH =") or stripped.startswith("PV_AZIMUTH="):
            new_lines.append(f"PV_AZIMUTH = {azimuth}  # Automatisch über Web-UI aktualisiert\n")
            updated_keys.add("PV_AZIMUTH")
        elif stripped.startswith("K_PUSH =") or stripped.startswith("K_PUSH="):
            new_lines.append(f"K_PUSH = {k_push}  # Automatisch über Web-UI aktualisiert\n")
            updated_keys.add("K_PUSH")
        else:
            new_lines.append(line)
            
    if "PV_KWP" not in updated_keys: new_lines.append(f"PV_KWP = {kwp}\n")
    if "PV_TILT" not in updated_keys: new_lines.append(f"PV_TILT = {tilt}\n")
    if "PV_AZIMUTH" not in updated_keys: new_lines.append(f"PV_AZIMUTH = {azimuth}\n")
    if "K_PUSH" not in updated_keys: new_lines.append(f"K_PUSH = {k_push}\n")
    
    with open(config_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
        
    importlib.reload(config)
    return True

# ==============================================================================
# SIDEBAR - PARAMETER-FEINOPTIMIERUNG
# ==============================================================================
st.sidebar.title("⚙️ Anlagen-Konfiguration")
st.sidebar.markdown("Justiere hier die Kernparameter deiner PV-Anlage. Ein Klick auf Speichern berechnet die Prognose-Vektoren sofort neu.")

current_kwp = float(getattr(config, 'PV_KWP', 6.0))
current_tilt = int(getattr(config, 'PV_TILT', 18))
current_azimuth = int(getattr(config, 'PV_AZIMUTH', 28))
current_k_push = float(getattr(config, 'K_PUSH', 8.2))

st.sidebar.subheader("PV-Generator")
ui_kwp = st.sidebar.slider("Installierte Leistung (kWp)", 1.0, 25.0, current_kwp, 0.1, help="Maximale Peak-Leistung deiner Solarmodule.")
ui_tilt = st.sidebar.slider("Neigungswinkel (°)", 0, 90, current_tilt, 1, help="0° = flach liegend, 90° = senkrecht an der Fassade.")
ui_azimuth = st.sidebar.slider("Ausrichtung / Azimuth (°)", -180, 180, current_azimuth, 1, help="Süden = 0°, Westen = 90°, Norden = 180°, Osten = -90°.")

st.sidebar.subheader("Wirtschaftlichkeit")
ui_k_push = st.sidebar.number_input("Einspeisevergütung (Cent/kWh)", min_value=0.0, max_value=40.0, value=current_k_push, step=0.1)

st.sidebar.markdown("---")
if st.sidebar.button("💾 Parameter speichern & anwenden", type="primary"):
    if update_config_file(ui_kwp, ui_tilt, ui_azimuth, ui_k_push):
        st.sidebar.success("✅ config.py erfolgreich aktualisiert!")
        st.rerun()

# ==============================================================================
# HAUPTBEREICH - LIVE MONITORING & ZEITHORIZONT
# ==============================================================================
st.title("🔋 Ernie Energy Control Center")
st.markdown("### Interaktiver 24h-Optimierungsfahrplan (Testbetrieb)")

with st.spinner("⏳ Aktualisiere Live-Daten von Loxone, aWATTar und Forecast.Solar..."):
    current_soc = loxone_client.fetch_loxone_soc()
    if current_soc is None:
        current_soc = 50.0
        st.warning("⚠️ Loxone SoC konnte nicht live abgerufen werden. Verwende Dummy-Wert (50.0%) für die Simulation.")
        
    market_data = awattar_client.fetch_awattar_prices()
    forecast_consumption, forecast_pv = profile_manager.get_forecast_vectors()

if not market_data:
    st.error("🚨 Fehler: Es konnten keine Marktdaten von aWATTar geladen werden. Dashboard-Erstellung abgebrochen.")
else:
    # Synchronisierte Basis-Matrix aufbauen
    optimization_matrix = []
    for i, item in enumerate(market_data[:24]):
        optimization_matrix.append({
            "hour": item['hour'], 
            "k_act": item['price_buy'], 
            "expected_p_act": forecast_consumption[i], 
            "expected_p_pv": forecast_pv[i]
        })

    # --- ZENTRALE SIMULATION UND FAHRPLAN-GENERIERUNG ---
    chart_rows = optimizer.simulate_24h_horizon(optimization_matrix, current_soc)
    df = pd.DataFrame(chart_rows)
    
    # --- METRIKEN (TOP BANNER) ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Aktueller Batterie-SoC", f"{current_soc} %")
    
    current_price_row = df.iloc[0]
    col2.metric("Aktueller Börsenpreis", f"{current_price_row['Strompreis (Cent/kWh)']} Cnt/kWh")
    col3.metric("PV-Ertragsspitze (Heute)", f"{df['PV-Prognose (kW)'].max():.2f} kW")
    col4.metric("Nächster System-Befehl", current_price_row['Steuerbefehl'])
    
    st.markdown("---")
    
    # --- INTERAKTIVES PLOTLY CHART ---
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=df["Uhrzeit"], 
        y=df["Geplante Batterie-Aktion (kW)"], 
        name="Batterie Laden(+)/Entladen(-) (kW)", 
        marker_color='rgba(46, 204, 113, 0.7)',
        yaxis="y1"
    ))
    
    fig.add_trace(go.Scatter(
        x=df["Uhrzeit"], 
        y=df["PV-Prognose (kW)"], 
        name="PV-Prognose (kW)", 
        fill='tozeroy', 
        line=dict(color='#f1c40f', width=2),
        yaxis="y1"
    ))
    
    fig.add_trace(go.Scatter(
        x=df["Uhrzeit"], 
        y=df["Verbrauch-Prognose (kW)"], 
        name="Historischer Verbrauch (kW)", 
        line=dict(color='#3498db', width=2, dash='dash'),
        yaxis="y1"
    ))
    
    fig.add_trace(go.Scatter(
        x=df["Uhrzeit"], 
        y=df["Strompreis (Cent/kWh)"], 
        name="Börsenstrompreis (Cent)", 
        line=dict(color='#e74c3c', width=3, shape='hv'),
        yaxis="y2"
    ))
    
    fig.add_trace(go.Scatter(
        x=df["Uhrzeit"], 
        y=df["Simulierter SoC (%)"], 
        name="Simulierter Speicher-SoC (%)", 
        line=dict(color='#9b59b6', width=2, dash='dot'),
        yaxis="y2"
    ))
    
    fig.update_layout(
        title="Synchronisierter 24-Stunden-Zeithorizont (Leistung vs. Preis & SoC)",
        xaxis=dict(title="Uhrzeit (Stunden-Slots)"),
        yaxis=dict(title="Leistung (kW)", side="left"),
        yaxis2=dict(title="Strompreis (Cent/kWh) / SoC (%)", overlaying="y", side="right"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        hovermode="x unified",
        height=600
    )
    
    st.plotly_chart(fig, width="stretch")
    
    # --- TABELLEN-ANSICHT ---
    with st.expander("🔍 Rohe Berechnungs-Matrix einsehen (Datenbasis für Loxone)"):
        st.dataframe(
            df.set_index("Uhrzeit"), 
            width="stretch"
        )