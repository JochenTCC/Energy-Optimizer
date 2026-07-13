"""Open-Meteo archive irradiance for cons_data / backtesting PV synthesis."""
from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd
import requests

import config
from data.eu_market_features import month_ranges

OPEN_METEO_ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
HOURLY_VAR = "global_tilted_irradiance"
REFERENCE_WM2 = 1000.0


def irradiance_wm2_to_pv_kw(irradiance_wm2: float | None, kwp: float) -> float:
    if irradiance_wm2 is None or kwp <= 0.0:
        return 0.0
    return round(max(0.0, float(irradiance_wm2) / REFERENCE_WM2 * kwp), 3)


def _resolve_installation_params() -> tuple[float, float, float, float, float, str]:
    lat = float(config.get("LATITUDE", cast=float))
    lon = float(config.get("LONGITUDE", cast=float))
    tilt = float(config.get("PV_TILT", cast=float))
    azimuth = float(config.get("PV_AZIMUTH", cast=float))
    kwp = float(config.get("PV_KWP", cast=float))
    timezone = str(config.get_planning_timezone())
    return lat, lon, tilt, azimuth, kwp, timezone


def _parse_hourly_times(times: list[str]) -> list[datetime]:
    parsed: list[datetime] = []
    for raw in times:
        text = str(raw).replace("Z", "+00:00")
        moment = datetime.fromisoformat(text)
        if moment.tzinfo is not None:
            moment = moment.replace(tzinfo=None)
        parsed.append(moment)
    return parsed


def _fetch_archive_chunk(
    *,
    lat: float,
    lon: float,
    tilt: float,
    azimuth: float,
    kwp: float,
    timezone: str,
    start: date,
    end: date,
) -> pd.Series:
    params: dict[str, Any] = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start.isoformat(),
        "end_date": (end - timedelta(days=1)).isoformat(),
        "hourly": HOURLY_VAR,
        "tilt": int(round(tilt)),
        "azimuth": int(round(azimuth)),
        "timezone": timezone,
    }
    response = requests.get(
        OPEN_METEO_ARCHIVE,
        params=params,
        timeout=config.get_global_timeout(),
    )
    response.raise_for_status()
    payload = response.json()
    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    irradiance = hourly.get(HOURLY_VAR) or []
    if not times or len(times) != len(irradiance):
        raise ValueError(
            f"Open-Meteo archive unvollständig ({start}..{end - timedelta(days=1)}): "
            f"{len(times)} Zeitstempel, {len(irradiance)} Irradianz-Werte."
        )
    index = pd.DatetimeIndex(_parse_hourly_times(times))
    values = [irradiance_wm2_to_pv_kw(value, kwp) for value in irradiance]
    return pd.Series(values, index=index, dtype=float)


def fetch_hourly_pv_kw_series(
    start: date,
    end: date,
    *,
    lat: float,
    lon: float,
    tilt: float,
    azimuth: float,
    kwp: float,
    timezone: str,
) -> pd.Series:
    """Stündliche PV-Leistung (kW) aus Open-Meteo global_tilted_irradiance."""
    if end < start:
        raise ValueError("Open-Meteo PV: end muss nicht vor start liegen.")
    if kwp <= 0.0:
        return pd.Series(dtype=float)

    chunks: list[pd.Series] = []
    for chunk_start, chunk_end in month_ranges(start, end + timedelta(days=1)):
        chunks.append(
            _fetch_archive_chunk(
                lat=lat,
                lon=lon,
                tilt=tilt,
                azimuth=azimuth,
                kwp=kwp,
                timezone=timezone,
                start=chunk_start,
                end=chunk_end,
            )
        )
    if not chunks:
        return pd.Series(dtype=float)
    series = pd.concat(chunks)
    return series[~series.index.duplicated(keep="last")].sort_index()


class OpenMeteoPvLookup:
    """Maps naive local hour slots to PV kW from Open-Meteo archive data."""

    def __init__(
        self,
        series: pd.Series,
        *,
        kwp: float,
        fallback: Callable[[int, int, float], float],
    ) -> None:
        self._series = series
        self._kwp = kwp
        self._fallback = fallback

    def kw_at(self, slot: datetime) -> float:
        if self._kwp <= 0.0:
            return 0.0
        key = slot.replace(minute=0, second=0, microsecond=0)
        if key in self._series.index:
            return round(float(self._series.loc[key]), 3)
        return self._fallback(key.hour, key.month, self._kwp)


def build_open_meteo_pv_lookup(
    start: date,
    end: date,
    *,
    fallback: Callable[[int, int, float], float],
) -> OpenMeteoPvLookup:
    lat, lon, tilt, azimuth, kwp, timezone = _resolve_installation_params()
    if kwp <= 0.0:
        print("[INFO] PV deaktiviert (PV_KWP=0) – cons_data pv_kw bleibt 0.")
        return OpenMeteoPvLookup(pd.Series(dtype=float), kwp=kwp, fallback=fallback)

    try:
        series = fetch_hourly_pv_kw_series(
            start,
            end,
            lat=lat,
            lon=lon,
            tilt=tilt,
            azimuth=azimuth,
            kwp=kwp,
            timezone=timezone,
        )
    except Exception as exc:
        print(f"[WARN] Open-Meteo Solar Archive fehlgeschlagen: {exc}. Nutze PV-Fallback-Kurve.")
        return OpenMeteoPvLookup(pd.Series(dtype=float), kwp=kwp, fallback=fallback)

    expected_hours = int((datetime.combine(end, datetime.min.time()) - datetime.combine(start, datetime.min.time())).total_seconds() // 3600) + 24
    covered = len(series)
    print(
        f"[OK] Open-Meteo Solar Archive: {covered} Stunden PV geladen "
        f"({start}..{end}, {kwp:.1f} kWp, {tilt:.0f}°/{azimuth:.0f}°)."
    )
    if covered < expected_hours:
        print(
            f"[WARN] Open-Meteo PV: nur {covered}/{expected_hours} Stunden im Zeitraum – "
            "fehlende Slots nutzen PV-Fallback."
        )
    return OpenMeteoPvLookup(series, kwp=kwp, fallback=fallback)
