"""Analyse Verbrauch & Kosten: Live-Log attribution plus Swimspa section."""
from __future__ import annotations

import streamlit as st

from ui.chart_context import live_now
from ui.consumer_analysis_charts import (
    render_swimspa_filter_chart,
    render_swimspa_temperature_chart,
)
from ui.consumer_analysis_data import build_swimspa_analysis_data
from ui.consumer_cost_analysis_charts import render_week_analysis
from ui.consumer_cost_analysis_data import (
    build_cost_analysis_series,
    iso_weeks_in_slots,
)
from ui.consumption_display.navigation import render_iso_week_navigation
from ui.help_hint import render_page_title_with_help
from ui.history_navigation import get_s2_cycle_offset, get_s2_segment_index

_HELP = (
    "Analyse aus dem Produktiv-Log: Verbrauch je Verbraucher vs. Preis/PV, "
    "Herkunft (PV / Batterie / Netz) und grobe Kosten nur für den Netzanteil. "
    "Summen für KW / Monat / Jahr beziehen sich auf vorhandene Log-Daten — "
    "keine Rechnungskorrektur. Swimspa-Temperatur und Filter unten."
)


def _render_cost_section() -> None:
    now = live_now()
    series = build_cost_analysis_series(now=now)
    if series is None or not series.slots:
        st.info("Noch keine Produktiv-Log-Daten für die Verbrauchs- & Kostenanalyse.")
        return

    weeks = iso_weeks_in_slots(series.slots)
    if not weeks:
        st.info("Keine Kalenderwochen im Produktiv-Log.")
        return

    timestamps = [slot.slot_start.isoformat() for slot in series.slots]
    # Prefer latest ISO week on first visit (nav helper defaults to oldest).
    week_idx_key = "cost_analysis_week_idx"
    week_reset_key = "cost_analysis_week_reset"
    reset_token = "cost_analysis_v1"
    if st.session_state.get(week_reset_key) != reset_token:
        st.session_state[week_reset_key] = reset_token
        st.session_state[week_idx_key] = max(0, len(weeks) - 1)
    selected = render_iso_week_navigation(
        timestamps,
        key_prefix="cost_analysis",
        reset_token=reset_token,
    )
    if selected is None:
        return
    iso_year, iso_week = selected
    render_week_analysis(
        series,
        iso_year=iso_year,
        iso_week=iso_week,
        now=now,
    )


def _render_swimspa_section() -> None:
    st.markdown("#### Swimspa")
    data = build_swimspa_analysis_data(
        cycle_offset=get_s2_cycle_offset(),
        segment_index=get_s2_segment_index(),
    )
    if data is None:
        st.info(
            "Für dieses S-2-Segment liegen keine Historien-Daten vor "
            "(SA₁→SA₂ zeigt nur MILP-Prognose)."
        )
        return
    if data.gap_notice:
        st.caption(data.gap_notice)
    render_swimspa_temperature_chart(data.temperature_df, chart_zones=data.zones)
    render_swimspa_filter_chart(data.filter_df, chart_zones=data.zones)


def render() -> None:
    render_page_title_with_help(
        "📈 Analyse Verbrauch & Kosten",
        _HELP,
        key="consumer_analysis_help",
    )
    _render_cost_section()
    st.divider()
    _render_swimspa_section()
