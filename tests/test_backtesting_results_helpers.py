# tests/test_backtesting_results_helpers.py
"""Tests für Backtesting-Ergebnis-Hilfsfunktionen (1.25.c)."""
from __future__ import annotations

from datetime import datetime

import pandas as pd

from simulation.backtesting_log import consumption_totals_from_report
from simulation.engine import HISTORICAL_REFERENCE_ID, PlausibilityReport, PlausibilityResult
from ui.backtesting_results_helpers import (
    build_annual_cost_rows,
    build_scenario_consumption_rows,
    cons_data_has_flex_energy,
    is_single_month_test_run,
    nav_bounds_from_period,
    reference_consumption_subheader,
    reference_kwh_for_period,
    format_test_run_caption,
    scenario_consumption_subheader,
)


def _sample_cons_df() -> pd.DataFrame:
    idx = pd.date_range("2025-03-01", periods=24 * 31, freq="h", name="timestamp")
    return pd.DataFrame(
        {
            "total_kw": [1.0] * len(idx),
            "baseload_kw": [0.5] * len(idx),
            "pv_kw": [0.0] * len(idx),
        },
        index=idx,
    )


def test_is_single_month_test_run_true():
    period = {"start_month": 3, "end_month": 3}
    assert is_single_month_test_run(period) is True


def test_is_single_month_test_run_false_for_full_year():
    period = {"start_month": None, "end_month": None}
    assert is_single_month_test_run(period) is False


def test_is_single_month_test_run_false_for_different_months():
    period = {"start_month": 1, "end_month": 12}
    assert is_single_month_test_run(period) is False


def test_format_test_run_caption():
    period = {"start_month": 3, "end_month": 3, "backtesting_year": 2025}
    assert format_test_run_caption(period) == "Testlauf — nur Monat 03/2025"


def test_format_test_run_caption_none_for_full_year():
    assert format_test_run_caption({"start_month": None, "end_month": None}) is None


def test_nav_bounds_from_period_includes_end_of_day():
    period = {"start": "2025-03-01", "end": "2025-03-31"}
    start, end = nav_bounds_from_period(period)
    assert start == datetime(2025, 3, 1, 0, 0, 0)
    assert end == datetime(2025, 3, 31, 23, 59, 59)


def test_nav_bounds_from_period_none_without_dates():
    assert nav_bounds_from_period({}) is None


def test_reference_kwh_for_period_march():
    period = {"start": "2025-03-01", "end": "2025-03-31"}
    kwh = reference_kwh_for_period(_sample_cons_df(), period)
    assert kwh == 744.0


def test_build_annual_cost_rows_reference_kwh_and_delta():
    meta = {
        "reference_id": HISTORICAL_REFERENCE_ID,
        "labels": {
            HISTORICAL_REFERENCE_ID: "Historisch",
            "live": "Live",
        },
        "summary": {
            "total_eur": {
                HISTORICAL_REFERENCE_ID: 1200.0,
                "live": 1000.0,
            },
        },
    }
    rows = build_annual_cost_rows(meta, ref_kwh=5000.0)
    assert len(rows) == 2
    ref_row = next(r for r in rows if r["Szenario"] == "Historisch")
    assert ref_row["Jahres-kWh"] == "5000"
    assert ref_row["Δ vs. Referenz"] == "—"
    live_row = next(r for r in rows if r["Szenario"] == "Live")
    assert live_row["Jahres-kWh"] == "—"
    assert live_row["Δ vs. Referenz"] == "-200.00 €"


def test_reference_consumption_subheader_test_run():
    period = {"start_month": 3, "end_month": 3, "backtesting_year": 2025}
    assert reference_consumption_subheader(period) == (
        "Referenz-Verbrauch (Testmonat 03/2025, nicht optimiert)"
    )


def test_reference_consumption_subheader_full_year():
    assert reference_consumption_subheader({}) == "Referenz-Jahresverbrauch (nicht optimiert)"


def test_cons_data_has_flex_energy_false_without_consumer_columns(monkeypatch):
    monkeypatch.setattr(
        "ui.backtesting_results_helpers.config.get_flexible_consumers",
        lambda: [{"id": "eauto"}],
    )
    df = _sample_cons_df()
    assert cons_data_has_flex_energy(df) is False


def test_cons_data_has_flex_energy_true_with_consumer_data(monkeypatch):
    monkeypatch.setattr(
        "ui.backtesting_results_helpers.config.get_flexible_consumers",
        lambda: [{"id": "eauto"}],
    )
    df = _sample_cons_df()
    df["eauto_kw"] = 0.5
    assert cons_data_has_flex_energy(df) is True


def test_consumption_totals_from_report_sums_windows():
    report = PlausibilityReport()
    report.add(
        PlausibilityResult(
            window_end=datetime(2025, 1, 1, 0, 0),
            historical_kwh=10.0,
            optimized_kwh=10.5,
            diff_kwh=0.5,
            ok=True,
            historical_baseload_kwh=6.0,
            optimized_baseload_kwh=6.0,
            historical_flex_kwh=4.0,
            optimized_flex_kwh=4.5,
            baseload_diff_kwh=0.0,
            flex_diff_kwh=0.5,
        )
    )
    report.add(
        PlausibilityResult(
            window_end=datetime(2025, 1, 2, 0, 0),
            historical_kwh=12.0,
            optimized_kwh=11.0,
            diff_kwh=1.0,
            ok=False,
            historical_baseload_kwh=7.0,
            optimized_baseload_kwh=7.0,
            historical_flex_kwh=5.0,
            optimized_flex_kwh=4.0,
            baseload_diff_kwh=0.0,
            flex_diff_kwh=1.0,
        )
    )
    totals = consumption_totals_from_report(report)
    assert totals["historical_kwh"] == 22.0
    assert totals["optimized_kwh"] == 21.5
    assert totals["delta_kwh"] == -0.5
    assert totals["historical_flex_kwh"] == 9.0
    assert totals["optimized_flex_kwh"] == 8.5


def test_build_scenario_consumption_rows_includes_reference_and_optimized():
    meta = {
        "reference_id": HISTORICAL_REFERENCE_ID,
        "scenario_ids": ["live"],
        "labels": {
            HISTORICAL_REFERENCE_ID: "Historisch",
            "live": "Live",
        },
        "plausibility": {
            "live": {
                "ok_count": 29,
                "total_windows": 31,
                "consumption_totals": {
                    "historical_kwh": 500.0,
                    "optimized_kwh": 520.5,
                    "delta_kwh": 20.5,
                },
            },
        },
    }
    rows = build_scenario_consumption_rows(meta, ref_kwh=500.0)
    assert len(rows) == 2
    ref_row = next(r for r in rows if r["Szenario"] == "Historisch")
    assert ref_row["Historisch (kWh)"] == "500.0"
    assert ref_row["Optimiert (kWh)"] == "500.0"
    assert ref_row["Δ kWh (Opt−Hist)"] == "+0.0"
    live_row = next(r for r in rows if r["Szenario"] == "Live")
    assert live_row["Optimiert (kWh)"] == "520.5"
    assert live_row["Δ kWh (Opt−Hist)"] == "+20.5"
    assert live_row["Plausibilität"] == "29/31 OK"


def test_scenario_consumption_subheader_test_run():
    period = {"start_month": 1, "end_month": 1, "backtesting_year": 2025}
    assert scenario_consumption_subheader(period) == (
        "Verbrauchsvergleich (Debug, Testmonat 01/2025)"
    )
