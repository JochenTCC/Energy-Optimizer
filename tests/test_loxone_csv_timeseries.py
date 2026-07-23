"""Tests for Loxone CSV separator / decimal detection and hourly load."""
from __future__ import annotations

from pathlib import Path

import pytest

from data.loxone_csv_timeseries import (
    _detect_loxone_csv_sep,
    _to_numeric_power,
    load_loxone_value_hourly,
)


def test_detect_semicolon_german_decimal(tmp_path: Path) -> None:
    path = tmp_path / "semi.csv"
    path.write_text(
        "Datum;Zeit;Leistung [kW]\n01.07.2024;07:10:00;0,03\n",
        encoding="latin-1",
    )
    assert _detect_loxone_csv_sep(path, encoding="latin-1") == (";", ",")


def test_detect_comma_sep_english_decimal(tmp_path: Path) -> None:
    path = tmp_path / "en.csv"
    path.write_text(
        "Datum,Zeit,Leistung [kW]\n01.07.2024,07:10:00,0.03\n",
        encoding="latin-1",
    )
    assert _detect_loxone_csv_sep(path, encoding="latin-1") == (",", ".")


def test_detect_comma_sep_quoted_german_decimal(tmp_path: Path) -> None:
    path = tmp_path / "de_quoted.csv"
    # Leading integer rows must not hide later quoted decimals.
    lines = ["Datum,Zeit,Leistung Produktion [kW]"]
    lines.extend(f"01.07.2024,{h:02d}:00:00,0" for h in range(6))
    lines.append('01.07.2024,07:10:00,"0,03"')
    lines.append('01.07.2024,07:20:00,"0,011"')
    path.write_text("\n".join(lines) + "\n", encoding="latin-1")
    assert _detect_loxone_csv_sep(path, encoding="latin-1") == (",", ",")


def test_load_quoted_german_decimal_hourly(tmp_path: Path) -> None:
    from data.loxone_csv_timeseries import load_loxone_raw_value_series

    path = tmp_path / "ppv.csv"
    lines = ["Datum,Zeit,Leistung Produktion [kW]"]
    for minute in range(0, 60, 10):
        lines.append(f"01.07.2024,07:{minute:02d}:00,0")
    for minute, value in (
        (0, "0,100"),
        (10, "0,200"),
        (20, "0,300"),
        (30, "0,400"),
        (40, "0,500"),
        (50, "0,600"),
    ):
        lines.append(f'01.07.2024,08:{minute:02d}:00,"{value}"')
    path.write_text("\n".join(lines) + "\n", encoding="latin-1")
    raw = load_loxone_raw_value_series(str(path))
    assert raw.loc["2024-07-01 08:10:00"] == pytest.approx(0.2)
    assert raw.loc["2024-07-01 08:50:00"] == pytest.approx(0.6)
    series = load_loxone_value_hourly(str(path))
    # Must not collapse quoted decimals to NaN / stay at 0 via ZOH.
    assert series.loc["2024-07-01 08:00:00"] == pytest.approx(0.305882, rel=1e-4)


def test_to_numeric_power_recovers_german_decimal_strings() -> None:
    import pandas as pd

    values = pd.Series(["0", "0,03", "1,5", "2.25", "x"])
    parsed = _to_numeric_power(values)
    assert parsed.iloc[0] == pytest.approx(0.0)
    assert parsed.iloc[1] == pytest.approx(0.03)
    assert parsed.iloc[2] == pytest.approx(1.5)
    assert parsed.iloc[3] == pytest.approx(2.25)
    assert parsed.isna().iloc[4]
