"""Loxone Energiemonitor multi-column statistics CSV → hourly power series."""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from data.loxone_csv_timeseries import (
    _parse_combined_timestamps,
    _parse_split_timestamps,
    _read_loxone_frame,
    _resolve_timestamp_width,
    _series_to_hourly,
)

# Headers after lowercasing and collapsing whitespace / bracket units.
_VERBRAUCH_ALIASES = frozenset(
    {
        "leistung verbrauch",
        "leistungverbrauch",
    }
)
_PRODUKTION_ALIASES = frozenset(
    {
        "leistung produktion",
        "leistungproduktion",
    }
)
_BATTERY_ALIASES = frozenset(
    {
        "leistung batterie",
        "leistungbatterie",
    }
)
_GRID_ALIASES = frozenset(
    {
        "leistung energieversorger",
        "leistungenergieversorger",
    }
)


def _normalize_header(name: object) -> str:
    text = str(name).strip().lower()
    text = re.sub(r"\[[^\]]*\]", "", text)
    text = text.replace("%", "")
    text = re.sub(r"[\s_]+", " ", text).strip()
    return text


def _find_column_index(df: pd.DataFrame, aliases: frozenset[str]) -> int | None:
    for index, name in enumerate(df.columns):
        if _normalize_header(name) in aliases:
            return index
    return None


def _optional_hourly_column(
    df: pd.DataFrame,
    timestamps: pd.Series,
    aliases: frozenset[str],
) -> pd.Series | None:
    col = _find_column_index(df, aliases)
    if col is None:
        return None
    series = _series_to_hourly(df, timestamps, col).astype(float)
    return series if not series.empty else None


def load_energiemonitor_hourly(
    filepath: str,
    *,
    encoding: str = "latin-1",
    require_verbrauch: bool = True,
) -> dict[str, pd.Series]:
    """Load Energiemonitor CSV; return hourly series by role key.

    Keys: ``verbrauch`` (required unless ``require_verbrauch=False``),
    optional ``produktion``, ``batterie``, ``energieversorger``.

    Expected columns (among others):
    Datum;Zeit;Leistung Produktion [kW];Leistung Verbrauch [kW];…
    """
    path = Path(filepath)
    if not path.is_file():
        raise FileNotFoundError(f"Energiemonitor-CSV nicht gefunden: {filepath}")

    df = _read_loxone_frame(path, encoding=encoding)
    ts_width = _resolve_timestamp_width(df, filepath)
    if ts_width == 2:
        timestamps = _parse_split_timestamps(df)
    else:
        timestamps = _parse_combined_timestamps(df)

    result: dict[str, pd.Series] = {}
    verbrauch = _optional_hourly_column(df, timestamps, _VERBRAUCH_ALIASES)
    if verbrauch is not None:
        result["verbrauch"] = verbrauch
    elif require_verbrauch:
        raise ValueError(
            f"Energiemonitor-CSV '{filepath}': Spalte "
            "'Leistung Verbrauch [kW]' fehlt."
        )

    produktion = _optional_hourly_column(df, timestamps, _PRODUKTION_ALIASES)
    if produktion is not None:
        result["produktion"] = produktion
    batterie = _optional_hourly_column(df, timestamps, _BATTERY_ALIASES)
    if batterie is not None:
        result["batterie"] = batterie
    grid = _optional_hourly_column(df, timestamps, _GRID_ALIASES)
    if grid is not None:
        result["energieversorger"] = grid

    if not result:
        raise ValueError(
            f"Energiemonitor-CSV '{filepath}': keine Leistungsspalten gefunden."
        )
    return result


def looks_like_energiemonitor(path: Path | str) -> bool:
    """True if header suggests multi-column Energiemonitor statistics."""
    file_path = Path(path)
    try:
        text = file_path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return False
    first = text.splitlines()[0] if text else ""
    lower = first.lower()
    has_verbrauch = "verbrauch" in lower and "leistung" in lower
    has_produktion = "produktion" in lower and "leistung" in lower
    has_balance = (
        "batterie" in lower
        and "energieversorger" in lower
        and "leistung" in lower
    )
    return (has_verbrauch and (has_produktion or "energiemonitor" in lower or ";" in first)) or (
        has_balance and has_produktion
    )
