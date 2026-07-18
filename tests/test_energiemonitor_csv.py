"""Tests for Loxone Energiemonitor multi-column CSV import."""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from data.energiemonitor_csv import load_energiemonitor_hourly, looks_like_energiemonitor
from house_config.consumption_csv import (
    MIN_HOURS_FULL_YEAR,
    import_energiemonitor_to_canonical,
    load_hourly_profile_csv,
)


_HEADER = (
    "Datum;Zeit;Leistung Produktion [kW];Leistung Verbrauch [kW];"
    "Leistung Energieversorger [kW];Leistung Batterie;Ladestand Batterie [%%];"
    "Zähler Produktion [kWh];Zähler Verbrauch [kWh]"
)


def _write_energiemonitor(
    path: Path,
    *,
    hours: int,
    step_minutes: int = 60,
    verbrauch: float = 0.5,
    produktion: float = 1.2,
    include_produktion: bool = True,
) -> None:
    start = datetime(2023, 1, 1)
    if include_produktion:
        lines = [_HEADER]
    else:
        lines = [
            "Datum;Zeit;Leistung Verbrauch [kW];Leistung Energieversorger [kW];"
            "Leistung Batterie;Ladestand Batterie [%%]"
        ]
    samples = hours * (60 // step_minutes)
    for i in range(samples):
        ts = start + timedelta(minutes=step_minutes * i)
        date_s = ts.strftime("%d.%m.%Y")
        time_s = ts.strftime("%H:%M:%S")
        v = f"{verbrauch:.3f}".replace(".", ",")
        if include_produktion:
            p = f"{produktion:.3f}".replace(".", ",")
            lines.append(f"{date_s};{time_s};{p};{v};0,000;0,000;50,000;0,000;0,000")
        else:
            lines.append(f"{date_s};{time_s};{v};0,000;0,000;50,000")
    path.write_text("\n".join(lines) + "\n", encoding="latin-1")


def test_looks_like_energiemonitor(tmp_path: Path) -> None:
    path = tmp_path / "em.csv"
    _write_energiemonitor(path, hours=24)
    assert looks_like_energiemonitor(path)


def test_load_energiemonitor_hourly_both_series(tmp_path: Path) -> None:
    path = tmp_path / "em.csv"
    _write_energiemonitor(path, hours=48, step_minutes=10)
    series = load_energiemonitor_hourly(str(path))
    assert "verbrauch" in series
    assert "produktion" in series
    assert len(series["verbrauch"]) >= 48
    assert series["verbrauch"].iloc[0] == pytest.approx(0.5)
    assert series["produktion"].iloc[0] == pytest.approx(1.2)


def test_load_energiemonitor_without_produktion(tmp_path: Path) -> None:
    path = tmp_path / "em_no_pv.csv"
    _write_energiemonitor(path, hours=24, include_produktion=False)
    series = load_energiemonitor_hourly(str(path))
    assert "verbrauch" in series
    assert "produktion" not in series


def test_load_energiemonitor_missing_verbrauch_raises(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text(
        "Datum;Zeit;Leistung Produktion [kW]\n01.01.2023;00:00:00;1,000\n",
        encoding="latin-1",
    )
    with pytest.raises(ValueError, match="Verbrauch"):
        load_energiemonitor_hourly(str(path))


def test_import_energiemonitor_to_canonical(tmp_path: Path) -> None:
    source = tmp_path / "em.csv"
    _write_energiemonitor(source, hours=MIN_HOURS_FULL_YEAR)
    verbrauch_dest = tmp_path / "verbrauch.csv"
    produktion_dest = tmp_path / "pv.csv"
    result = import_energiemonitor_to_canonical(
        str(source),
        verbrauch_dest=str(verbrauch_dest),
        produktion_dest=str(produktion_dest),
    )
    assert result["total_profile_csv"] == str(verbrauch_dest)
    assert result["pv_profile_csv"] == str(produktion_dest)
    rows_v = load_hourly_profile_csv(str(verbrauch_dest))
    rows_p = load_hourly_profile_csv(str(produktion_dest))
    assert len(rows_v) >= MIN_HOURS_FULL_YEAR
    assert len(rows_p) >= MIN_HOURS_FULL_YEAR
    assert rows_v[0][1] == pytest.approx(0.5)
    assert rows_p[0][1] == pytest.approx(1.2)


def test_import_energiemonitor_too_short_raises(tmp_path: Path) -> None:
    source = tmp_path / "em_short.csv"
    _write_energiemonitor(source, hours=100)
    with pytest.raises(ValueError, match="Stunden"):
        import_energiemonitor_to_canonical(
            str(source),
            verbrauch_dest=str(tmp_path / "v.csv"),
            produktion_dest=str(tmp_path / "p.csv"),
        )
