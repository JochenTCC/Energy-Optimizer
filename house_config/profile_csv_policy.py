"""Shared policy for consumer CSV use and SE Basislast path A vs B."""
from __future__ import annotations

from pathlib import Path

from house_config.consumption_csv import consumer_uses_profile_csv
from house_config.earnie_role import is_earnie_flex, is_earnie_manual
from runtime_store.persist_paths import resolve_config_prefixed_path


def _generic_consumers(house_profile: dict) -> list[dict]:
    return [
        consumer
        for consumer in house_profile.get("consumers", [])
        if consumer.get("type") == "generic"
    ]


def controllable_generics(house_profile: dict) -> list[dict]:
    """Gesteuert + Manuelles Gerät (SE-MILP-flex generics for B-gate)."""
    return [
        consumer
        for consumer in _generic_consumers(house_profile)
        if is_earnie_flex(consumer) or is_earnie_manual(consumer)
    ]


def accounted_csv_consumers(house_profile: dict) -> list[dict]:
    """Consumers whose CSV series are peeled for residual / fixed CSV overlay."""
    return [
        consumer
        for consumer in house_profile.get("consumers", [])
        if consumer_uses_profile_csv(consumer)
    ]


def _total_profile_csv_resolvable(house_profile: dict) -> bool:
    path = str(house_profile.get("total_profile_csv", "") or "").strip()
    if not path:
        return False
    try:
        return Path(resolve_config_prefixed_path(path)).is_file()
    except (OSError, TypeError, ValueError):
        return False


def se_uses_meter_residual_baseload(house_profile: dict) -> bool:
    """Path B: Gesamt-CSV present and every controllable generic has active CSV.

    Otherwise path A (flat baseload_kwh/8760 + role overlays), or monthly
    residual when ``baseload_distribution=monthly``.
    """
    if not _total_profile_csv_resolvable(house_profile):
        return False
    controllable = controllable_generics(house_profile)
    if not controllable:
        # No flex/manual: residual still useful when Gesamt-CSV exists.
        return True
    return all(consumer_uses_profile_csv(c) for c in controllable)


def se_uses_monthly_baseload(house_profile: dict) -> bool:
    """Path A monthly: Monats-Rest when not B and Gesamt-CSV is resolvable."""
    from house_config.baseload import (
        BASELOAD_DIST_MONTHLY,
        normalize_baseload_distribution,
    )

    if se_uses_meter_residual_baseload(house_profile):
        return False
    if normalize_baseload_distribution(
        house_profile.get("baseload_distribution")
    ) != BASELOAD_DIST_MONTHLY:
        return False
    return _total_profile_csv_resolvable(house_profile)
