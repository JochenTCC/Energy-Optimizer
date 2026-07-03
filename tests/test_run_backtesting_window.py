"""Unit-Tests für resolve_backtesting_window und SoC-Kette über zwei Fenster."""
from __future__ import annotations

import os

import pandas as pd
import pytest

from scripts.run_backtesting import (
    BACKTESTING_YEAR,
    _parse_month,
    resolve_backtesting_window,
)
from simulation.engine import list_simulation_anchors, run_simulation
from tests.fixtures.backtesting_fixtures import (
    SOC_CHAIN_END_DAY,
    SOC_CHAIN_START_DAY,
    activate_backtesting_fixtures,
    build_synthetic_prices_df,
    fixture_scenario_params,
    load_fixture_cache,
)

os.environ.setdefault("ENERGY_OPTIMIZER_OFFLINE", "1")


class TestParseMonth:
    def test_parses_valid_month(self):
        ts = _parse_month("6")
        assert ts == pd.Timestamp(BACKTESTING_YEAR, 6, 1)

    def test_rejects_invalid_month(self):
        import argparse

        with pytest.raises(argparse.ArgumentTypeError, match="zwischen 1 und 12"):
            _parse_month("13")


class TestResolveBacktestingWindow:
    @pytest.fixture(autouse=True)
    def _fixtures(self, monkeypatch):
        with activate_backtesting_fixtures(monkeypatch):
            yield

    def test_month_range_within_fixture_bounds(self):
        start = _parse_month("6")
        end = _parse_month("6")
        # Fixture-Daten reichen bis 2026-06-25; Juni 2025 liegt dazwischen ohne Logs,
        # aber die Datumsauflösung selbst muss ein gültiges Intervall liefern.
        resolved_start, resolved_end = resolve_backtesting_window(
            start,
            end,
            "last_12_months",
            "tests/fixtures/backtesting/cons_data_hourly.csv",
            "unused.csv",
        )
        assert resolved_start.month == 6
        assert resolved_end.month == 6
        assert resolved_start.year == BACKTESTING_YEAR
        assert resolved_start <= resolved_end

    def test_june_2026_clamped_to_fixture_data(self, monkeypatch):
        """Juni 2026: Enddatum wird auf letzten Log-Tag (2026-06-25) begrenzt."""
        monkeypatch.setattr(
            "scripts.run_backtesting.pd.Timestamp.now",
            lambda: pd.Timestamp("2026-07-03"),
        )
        start = pd.Timestamp(2026, 6, 1)
        end = pd.Timestamp(2026, 6, 1)
        resolved_start, resolved_end = resolve_backtesting_window(
            start,
            end,
            "last_12_months",
            "tests/fixtures/backtesting/cons_data_hourly.csv",
            "unused.csv",
        )
        assert resolved_start == pd.Timestamp("2026-06-01")
        assert resolved_end == pd.Timestamp("2026-06-25")

    def test_requires_both_months(self):
        start = _parse_month("6")
        with pytest.raises(SystemExit, match="gemeinsam"):
            resolve_backtesting_window(
                start,
                None,
                "last_12_months",
                "tests/fixtures/backtesting/cons_data_hourly.csv",
                "unused.csv",
            )

    def test_rejects_start_after_end_month(self):
        start = _parse_month("8")
        end = _parse_month("6")
        with pytest.raises(SystemExit, match="darf nicht nach"):
            resolve_backtesting_window(
                start,
                end,
                "last_12_months",
                "tests/fixtures/backtesting/cons_data_hourly.csv",
                "unused.csv",
            )


class TestSocChainTwoWindows:
    @pytest.fixture(autouse=True)
    def _fixtures(self, monkeypatch):
        with activate_backtesting_fixtures(monkeypatch):
            yield

    def test_two_day_run_has_continuous_soc(self):
        cache = load_fixture_cache()
        scenario = fixture_scenario_params()
        prices = build_synthetic_prices_df(
            pd.Timestamp(SOC_CHAIN_START_DAY),
            pd.Timestamp(SOC_CHAIN_END_DAY),
        )
        start = pd.Timestamp(SOC_CHAIN_START_DAY)
        end = pd.Timestamp(SOC_CHAIN_END_DAY)
        anchors = list_simulation_anchors(start, end, cache)
        assert len(anchors) == 2, f"Erwartet 2 Fenster, erhalten: {anchors}"

        df, plausibility, _ = run_simulation(
            start,
            end,
            scenario,
            prices,
            cache=cache,
            initial_soc=50.0,
        )
        assert len(df) == 48
        assert plausibility.failed == []
        assert df["sim_soc"].notna().all()

        boundary_idx = 23
        assert df["sim_soc"].iloc[boundary_idx + 1] == pytest.approx(
            df["sim_soc"].iloc[boundary_idx],
            abs=0.05,
        ), "SoC muss am Fensterübergang durchgängig sein (kein Reset auf initial_soc)"

        assert df["sim_soc"].iloc[0] == pytest.approx(50.0, abs=15.0)
        assert not all(df["sim_soc"] == pytest.approx(50.0, abs=0.01)), (
            "SoC sollte sich über zwei Fenster hinweg verändern"
        )
