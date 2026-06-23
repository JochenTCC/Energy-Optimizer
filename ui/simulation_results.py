"""Gemeinsame Darstellung von Simulationsergebnissen (Live + Historisch)."""
from __future__ import annotations

import logging

import streamlit as st
import pandas as pd

from runtime_store import live_optimization_debug
from ui.charts import render_optimization_chart

logger = logging.getLogger("app")


def calculate_scaled_consumption_and_cost(
    optimized_rows: list,
) -> tuple[float, float, float]:
    """Berechnet Gesamtverbrauch und Kosten ohne PV, skaliert auf 24h."""
    total_consumption_kwh = 0.0
    cost_without_pv_cents = 0.0

    for row in optimized_rows:
        consumption = row.get("Verbrauch-Prognose (kW)", 0.0)
        price_cent = row.get("Strompreis (Cent/kWh)", 0.0)
        total_consumption_kwh += consumption
        cost_without_pv_cents += consumption * price_cent

    cost_without_pv_euro = cost_without_pv_cents / 100.0
    num_hours = len(optimized_rows)
    scaling_factor = (24 / num_hours) if num_hours > 0 else 0.0

    consumption_24h = total_consumption_kwh * scaling_factor
    cost_without_pv_24h_euro = cost_without_pv_euro * scaling_factor

    return total_consumption_kwh, consumption_24h, cost_without_pv_24h_euro


def render_applied_targets(savings: dict) -> None:
    """Zeigt Baseline- und Optimierungsenergie je Verbraucher in einer Tabelle."""
    comparison = savings.get("energy_comparison") or []
    if not comparison:
        return

    with st.expander("⚡ Energievergleich Baseline vs. Optimierung (24h)"):
        st.caption(
            "BL Profil: historisches Flex-Profil. BL Ziel: gleiche Energie wie die Optimierung "
            "(Profil skaliert), ohne Lastverschiebung."
        )

        def _format_kwh_cell(kwh: float) -> str:
            return f"{kwh:.1f} kWh"

        def _format_optimization_cell(kwh: float, source: str) -> str:
            formatted = _format_kwh_cell(kwh)
            if source:
                return f"{formatted} ({source})"
            return formatted

        st.dataframe(
            pd.DataFrame([
                {
                    "Verbraucher": row["name"],
                    "BL Profil (kWh)": _format_kwh_cell(row["baseline_kwh"]),
                    "BL Ziel (kWh)": _format_kwh_cell(row.get("matched_baseline_kwh", 0.0)),
                    "Optimierung": _format_optimization_cell(
                        row["optimization_kwh"],
                        row.get("optimization_source", ""),
                    ),
                }
                for row in comparison
            ]),
            width="stretch",
            hide_index=True,
        )


def render_savings_metrics(savings: dict) -> None:
    """Rendert die finanzielle Metriken-Übersicht im Dashboard auf einheitlicher Zeitbasis."""
    st.subheader("💶 Optimierungs-Einsparungen")
    baseline_cost = savings.get("baseline_cost_euro", 0.0)
    matched_baseline_cost = savings.get("matched_baseline_cost_euro", baseline_cost)
    optimized_cost = savings.get("optimized_cost_euro", 0.0)
    matched_baseline_kwh = savings.get(
        "matched_baseline_consumption_kwh", savings.get("optimized_consumption_kwh", 0.0)
    )
    optimized_kwh = savings.get("optimized_consumption_kwh", 0.0)

    optimized_rows = savings.get("optimized_rows", [])
    _, _, cost_without_pv_24h_euro = calculate_scaled_consumption_and_cost(optimized_rows)

    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
    col1.metric(
        "Ohne PV (24h hochger.)",
        f"{cost_without_pv_24h_euro:.2f} €",
        help="Hochgerechnete Kosten bei 100 % Netzbezug ohne PV-Anlage auf einen vollen 24h-Horizont.",
    )
    col2.metric(
        "BL Profil",
        f"{baseline_cost:.2f} €",
        help="Baseline mit historischem Flex-Profil, ohne Lastverschiebung.",
    )
    col3.metric(
        "BL gleiches Ziel",
        f"{matched_baseline_cost:.2f} €",
        help=(
            "Baseline mit gleicher Flex-Energie wie die Optimierung (Profil skaliert), "
            "aber ohne Lastverschiebung."
        ),
    )
    col4.metric("Optimiert", f"{optimized_cost:.2f} €")
    col5.metric(
        "Verbrauch BL Ziel",
        f"{matched_baseline_kwh:.1f} kWh",
        help="Summe Grundlast + Flex in der Ziel-Baseline (entspricht dem Optimierungsziel).",
    )
    col6.metric(
        "Verbrauch Opt.",
        f"{optimized_kwh:.1f} kWh",
        help="Summe Grundlast + Flex über alle Stunden im 24h-Fenster.",
    )

    display_savings = optimized_cost - matched_baseline_cost
    col7.metric(
        "Ersparnis",
        f"{display_savings:.2f} €",
        delta=f"{display_savings:.2f} €",
        delta_color="inverse",
        help="Optimierte Kosten minus Baseline mit gleichem Verbrauchsziel (negativ = günstiger).",
    )


