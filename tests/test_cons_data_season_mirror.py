"""Tests for cons_data season-mirror onto wall-clock months."""
from __future__ import annotations

import pandas as pd
import pytest

from data.cons_data_season_mirror import (
    season_mirror_cons_dataframe,
    wall_clock_simulation_window,
)


def _hourly_month(year: int, month: int, value: float) -> pd.DataFrame:
    start = pd.Timestamp(year, month, 1)
    end = start + pd.offsets.MonthEnd(0)
    idx = pd.date_range(start, end + pd.Timedelta(hours=23), freq="h")
    return pd.DataFrame(
        {"total_kw": value, "baseload_kw": value, "pv_kw": 0.0},
        index=idx,
    )


def test_wall_clock_simulation_window_last_complete_month():
    start, end = wall_clock_simulation_window(now=pd.Timestamp("2026-07-24"))
    assert end == pd.Timestamp("2026-06-30")
    assert start == pd.Timestamp("2025-07-01")


def test_season_mirror_maps_calendar_month_to_target_year():
    source = pd.concat(
        [
            _hourly_month(2024, 6, 1.0),
            _hourly_month(2024, 7, 2.0),
        ]
    )
    mirrored = season_mirror_cons_dataframe(
        source,
        target_start=pd.Timestamp("2026-06-01"),
        target_end=pd.Timestamp("2026-06-30"),
    )
    assert mirrored.index.min() == pd.Timestamp("2026-06-01")
    assert mirrored.index.max() == pd.Timestamp("2026-06-30 23:00:00")
    assert float(mirrored["total_kw"].iloc[0]) == 1.0
    assert len(mirrored) == 30 * 24


def test_season_mirror_prefers_most_recent_source_year():
    source = pd.concat(
        [
            _hourly_month(2023, 6, 3.0),
            _hourly_month(2024, 6, 4.0),
        ]
    )
    mirrored = season_mirror_cons_dataframe(
        source,
        target_start=pd.Timestamp("2026-06-01"),
        target_end=pd.Timestamp("2026-06-01"),
    )
    assert float(mirrored["total_kw"].iloc[0]) == 4.0


def test_season_mirror_missing_month_raises():
    source = _hourly_month(2024, 1, 1.0)
    with pytest.raises(ValueError, match="Kalendermonat 06"):
        season_mirror_cons_dataframe(
            source,
            target_start=pd.Timestamp("2026-06-01"),
            target_end=pd.Timestamp("2026-06-30"),
        )
