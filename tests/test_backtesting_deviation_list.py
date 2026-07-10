"""Tests für Backtesting-Abweichungsliste (1.25.d)."""
from __future__ import annotations

from simulation.engine import HISTORICAL_REFERENCE_ID
from ui.backtesting_deviation_list import (
    KIND_LABELS,
    build_deviation_table_rows,
    case_to_plausibility_failure,
    deviation_cases_for_display,
    format_deviation_delta_kwh,
    format_deviation_select_label,
    kind_label,
    _resolve_chart_view,
)
from ui.backtesting_display_bundle import VIEW_MODE_24H, VIEW_MODE_SUNSET
from simulation.horizon_mode import SUNSET_WINDOW


def _sample_meta() -> dict:
    return {
        "reference_id": HISTORICAL_REFERENCE_ID,
        "labels": {
            HISTORICAL_REFERENCE_ID: "Historisch",
            "runtime_settings": "Runtime",
        },
        "critical_cases": [
            {
                "kind": "consumption_tolerance",
                "scenario_id": "runtime_settings",
                "window_anchor": "2025-08-01T07:00:00",
                "historical_kwh": 32.0,
                "optimized_kwh": 34.0,
                "diff_kwh": 2.0,
            },
            {
                "kind": "strict_slow",
                "scenario_id": "runtime_settings",
                "window_anchor": "2025-09-28T10:00:00",
                "slot_datetime": "2025-09-27T10:00:00",
                "simulation_hour_index": 1392,
                "strict_elapsed_sec": 3.01,
            },
            {
                "kind": "consumption_tolerance",
                "scenario_id": HISTORICAL_REFERENCE_ID,
                "window_anchor": "2025-07-01T07:00:00",
                "diff_kwh": 5.0,
            },
        ],
    }


def test_deviation_cases_for_display_excludes_reference():
    cases = deviation_cases_for_display(_sample_meta())
    scenario_ids = {c["scenario_id"] for c in cases}
    assert HISTORICAL_REFERENCE_ID not in scenario_ids
    assert len(cases) == 2


def test_deviation_cases_for_display_preserves_sort_order():
    cases = deviation_cases_for_display(_sample_meta())
    anchors = [c.get("window_anchor") or "" for c in cases]
    assert anchors == sorted(anchors)


def test_format_deviation_delta_kwh():
    plaus = {"kind": "consumption_tolerance", "diff_kwh": 1.25}
    cbc = {"kind": "strict_slow"}
    assert format_deviation_delta_kwh(plaus) == "+1.25"
    assert format_deviation_delta_kwh(cbc) == "—"


def test_build_deviation_table_rows_columns():
    meta = _sample_meta()
    cases = deviation_cases_for_display(meta)
    rows = build_deviation_table_rows(cases, meta["labels"], meta)
    assert len(rows) == 2
    assert set(rows[0].keys()) == {
        "Fenster",
        "Szenario",
        "Art",
        "Δ kWh (Soll/Ist)",
    }
    tolerance_row = next(r for r in rows if r["Art"] == KIND_LABELS["consumption_tolerance"])
    cbc_row = next(r for r in rows if r["Art"] == KIND_LABELS["strict_slow"])
    assert tolerance_row["Δ kWh (Soll/Ist)"] == "+2.00"
    assert cbc_row["Δ kWh (Soll/Ist)"] == "—"
    assert tolerance_row["Szenario"] == "Runtime"
    assert "2025-08-01 07:00" in tolerance_row["Fenster"]


def test_kind_label_known_and_unknown():
    assert kind_label("strict_fallback") == "CBC Fallback"
    assert kind_label("custom_event") == "custom_event"


def test_case_to_plausibility_failure_maps_window_anchor():
    case = {
        "window_anchor": "2025-08-01T07:00:00",
        "historical_kwh": 10.0,
        "optimized_kwh": 12.0,
        "diff_kwh": 2.0,
    }
    failure = case_to_plausibility_failure(case)
    assert failure["window_end"] == "2025-08-01T07:00:00"
    assert failure["diff_kwh"] == 2.0


def test_format_deviation_select_label():
    row = {
        "Fenster": "2025-08-01 07:00",
        "Szenario": "Runtime",
        "Art": "Verbrauchstoleranz",
        "Δ kWh (Soll/Ist)": "+2.00",
    }
    label = format_deviation_select_label(row)
    assert "Runtime" in label
    assert "+2.00" in label


def test_resolve_chart_view_from_deviation_list():
    sunset_meta = {"period": {"horizon_mode": SUNSET_WINDOW}}
    assert _resolve_chart_view(
        sunset_meta,
        segment_toggle="SA₀→SA₁",
    ) == (VIEW_MODE_SUNSET, 0)