def render_simulation_details(
    df: pd.DataFrame,
    title: str = "📋 Simulations-Details (Nächste 24 Stunden)",
) -> None:
    with st.expander(title):
        st.markdown(
            "Hier sind die exakten mathematischen Stundenslots aufgelistet, "
            "die als Grundlage für den Chart dienen:"
        )
        st.dataframe(df, width="stretch")


def render_optimization_results(
    savings_info: dict,
    optimized_df: pd.DataFrame,
    baseline_df: pd.DataFrame,
    matched_baseline_df: pd.DataFrame | None = None,
    *,
    simulation_table_title: str | None = "📋 Simulations-Details (Nächste 24 Stunden)",
) -> None:
    if matched_baseline_df is None and savings_info.get("matched_baseline_rows"):
        matched_baseline_df = pd.DataFrame(savings_info["matched_baseline_rows"])
    render_savings_metrics(savings_info)
    render_optimization_chart(
        optimized_df,
        baseline_df,
        matched_baseline_df,
        hourly_savings_euro=savings_info.get("hourly_savings_euro"),
    )
    render_applied_targets(savings_info)
    if simulation_table_title:
        render_simulation_details(optimized_df, title=simulation_table_title)


def persist_simulation_debug(
    savings_info: dict,
    optimized_df: pd.DataFrame,
    baseline_df: pd.DataFrame,
    *,
    kind: str,
    initial_soc: float,
    main_state: dict | None = None,
    quarter_hour_slot: str | None = None,
    sync_reason: str | None = None,
    optimized_df_raw: pd.DataFrame | None = None,
    target_date: str | None = None,
    historical_meta: dict | None = None,
    matched_baseline_df: pd.DataFrame | None = None,
) -> None:
    """Schreibt Simulationsergebnis als JSON in runtime/ (Debug / Nachrechnen)."""
    if matched_baseline_df is None and savings_info.get("matched_baseline_rows"):
        matched_baseline_df = pd.DataFrame(savings_info["matched_baseline_rows"])
    try:
        payload = live_optimization_debug.build_debug_payload(
            savings_info,
            optimized_df.to_dict("records"),
            baseline_df.to_dict("records"),
            kind=kind,
            initial_soc=initial_soc,
            main_state=main_state,
            quarter_hour_slot=quarter_hour_slot,
            sync_reason=sync_reason,
            optimized_rows_raw=(
                optimized_df_raw.to_dict("records") if optimized_df_raw is not None else None
            ),
            target_date=target_date,
            historical_meta=historical_meta,
            matched_baseline_rows=(
                matched_baseline_df.to_dict("records")
                if matched_baseline_df is not None
                else None
            ),
        )
        live_optimization_debug.save_debug_snapshot(payload, kind=kind)
    except OSError as exc:
        logger.warning("Debug-Snapshot konnte nicht gespeichert werden: %s", exc)
