# app.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import importlib

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

def update_config_file(settings_dict):
    """Aktualisiert alle übergebenen Parameter über die zentrale Laufzeit-Schnittstelle der config.py."""
    try:
        # 1. Werte in die JSON-Konfiguration schreiben
        config.update_runtime_settings(settings_dict)
        
        # 2. BEHOBEN: Modul im RAM neu laden, damit Streamlit die JSON-Änderungen sofort übernimmt
        importlib.reload(config)
        
        st.success("✅ Alle Parameter erfolgreich gespeichert und im System aktualisiert!")
    except Exception as e:
        st.error(f"🚨 Fehler beim Speichern der Konfiguration: {e}")

def get_runtime_settings() -> dict:
    return {
        'PV_KWP': getattr(config, 'PV_KWP'),
        'PV_TILT': getattr(config, 'PV_TILT'),
        'PV_AZIMUTH': getattr(config, 'PV_AZIMUTH'),
        'K_PUSH_CENT': getattr(config, 'K_PUSH_CENT'),
        'BATTERY_CAPACITY_KWH': getattr(config, 'BATTERY_CAPACITY_KWH'),
        'BATTERY_MIN_SOC': getattr(config, 'BATTERY_MIN_SOC'),
        'BATTERY_MAX_SOC': getattr(config, 'BATTERY_MAX_SOC'),
        'BATTERY_MAX_POWER_KW': getattr(config, 'BATTERY_MAX_POWER_KW'),
    }


def render_pv_config_inputs(settings: dict):
    st.markdown("#### ☀️ PV-Anlage")
    kwp = st.number_input("PV Leistung (kWp)", min_value=0.0, value=float(settings['PV_KWP']), step=0.1, format="%.2f")
    tilt = st.number_input("Dachneigung (°)", min_value=0, max_value=90, value=int(settings['PV_TILT']))
    azimuth = st.number_input(
        "Ausrichtung (Azimut °)",
        min_value=-180,
        max_value=180,
        value=int(settings['PV_AZIMUTH']),
        help="0=Süd, -90=Ost, 90=West"
    )
    k_push = st.number_input(
        "Einspeisevergütung (Cent/kWh)",
        min_value=0.0,
        value=float(settings['K_PUSH_CENT']),
        step=0.1,
        format="%.2f"
    )
    return kwp, tilt, azimuth, k_push


def render_battery_config_inputs(settings: dict):
    st.markdown("#### 🔋 Batterie-Speicher")
    bat_capacity = st.number_input(
        "Speicher-Kapazität (kWh)",
        min_value=0.1,
        value=float(settings['BATTERY_CAPACITY_KWH']),
        step=0.5,
        format="%.1f"
    )
    bat_min_soc = st.number_input(
        "Minimaler SoC (%)",
        min_value=0.0,
        max_value=100.0,
        value=float(settings['BATTERY_MIN_SOC']),
        step=1.0
    )
    bat_max_soc = st.number_input(
        "Maximaler SoC (%)",
        min_value=0.0,
        max_value=100.0,
        value=float(settings['BATTERY_MAX_SOC']),
        step=1.0
    )
    bat_max_power = st.number_input(
        "Max. Lade-/Entladeleistung (kW)",
        min_value=0.1,
        value=float(settings['BATTERY_MAX_POWER_KW']),
        step=0.1,
        format="%.2f"
    )
    return bat_capacity, bat_min_soc, bat_max_soc, bat_max_power


def render_config_form(settings: dict):
    with st.sidebar.form("config_form"):
        kwp, tilt, azimuth, k_push = render_pv_config_inputs(settings)
        bat_capacity, bat_min_soc, bat_max_soc, bat_max_power = render_battery_config_inputs(settings)

        submit_btn = st.form_submit_button("Alle Änderungen übernehmen")
        if submit_btn:
            update_config_file({
                "PV_KWP": kwp,
                "PV_TILT": tilt,
                "PV_AZIMUTH": azimuth,
                "K_PUSH_CENT": k_push,
                "BATTERY_CAPACITY_KWH": bat_capacity,
                "BATTERY_MIN_SOC": bat_min_soc,
                "BATTERY_MAX_SOC": bat_max_soc,
                "BATTERY_MAX_POWER_KW": bat_max_power
            })
            st.rerun()


