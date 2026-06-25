"""Hilfen für flexible Verbraucher: Binär (Ein/Aus) vs. kW-Sollwert."""
from __future__ import annotations


def uses_power_setpoint(consumer: dict) -> bool:
    """True, wenn die Optimierung einen kW-Sollwert an Loxone sendet."""
    outputs = consumer.get("loxone_outputs") or {}
    return bool(str(outputs.get("power_setpoint_name", "")).strip())


def power_limits_kw(consumer: dict) -> tuple[float, float]:
    """
    (min_kw, max_kw) für MILP und Loxone-Clamping.
    Binärmodus: min=0, max=nominal_power_kw.
    """
    max_kw = float(consumer["nominal_power_kw"])
    if not uses_power_setpoint(consumer):
        return 0.0, max_kw

    min_kw = consumer.get("min_power_kw")
    if min_kw is None:
        raise ValueError(
            f"Verbraucher '{consumer.get('id', '?')}': min_power_kw fehlt "
            "(Pflicht bei loxone_outputs.power_setpoint_name)."
        )
    min_kw = float(min_kw)
    if min_kw < 0.0:
        raise ValueError(
            f"Verbraucher '{consumer.get('id', '?')}': min_power_kw muss >= 0 sein."
        )
    if min_kw > max_kw + 1e-9:
        raise ValueError(
            f"Verbraucher '{consumer.get('id', '?')}': min_power_kw ({min_kw}) "
            f"darf nicht größer als nominal_power_kw ({max_kw}) sein."
        )
    return min_kw, max_kw


def clamp_setpoint_kw(consumer: dict, power_kw: float) -> float:
    """Soll-Leistung für Loxone: 0 oder im Bereich [min, max]."""
    min_kw, max_kw = power_limits_kw(consumer)
    power_kw = max(0.0, float(power_kw or 0.0))
    if power_kw <= 1e-3:
        return 0.0
    return round(max(min_kw, min(max_kw, power_kw)), 3)
