"""Scenario Explorer monthly standing charges (post-aggregation only)."""
from __future__ import annotations


def _fee_from_spec(spec: dict | None) -> float:
    if not isinstance(spec, dict):
        return 0.0
    raw = spec.get("monthly_fee_eur")
    if raw is None:
        return 0.0
    return float(raw)


def _require_supplier_id(spec: dict) -> str:
    sid = str(spec.get("supplier_id") or "").strip()
    if not sid:
        tariff_id = str(spec.get("id") or "?").strip() or "?"
        raise ValueError(
            f"Tarif '{tariff_id}': supplier_id fehlt für Monatsgebühr-Aggregation."
        )
    return sid


def monthly_fee_eur_from_specs(
    import_spec: dict | None,
    export_spec: dict | None,
) -> float:
    """One fee per supplier_id (max within group); sum across suppliers."""
    by_supplier: dict[str, float] = {}
    for spec in (import_spec, export_spec):
        if not isinstance(spec, dict) or not spec:
            continue
        fee = _fee_from_spec(spec)
        sid = _require_supplier_id(spec)
        prev = by_supplier.get(sid)
        by_supplier[sid] = fee if prev is None else max(prev, fee)
    return float(sum(by_supplier.values()))


def monthly_fee_eur_from_params(params: dict | None) -> float:
    """Fee from resolved scenario params (`_import_tariff_spec` / `_export_tariff_spec`)."""
    if not isinstance(params, dict):
        return 0.0
    return monthly_fee_eur_from_specs(
        params.get("_import_tariff_spec"),
        params.get("_export_tariff_spec"),
    )


def monthly_fees_by_result_id(
    *,
    scenarios: dict[str, dict],
    historical_params: dict | None,
    historical_id: str,
    extra_ref_specs: list[tuple[str, dict | None, str]] | None = None,
) -> dict[str, float]:
    """Map SE result IDs → EUR/month fee (0 if unknown)."""
    fees: dict[str, float] = {
        historical_id: monthly_fee_eur_from_params(historical_params),
    }
    for scenario_id, params in scenarios.items():
        fees[scenario_id] = monthly_fee_eur_from_params(params)
    for ref_id, params, _label in extra_ref_specs or ():
        fees[ref_id] = monthly_fee_eur_from_params(params)
    return fees