def render_pv_tuning_sidebar():
    st.sidebar.markdown("---")
    st.sidebar.subheader("📈 Adaptives PV-Tuning")

    try:
        tuning_factor = pv_tuner.calculate_tuning_factor(days_back=14)
        deviation_pct = (tuning_factor - 1.0) * 100

        if tuning_factor == 1.0:
            delta_text = "Keine Abweichung (Basis)"
            delta_color = "off"
        elif tuning_factor > 1.0:
            delta_text = f"+{deviation_pct:.1f}% Mehrertrag vs. Prognose"
            delta_color = "normal"
        else:
            delta_text = f"{deviation_pct:.1f}% Minderertrag vs. Prognose"
            delta_color = "inverse"

        st.sidebar.metric(
            label="Aktueller Korrekturfaktor",
            value=f"{tuning_factor:.2f}",
            delta=delta_text,
            delta_color=delta_color
        )
    except Exception as e:
        st.sidebar.warning(f"⚠️ Tuning-Faktor konnte nicht berechnet werden: {e}")

    st.sidebar.caption(
        "Errechnet aus dem automatischen Abgleich zwischen Forecast.Solar "
        "und deinen realen Loxone-Zählerständen der vergangenen 2 Wochen."
    )


def render_parameter_input():
    st.sidebar.header("⚙️ System-Parameter")
    st.sidebar.markdown("Änderungen werden direkt über das Konfigurationsmodul angewendet.")

    render_config_form(get_runtime_settings())
    render_pv_tuning_sidebar()


def get_bar_colors(df):
    return [
        "forestgreen" if "Zwangsladen" in cmd else
        "crimson" if "Entladesperre" in cmd or "Entladen" in cmd else
        "dodgerblue"
        for cmd in df["Steuerbefehl"]
    ]


def add_power_traces(fig, df, bar_colors):
    if "PV-Prognose (kW)" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["Uhrzeit"],
            y=df["PV-Prognose (kW)"],
            name="PV-Ertrag Prognose (kW)",
            line=dict(color='#f1c40f', width=2),
            fill='tozeroy',
            fillcolor='rgba(241, 196, 15, 0.15)',
            yaxis="y"
        ))

    if "Verbrauch-Prognose (kW)" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["Uhrzeit"],
            y=df["Verbrauch-Prognose (kW)"],
            name="Historischer Verbrauch (kW)",
            line=dict(color='#3498db', width=2, dash='dash'),
            yaxis="y"
        ))

    fig.add_trace(go.Bar(
        x=df["Uhrzeit"],
        y=df["Geplante Batterie-Aktion (kW)"],
        name="Batterie-Aktion (kW)",
        marker=dict(color=bar_colors),
        opacity=0.75,
        offset=0.05,
        width=0.9,
        offsetgroup="bars",
        yaxis="y"
    ))


def add_price_soc_traces(fig, df):
    fig.add_trace(go.Scatter(
        x=df["Uhrzeit"],
        y=df["Strompreis (Cent/kWh)"],
        name="Brutto-Strompreis (Cent)",
        mode="lines",
        line=dict(color="red", width=3, shape="hv"),
        yaxis="y2"
    ))

    fig.add_trace(go.Scatter(
        x=df["Uhrzeit"],
        y=df["Simulierter SoC (%)"],
        name="Simulierter Speicher-SoC (%)",
        mode="lines",
        line=dict(color="gold", width=2.5, dash="dash"),
        yaxis="y2"
    ))


