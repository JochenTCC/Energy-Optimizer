"""Tests for SE monthly standing charges (2.3.b)."""
from __future__ import annotations

import pandas as pd

from house_config.tariffs_store import _normalize_dach_fields
from simulation.backtesting_log import _build_summary
from simulation.monthly_fees import (
    monthly_fee_eur_from_params,
    monthly_fee_eur_from_specs,
    monthly_fees_by_result_id,
)
from ui.tariff_filter_helpers import tariff_parameter_rows


def test_monthly_fee_from_specs_sums_import_export() -> None:
    assert monthly_fee_eur_from_specs(
        {"monthly_fee_eur": 4.79},
        {"monthly_fee_eur": 1.0},
    ) == 5.79
    assert monthly_fee_eur_from_specs({"monthly_fee_eur": 3.0}, None) == 3.0
    assert monthly_fee_eur_from_specs(None, None) == 0.0


def test_monthly_fee_from_params() -> None:
    params = {
        "_import_tariff_spec": {"monthly_fee_eur": 2.99},
        "_export_tariff_spec": {},
    }
    assert monthly_fee_eur_from_params(params) == 2.99
    assert monthly_fee_eur_from_params(None) == 0.0


def test_monthly_fees_by_result_id() -> None:
    fees = monthly_fees_by_result_id(
        scenarios={
            "live": {
                "_import_tariff_spec": {"monthly_fee_eur": 4.79},
                "_export_tariff_spec": {},
            }
        },
        historical_params={
            "_import_tariff_spec": {"monthly_fee_eur": 4.79},
            "_export_tariff_spec": {},
        },
        historical_id="historical_reference",
        extra_ref_specs=[
            (
                "live_ref",
                {
                    "_import_tariff_spec": {"monthly_fee_eur": 3.0},
                    "_export_tariff_spec": {},
                },
                "Live Ref",
            )
        ],
    )
    assert fees["historical_reference"] == 4.79
    assert fees["live"] == 4.79
    assert fees["live_ref"] == 3.0


def test_build_summary_adds_full_month_fees() -> None:
    idx = pd.date_range("2025-01-01", periods=48, freq="h")
    df = pd.DataFrame({"sim_cost": [1.0] * 48}, index=idx)
    # Two calendar months (Jan + Feb) with 24h each if we use Jan 31–Feb 1
    idx2 = pd.date_range("2025-01-31", periods=48, freq="h")
    df2 = pd.DataFrame({"sim_cost": [2.0] * 48}, index=idx2)
    summary = _build_summary(
        {"s1": df2},
        {"s1": "S1"},
        monthly_fee_by_scenario={"s1": 10.0},
    )
    months = summary["monthly_eur"]
    assert "2025-01" in months
    assert "2025-02" in months
    assert months["2025-01"]["S1"] == round(24 * 2.0 + 10.0, 4)
    assert months["2025-02"]["S1"] == round(24 * 2.0 + 10.0, 4)
    assert summary["total_eur"]["s1"] == round(48 * 2.0 + 2 * 10.0, 4)
    # Hourly volumetric unchanged relative to fee add
    assert float(df2["sim_cost"].sum()) == 96.0


def test_build_summary_zero_fee_matches_volumetric() -> None:
    idx = pd.date_range("2025-03-01", periods=24, freq="h")
    df = pd.DataFrame({"sim_cost": [0.5] * 24}, index=idx)
    summary = _build_summary({"a": df}, {"a": "A"})
    assert summary["total_eur"]["a"] == 12.0
    assert summary["monthly_eur"]["2025-03"]["A"] == 12.0


def test_normalize_dach_copies_monthly_fee() -> None:
    spec: dict = {}
    _normalize_dach_fields({"monthly_fee_eur": 5.99, "land": "DE"}, spec)
    assert spec["monthly_fee_eur"] == 5.99


def test_tariff_preview_shows_monthly_fee() -> None:
    rows = dict(
        tariff_parameter_rows(
            {
                "type": "spot_hourly",
                "settlement_fee_cent_kwh": 1.2,
                "monthly_fee_eur": 3.0,
                "prices_include_vat": False,
            },
            kind="import",
        )
    )
    assert "Monatsgebühr (ca.)" in rows
    assert "3" in rows["Monatsgebühr (ca.)"]
