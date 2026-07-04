"""Day-Ahead-Preise für das rollierende 24h-Fenster inkl. Spiegel-Extrapolation."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pandas as pd

import config

PRICE_SOURCE_DAY_AHEAD = "day_ahead"
PRICE_SOURCE_MIRRORED = "mirrored"
MAX_MIRROR_LOOKBACK_DAYS = 7


def normalize_price_slot(dt: datetime) -> datetime:
    """Stunden-Slot in Planungszeitzone (config: runtime_settings.timezone_name)."""
    from zoneinfo import ZoneInfo

    tz = ZoneInfo(config.get_planning_timezone())
    if dt.tzinfo is None:
        aligned = dt.replace(tzinfo=tz)
    else:
        aligned = dt.astimezone(tz)
    return aligned.replace(minute=0, second=0, microsecond=0)


def epex_to_brutto_cent(epex_price_cent: float) -> float:
    """EPEX Cent/kWh → Endkunden-Bruttopreis laut config."""
    fix_aufschlag = config.get("FIX_AUFSCHLAG_CENT", cast=float)
    netzverlust = config.get("NETZVERLUST_FAKTOR", cast=float)
    mwst_faktor = config.get("MWST_AUSTRIA_FAKTOR", cast=float)
    brutto = (float(epex_price_cent) * netzverlust + fix_aufschlag) * mwst_faktor
    return round(brutto, 4)


def index_market_data_by_slot(market_data: list[dict[str, Any]]) -> dict[datetime, dict[str, Any]]:
    """Indiziert Roh-Marktdaten nach Stunden-Slot (Mittelwert bei Duplikaten)."""
    buckets: dict[datetime, list[float]] = {}
    for item in market_data:
        ts = item.get("timestamp")
        if ts is None:
            continue
        slot = normalize_price_slot(ts)
        try:
            price = float(item["price_buy"])
        except (KeyError, TypeError, ValueError):
            continue
        buckets.setdefault(slot, []).append(price)

    indexed: dict[datetime, dict[str, Any]] = {}
    for slot, prices in buckets.items():
        epex = sum(prices) / len(prices)
        indexed[slot] = {
            "timestamp": slot,
            "hour": slot.hour,
            "price_buy": round(epex, 4),
        }
    return indexed


def find_mirror_slot(
    slot: datetime,
    by_slot: dict[datetime, dict[str, Any]],
    *,
    max_lookback_days: int,
) -> datetime | None:
    """Sucht Spiegelquelle: gleiche Uhrzeit an vorherigen Tagen."""
    if max_lookback_days < 1:
        raise ValueError("max_lookback_days muss mindestens 1 sein.")
    for days_back in range(1, max_lookback_days + 1):
        candidate = slot - timedelta(days=days_back)
        if candidate in by_slot:
            return candidate
    return None


def _append_mirrored_slot(
    resolved: list[dict[str, Any]],
    slot: datetime,
    mirror_slot: datetime,
    by_slot: dict[datetime, dict[str, Any]],
) -> None:
    epex = float(by_slot[mirror_slot]["price_buy"])
    resolved.append(
        {
            "slot_datetime": slot,
            "hour": slot.hour,
            "price_buy": epex,
            "price_source": PRICE_SOURCE_MIRRORED,
            "mirrored_from": mirror_slot,
            "k_act": epex_to_brutto_cent(epex),
        }
    )


def resolve_market_slots(
    market_data: list[dict[str, Any]],
    target_hours: list[datetime],
) -> list[dict[str, Any]]:
    """
    Liefert Preis-Slots für target_hours (beliebige Länge >= 1).

    Fehlende Day-Ahead-Stunden werden per Spiegelung befüllt:
    gleiche Uhrzeit an vorherigen Tagen (bis MAX_MIRROR_LOOKBACK_DAYS).
    """
    if not target_hours:
        raise ValueError("resolve_market_slots erfordert mindestens eine Zielstunde.")

    by_slot = index_market_data_by_slot(market_data)
    resolved: list[dict[str, Any]] = []

    for target_dt in target_hours:
        slot = normalize_price_slot(target_dt)
        if slot in by_slot:
            epex = float(by_slot[slot]["price_buy"])
            resolved.append(
                {
                    "slot_datetime": slot,
                    "hour": slot.hour,
                    "price_buy": epex,
                    "price_source": PRICE_SOURCE_DAY_AHEAD,
                    "k_act": epex_to_brutto_cent(epex),
                }
            )
            continue

        mirror_slot = find_mirror_slot(
            slot,
            by_slot,
            max_lookback_days=MAX_MIRROR_LOOKBACK_DAYS,
        )
        if mirror_slot is None:
            raise ValueError(
                f"Kein Day-Ahead-Preis für {slot:%Y-%m-%d %H:%M} und keine Spiegelquelle "
                f"innerhalb von {MAX_MIRROR_LOOKBACK_DAYS} Tagen verfügbar. "
                "aWATTar-Zeitraum erweitern oder später erneut versuchen."
            )

        _append_mirrored_slot(resolved, slot, mirror_slot, by_slot)

    return resolved


def resolve_24h_market_slots(
    market_data: list[dict[str, Any]],
    target_hours: list[datetime],
) -> list[dict[str, Any]]:
    """Kompatibilitäts-Wrapper; bevorzugt resolve_market_slots direkt."""
    return resolve_market_slots(market_data, target_hours)


def mirrored_price_share(resolved_slots: list[dict[str, Any]]) -> float:
    """Anteil gespiegelter Preise (0.0–1.0)."""
    if not resolved_slots:
        return 0.0
    mirrored = sum(
        1 for slot in resolved_slots if slot.get("price_source") == PRICE_SOURCE_MIRRORED
    )
    return mirrored / len(resolved_slots)


def awattar_fetch_window(planning_end: datetime | None = None) -> tuple[datetime, datetime]:
    """
    Start und Ende für den aWATTar-Abruf.

    Start: Mitternacht heute minus MAX_MIRROR_LOOKBACK_DAYS (Spiegelquellen).
    planning_end: optionales Fensterende (z. B. SA₂); sonst jetzt + 24 h.
    Zeitzone von planning_end wird übernommen (typisch Europe/Vienna).
    """
    tz = planning_end.tzinfo if planning_end is not None and planning_end.tzinfo else None
    if tz is not None:
        now = datetime.now(tz).replace(minute=0, second=0, microsecond=0)
    else:
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(
        days=MAX_MIRROR_LOOKBACK_DAYS
    )
    if planning_end is not None:
        end = normalize_price_slot(planning_end)
        if end.tzinfo is None and tz is not None:
            end = end.replace(tzinfo=tz)
        if end < now:
            raise ValueError(
                f"planning_end ({planning_end}) liegt vor dem aktuellen Stunden-Slot ({now})."
            )
        return start, end
    end = now + timedelta(hours=24)
    return start, end


def epex_prices_for_slots(
    prices_df: pd.DataFrame,
    slot_datetimes: list[datetime],
) -> list[float]:
    """EPEX Cent/kWh je Stunden-Slot aus einem Preis-DataFrame."""
    hourly = prices_df["price_cent_kwh"].resample("h").mean()
    idx = pd.DatetimeIndex(slot_datetimes)
    series = hourly.reindex(idx).ffill().bfill().fillna(0.0)
    return [float(p) for p in series.tolist()]