def render_optimization_chart(df):
    """Zeichnet Leistungen (PV, Verbrauch, Batterie) und Preise/SoC über zwei Y-Achsen."""
    bar_colors = get_bar_colors(df)
    fig = go.Figure()

    add_power_traces(fig, df, bar_colors)
    add_price_soc_traces(fig, df)

    fig.update_layout(
        title="Synchronisierter 24-Stunden-Zeithorizont (Leistung vs. Preis & SoC)",
        xaxis=dict(title="Uhrzeit (Stunden-Slots / Intervalle)", type="category"),
        barmode="overlay",
        yaxis=dict(title="Leistung (kW)", side="left"),
        yaxis2=dict(title="Preis (Cent/kWh) / SoC (%)", side="right", overlaying="y", showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=80, b=40)
    )

    st.plotly_chart(fig, width='stretch')


def fetch_market_data():
    market_data = awattar_client.fetch_awattar_prices()
    if not market_data:
        st.error("🚨 Fehler: Börsenstrompreise von aWATTar konnten nicht geladen werden. Abbruch der Simulation.")
        return None
    return market_data


def build_simulation_dataframe(matrix, current_soc):
    chart_rows = []
    sim_soc = current_soc
    battery_capacity_kwh = float(getattr(config, 'BATTERY_CAPACITY_KWH'))
    max_soc_limit = float(getattr(config, 'BATTERY_MAX_SOC'))
    min_soc_limit = float(getattr(config, 'BATTERY_MIN_SOC'))

    for i, row in enumerate(matrix):
        h = row["hour"]
        price = row["k_act"]
        p_pv = row["expected_p_pv"]
        p_cons = row["expected_p_act"]
        net_pv_surplus = p_pv - p_cons

        mode, target_power, _ = optimizer.heuristic_optimizer(matrix[i:], h, sim_soc)

        if mode == 1:
            batt_action = target_power
            action_text = "Zwangsladen active"
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
            "Simulierter SoC (%)": round(old_soc, 1),
            "Steuerbefehl": action_text,
            "PV-Prognose (kW)": round(p_pv, 2),
            "Verbrauch-Prognose (kW)": round(p_cons, 2)
        })

    return pd.DataFrame(chart_rows)


def render_simulation_details(df):
    st.subheader("📋 Simulations-Details (Nächste 24 Stunden)")
    st.markdown("Hier sind die exakten mathematischen Stundenslots aufgelistet, die als Grundlage für den Chart dienen:")
    st.dataframe(df, width='stretch')


def render_refresh_caption():
    st.markdown("---")
    loop_timeout = getattr(config, 'LOOP_TIMEOUT', 720)
    refresh_minutes = int(loop_timeout / 60) if loop_timeout else 12
    st.caption(f"🔄 Automatischer Daten-Refresh aktiv. Taktung der Hauptschleife beträgt {refresh_minutes} Minuten...")


def main():
    st.title("🔋 Ernie Energy Control Center")
    st.markdown("Echtzeit-Cockpit und Vorhersage-Simulation des synchronisierten 24-Stunden-Horizonts.")

    # 1. Parameter-Eingabemaske rendern
    render_parameter_input()

    # Live SoC abrufen
    current_soc = loxone_client.fetch_loxone_soc()
    if current_soc is None:
        current_soc = 50.0
        st.warning("⚠️ Live-Batteriestand konnte nicht von Loxone geladen werden. Simulation läuft mit 50% Fallback-SoC.")
    else:
        st.info(f"⚡ Aktueller Batterie-Ladezustand (Live-SoC): **{current_soc}%**")

    # 2. Marktdaten beschaffen
    st.subheader("📈 Last- & Preisverlauf")
    market_data = fetch_market_data()
    if market_data is None:
        return

    _, _, matrix = profile_manager.get_forecast_vectors(market_data)
    df = build_simulation_dataframe(matrix, current_soc)

    render_optimization_chart(df)
    render_simulation_details(df)
    render_refresh_caption()

if __name__ == "__main__":
    main()