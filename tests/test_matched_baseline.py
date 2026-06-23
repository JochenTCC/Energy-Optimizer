"""Tests für Profil- und Ziel-Baseline in der Simulation."""
from __future__ import annotations

from optimizer.simulation import (
    build_matched_flex_kw_per_hour,
    delivered_flex_kwh_from_rows,
    simulate_baseline_horizon,
    simulate_matched_baseline_horizon,
    total_consumption_kwh_from_rows,
)


def _sample_matrix() -> list[dict]:
    return [
        {
            "hour": h,
            "expected_p_pv": 1.0,
            "expected_p_act": 0.5,
            "k_act": 20.0,
            "expected_flex_kw": {
                "swimspa": 1.0 if h < 12 else 0.0,
                "eauto": 0.5,
                "waermepumpe": 0.0,
            },
        }
        for h in range(24)
    ]


def test_build_matched_flex_scales_to_target():
    matrix = _sample_matrix()
    targets = {"swimspa": 6.0, "eauto": 12.0, "waermepumpe": 0.0}
    per_hour = build_matched_flex_kw_per_hour(matrix, targets)

    assert len(per_hour) == 24
    swimspa_sum = sum(hour["swimspa"] for hour in per_hour)
    eauto_sum = sum(hour["eauto"] for hour in per_hour)
    assert abs(swimspa_sum - 6.0) < 0.01
    assert abs(eauto_sum - 12.0) < 0.01
    assert all(hour["swimspa"] == 0.0 for hour in per_hour[12:])


def test_matched_baseline_matches_optimized_consumption_total():
    matrix = _sample_matrix()
    targets = {"swimspa": 6.0, "eauto": 12.0, "waermepumpe": 0.0}
    profile_rows = simulate_baseline_horizon(matrix, initial_soc=50.0)
    matched_rows = simulate_matched_baseline_horizon(matrix, 50.0, targets)

    profile_kwh = total_consumption_kwh_from_rows(profile_rows)
    matched_kwh = total_consumption_kwh_from_rows(matched_rows)
    matched_flex = delivered_flex_kwh_from_rows(matched_rows)

    assert matched_kwh < profile_kwh
    assert abs(matched_flex["swimspa"] - 6.0) < 0.05
    assert abs(matched_flex["eauto"] - 12.0) < 0.05
    assert all(row["Steuerbefehl"] == "Baseline (Ziel)" for row in matched_rows)


def test_hourly_savings_sum_matches_total():
    matrix = _sample_matrix()
    targets = {"swimspa": 6.0, "eauto": 12.0, "waermepumpe": 0.0}
    matched_rows = simulate_matched_baseline_horizon(matrix, 50.0, targets)
    profile_rows = simulate_baseline_horizon(matrix, initial_soc=50.0)

    from optimizer.simulation import hourly_savings_euro_from_rows, calculate_cost_euro_from_rows

    sell = 3.5
    hourly = hourly_savings_euro_from_rows(matched_rows, profile_rows, sell)
    matched_cost = calculate_cost_euro_from_rows(matched_rows, sell)
    profile_cost = calculate_cost_euro_from_rows(profile_rows, sell)
    assert abs(sum(hourly) - (matched_cost - profile_cost)) < 0.001
