"""Einspeisevergütung: fix (k_push_cent) oder stündlich dynamisch (EPEX / Awattar Sunny Spot)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

FEED_IN_MODE_FIXED = "fixed"
FEED_IN_MODE_DYNAMIC_EPEX = "dynamic_epex"
VALID_FEED_IN_MODES = frozenset({FEED_IN_MODE_FIXED, FEED_IN_MODE_DYNAMIC_EPEX})


@dataclass(frozen=True)
class FeedInSettings:
    mode: str
    k_push_cent: float
    fee_factor: float
    fix_cent: float
    monthly_fixed_tariffs: tuple[tuple[int, int, float], ...] | None = None


def validate_feed_in_mode(mode: str) -> str:
    normalized = str(mode).strip().lower()
    if normalized not in VALID_FEED_IN_MODES:
        raise ValueError(
            f"Unbekannter feed_in_mode '{mode}'. "
            f"Erlaubt: {', '.join(sorted(VALID_FEED_IN_MODES))}."
        )
    return normalized


def validate_fixed_monthly_feed_in_rates(raw: list) -> tuple[tuple[int, int, float], ...]:
    """Validiert fixed_monthly_feed_in_rates aus backtesting_scenarios.json."""
    if not isinstance(raw, list) or not raw:
        raise ValueError(
            "fixed_monthly_feed_in_rates muss ein nicht-leeres Array sein."
        )
    seen: set[tuple[int, int]] = set()
    entries: list[tuple[int, int, float]] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(
                f"fixed_monthly_feed_in_rates[{index}] muss ein Objekt sein."
            )
        for key in ("year", "month", "tariff_cent_kwh"):
            if key not in item:
                raise ValueError(
                    f"fixed_monthly_feed_in_rates[{index}]: '{key}' fehlt."
                )
        year = int(item["year"])
        month = int(item["month"])
        tariff = float(item["tariff_cent_kwh"])
        if month < 1 or month > 12:
            raise ValueError(
                f"fixed_monthly_feed_in_rates[{index}]: month muss 1–12 sein."
            )
        if tariff <= 0.0:
            raise ValueError(
                f"fixed_monthly_feed_in_rates[{index}]: tariff_cent_kwh muss > 0 sein."
            )
        key = (year, month)
        if key in seen:
            raise ValueError(
                f"fixed_monthly_feed_in_rates: doppelter Eintrag für {year}-{month:02d}."
            )
        seen.add(key)
        entries.append((year, month, tariff))
    return tuple(entries)


def monthly_fixed_tariff_lookup(
    tariffs: tuple[tuple[int, int, float], ...],
) -> dict[tuple[int, int], float]:
    return {(year, month): tariff for year, month, tariff in tariffs}


def _fixed_tariff_for_slot(
    slot_datetime: datetime | None,
    settings: FeedInSettings,
) -> float:
    tariffs = settings.monthly_fixed_tariffs
    if tariffs is None:
        return float(settings.k_push_cent)
    if slot_datetime is None:
        raise ValueError(
            "feed_in_mode 'fixed' mit fixed_monthly_feed_in_rates erfordert "
            "slot_datetime pro Matrix-Zeile bzw. Stunde."
        )
    lookup = monthly_fixed_tariff_lookup(tariffs)
    key = (slot_datetime.year, slot_datetime.month)
    if key not in lookup:
        raise ValueError(
            f"Kein fixer Einspeisetarif für {key[0]}-{key[1]:02d} in "
            "fixed_monthly_feed_in_rates (backtesting_scenarios.json)."
        )
    return lookup[key]


def epex_to_feed_in_cent(
    epex_cent: float,
    fee_factor: float,
    fix_cent: float,
) -> float:
    """
    EPEX Cent/kWh → Einspeisevergütung (Awattar SUNNY Spot 60 min, netto):
    EPEX − fee_factor × |EPEX| + fix_cent (z. B. regionale Netz-/Abgaben-Offset).
    """
    epex = float(epex_cent)
    fee = float(fee_factor)
    fix = float(fix_cent)
    if fee < 0:
        raise ValueError("feed_in_fee_factor muss >= 0 sein.")
    return round(epex - fee * abs(epex) + fix, 4)


def resolve_k_push_act(
    epex_cent: float | None,
    settings: FeedInSettings,
    *,
    slot_datetime: datetime | None = None,
) -> float:
    mode = validate_feed_in_mode(settings.mode)
    if mode == FEED_IN_MODE_FIXED:
        return _fixed_tariff_for_slot(slot_datetime, settings)
    if epex_cent is None:
        raise ValueError(
            "feed_in_mode 'dynamic_epex' erfordert price_buy (EPEX Cent/kWh) pro Matrix-Zeile."
        )
    return epex_to_feed_in_cent(epex_cent, settings.fee_factor, settings.fix_cent)


def feed_in_settings_from_dict(
    runtime: dict[str, Any],
    awattar: dict[str, Any],
    *,
    monthly_fixed_tariffs: tuple[tuple[int, int, float], ...] | None = None,
) -> FeedInSettings:
    if "k_push_cent" not in runtime:
        raise KeyError("feed_in_settings erfordert k_push_cent in runtime_settings bzw. Szenario.")
    mode = validate_feed_in_mode(runtime.get("feed_in_mode", FEED_IN_MODE_FIXED))
    k_push = float(runtime["k_push_cent"])
    if mode == FEED_IN_MODE_DYNAMIC_EPEX:
        if "feed_in_fee_factor" not in awattar:
            raise ValueError(
                "feed_in_mode 'dynamic_epex' erfordert awattar.feed_in_fee_factor in config.json."
            )
        fee_factor = float(awattar["feed_in_fee_factor"])
        fix_cent = float(awattar.get("feed_in_fix_cent", 0.0))
    else:
        fee_factor = float(awattar.get("feed_in_fee_factor", 0.0))
        fix_cent = float(awattar.get("feed_in_fix_cent", 0.0))
    return FeedInSettings(
        mode=mode,
        k_push_cent=k_push,
        fee_factor=fee_factor,
        fix_cent=fix_cent,
        monthly_fixed_tariffs=monthly_fixed_tariffs,
    )


def enrich_matrix_feed_in_prices(matrix: list[dict[str, Any]], settings: FeedInSettings) -> None:
    """Setzt k_push_act je Matrix-Zeile (in-place)."""
    for row in matrix:
        row["k_push_act"] = resolve_k_push_act(
            row.get("price_buy"),
            settings,
            slot_datetime=row.get("slot_datetime"),
        )


def k_push_act_for_matrix_row(row: dict[str, Any], fallback_k_push: float) -> float:
    """Liest k_push_act aus der Matrix-Zeile oder nutzt den Fallback."""
    value = row.get("k_push_act")
    if value is not None:
        return float(value)
    return float(fallback_k_push)
