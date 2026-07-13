# tests/test_open_meteo_solar_archive.py
"""Tests für Open-Meteo Solar Archive PV in cons_data-Synthese."""
from __future__ import annotations

from datetime import date, datetime

import pandas as pd
import pytest

from data import open_meteo_solar_archive as archive


def _fallback(hour: int, month: int, kwp: float) -> float:
    return round(kwp * 0.01 * hour, 3)


def test_irradiance_wm2_to_pv_kw_scales_with_kwp():
    assert archive.irradiance_wm2_to_pv_kw(500.0, 10.0) == pytest.approx(5.0)
    assert archive.irradiance_wm2_to_pv_kw(None, 10.0) == 0.0
    assert archive.irradiance_wm2_to_pv_kw(500.0, 0.0) == 0.0


def test_open_meteo_pv_lookup_uses_series_and_fallback():
    series = pd.Series(
        {datetime(2024, 7, 13, 13, 0): 6.5},
        dtype=float,
    )
    lookup = archive.OpenMeteoPvLookup(series, kwp=10.0, fallback=_fallback)
    assert lookup.kw_at(datetime(2024, 7, 13, 13, 0)) == pytest.approx(6.5)
    assert lookup.kw_at(datetime(2024, 7, 14, 13, 0)) == pytest.approx(1.3)


def test_fetch_hourly_pv_kw_series_parses_archive_payload(monkeypatch):
    def _fake_get(url, params, timeout):
        assert url == archive.OPEN_METEO_ARCHIVE
        assert params["hourly"] == "global_tilted_irradiance"
        class Resp:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "hourly": {
                        "time": ["2024-07-13T09:00", "2024-07-13T13:00"],
                        "global_tilted_irradiance": [333.8, 666.8],
                    }
                }

        return Resp()

    monkeypatch.setattr(archive.requests, "get", _fake_get)
    series = archive.fetch_hourly_pv_kw_series(
        date(2024, 7, 13),
        date(2024, 7, 13),
        lat=48.0,
        lon=10.0,
        tilt=20.0,
        azimuth=-10.0,
        kwp=10.0,
        timezone="Europe/Berlin",
    )
    assert series[datetime(2024, 7, 13, 9, 0)] == pytest.approx(3.338)
    assert series[datetime(2024, 7, 13, 13, 0)] == pytest.approx(6.668)


def test_build_open_meteo_pv_lookup_falls_back_on_api_error(monkeypatch):
    monkeypatch.setattr(
        archive,
        "_resolve_installation_params",
        lambda: (48.0, 10.0, 20.0, -10.0, 10.0, "Europe/Berlin"),
    )
    monkeypatch.setattr(
        archive,
        "fetch_hourly_pv_kw_series",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("offline")),
    )
    lookup = archive.build_open_meteo_pv_lookup(
        date(2024, 7, 13),
        date(2024, 7, 13),
        fallback=_fallback,
    )
    assert lookup.kw_at(datetime(2024, 7, 13, 10, 0)) == pytest.approx(1.0)
