"""Entladesperre: Ziel-SOC und Huawei-Mapping."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from optimizer import battery as bat
from optimizer.milp import _derive_control_from_milp, milp_optimizer

_BATTERY_PARAMS = {
    "min_soc": 10.0,
    "max_soc": 100.0,
    "max_power_kw": 5.0,
    "battery_capacity_kwh": 10.0,
    "efficiency": 0.95,
}


def _model_with_soc_percent(percent: float) -> MagicMock:
    model = MagicMock()
    capacity = _BATTERY_PARAMS["battery_capacity_kwh"]
    model.e_batt = [MagicMock(varValue=capacity * percent / 100.0)]
    return model


_ZERO_BATTERY_PARAMS = {
    "min_soc": 0.0,
    "max_soc": 100.0,
    "max_power_kw": 0.0,
    "battery_capacity_kwh": 0.0,
    "efficiency": 1.0,
}


def test_derive_control_without_battery_returns_automatik():
    mode, target_power, target_soc = _derive_control_from_milp(
        MagicMock(e_batt=[MagicMock(varValue=0.0)]),
        [{"expected_p_pv": 1.0, "expected_p_act": 2.0}],
        {"p_charge": 0.0, "p_discharge": 0.0, "p_grid_buy": 1.0},
        {"heat_pump": 0.5},
        0.5,
        50.0,
        _ZERO_BATTERY_PARAMS,
    )
    assert mode == bat.MODE_AUTOMATIK
    assert target_power == 0.0
    assert target_soc == 50.0


def test_milp_optimizer_without_battery_completes():
    matrix = [
        {
            "hour": 0,
            "date": "2025-01-01",
            "expected_p_pv": 0.0,
            "expected_p_act": 1.5,
            "k_act": 25.0,
            "k_push_act": 5.0,
        }
    ]
    mode, target_power, target_soc, _, _, _, _ = milp_optimizer(
        matrix,
        current_hour=0,
        current_soc=50.0,
        battery_params=_ZERO_BATTERY_PARAMS,
        k_push=5.0,
        verbose=False,
        consumers=[],
    )
    assert mode == bat.MODE_AUTOMATIK
    assert target_power == 0.0
    assert target_soc == pytest.approx(50.0)


def test_entladesperre_target_soc_matches_current_soc():
    current_soc = 41.0
    mode, target_power, target_soc = _derive_control_from_milp(
        _model_with_soc_percent(50.0),
        [{"expected_p_pv": 0.0, "expected_p_act": 2.0}],
        {"p_charge": 0.0, "p_discharge": 0.0, "p_grid_buy": 0.5},
        {},
        0.0,
        current_soc,
        _BATTERY_PARAMS,
    )
    assert mode == bat.MODE_ENTLADESPERRE
    assert target_power == 0.0
    assert target_soc == current_soc
