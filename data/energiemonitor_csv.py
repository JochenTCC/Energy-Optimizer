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


def load_energiemonitor_hourly(
    filepath: str,
    *,
    encoding: str = "latin-1",
) -> dict[str, pd.Series]:
    """Load Energiemonitor CSV; return hourly series for Verbrauch (required) and Produktion (optional).

    Expected columns (among others):
    Datum;Zeit;Leistung Produktion [kW];Leistung Verbrauch [kW];…

    Ignores Energieversorger, Batterie, Ladestand, and energy counters.
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

    verbrauch_col = _find_column_index(df, _VERBRAUCH_ALIASES)
    if verbrauch_col is None:
        raise ValueError(
            f"Energiemonitor-CSV '{filepath}': Spalte "
            "'Leistung Verbrauch [kW]' fehlt."
        )

    result: dict[str, pd.Series] = {
        "verbrauch": _series_to_hourly(df, timestamps, verbrauch_col).astype(float),
    }
    if result["verbrauch"].empty:
        raise ValueError(
            f"Energiemonitor-CSV '{filepath}': Verbrauchsserie ist leer."
        )

    produktion_col = _find_column_index(df, _PRODUKTION_ALIASES)
    if produktion_col is not None:
        produktion = _series_to_hourly(df, timestamps, produktion_col).astype(float)
        if not produktion.empty:
            result["produktion"] = produktion

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
    return has_verbrauch and (has_produktion or "energiemonitor" in lower or ";" in first)
