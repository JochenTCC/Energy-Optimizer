"""Tests für generic-Flex min_on-Fortsetzung über rollierende MILP-Schritte."""
from __future__ import annotations

from datetime import datetime

import pulp

from optimizer.generic_flex_run import (
    continue_on_from_state,
    update_generic_flex_run_state,
)
from optimizer.milp import milp_optimizer
from optimizer.milp_consumers import add_generic_block_start_guard, add_min_on_time_constraints
from optimizer.simulation import simulate_horizon


def _matrix_row(hour: int, day: datetime, *, pv: float = 0.0, load: float = 1.0) -> dict:
    slot = day.replace(hour=hour, minute=0, second=0, microsecond=0)
    return {
        "hour": hour,
        "date": day.date(),
        "slot_datetime": slot,
        "expected_p_pv": pv,
        "expected_p_act": load,
        "k_act": 25.0,
    }


def _generic_consumer(cid: str = "standard", *, min_on_h: int = 2) -> dict:
    return {
        "id": cid,
        "name": cid,
        "nominal_power_kw": 3.0,
        "min_on_quarterhours": min_on_h * 4,
        "generic_flex_window": {
            "start_hour": 16,
            "start_shift_h": 6.0,
            "duration_h": 2.0,
        },
        "daily_target_kwh": 6.0,
    }


def test_continue_on_state_tracks_open_block():
    consumer = _generic_consumer()
    run_state: dict[str, dict] = {}
    update_generic_flex_run_state(run_state, consumer, 3.0)
    assert continue_on_from_state({"generic_flex_run": run_state}, [consumer])["standard"]
    update_generic_flex_run_state(run_state, consumer, 3.0)
    assert not continue_on_from_state({"generic_flex_run": run_state}, [consumer])["standard"]


def test_min_on_force_continuation_at_horizon_start():
    prob = pulp.LpProblem("test", pulp.LpMinimize)
    on_vars = [pulp.LpVariable(f"on_{t}", cat=pulp.LpBinary) for t in range(4)]
    add_min_on_time_constraints(
        prob,
        on_vars,
        min_on_quarterhours=8,
        prefix="std",
        on_before_horizon=True,
        force_on_at_start=True,
    )
    prob.solve(pulp.PULP_CBC_CMD(msg=False))
    assert on_vars[0].value() == 1


def test_rolling_horizon_completes_two_hour_generic_block():
    day = datetime(2025, 1, 1)
    matrix = [_matrix_row(h, day) for h in range(20, 24)]
    consumer = _generic_consumer()
    battery = {
        "battery_capacity_kwh": 5.0,
        "max_power_kw": 5.0,
        "min_soc": 10.0,
        "max_soc": 100.0,
        "efficiency": 0.95,
    }
    rows = simulate_horizon(
        matrix,
        50.0,
        battery_params=battery,
        verbose=False,
        consumer_daily_targets_kwh={"standard": 6.0},
        flexible_consumers=[consumer],
    )
    delivered = sum(float(row.get("standard (kW)", 0.0) or 0.0) for row in rows)
    assert delivered == 6.0


def test_milp_continues_generic_block_when_continue_on_set():
    day = datetime(2025, 1, 1)
    matrix = [_matrix_row(21, day), _matrix_row(22, day), _matrix_row(23, day)]
    consumer = _generic_consumer()
    battery = {
        "battery_capacity_kwh": 5.0,
        "max_power_kw": 5.0,
        "min_soc": 10.0,
        "max_soc": 100.0,
        "efficiency": 0.95,
    }
    _, _, _, powers, _, _, _ = milp_optimizer(
        matrix,
        21,
        50.0,
        battery_params=battery,
        verbose=False,
        consumers=[consumer],
        consumer_remaining_kwh={"standard": 3.0},
        consumer_continue_on={"standard": True},
        terminal_soc_percent=50.0,
    )
    assert powers.get("standard", 0.0) == 3.0


def test_generic_start_guard_blocks_short_block_at_t0():
    prob = pulp.LpProblem("guard", pulp.LpMinimize)
    on_vars = [pulp.LpVariable(f"on_{t}", cat=pulp.LpBinary) for t in range(3)]
    add_generic_block_start_guard(
        prob,
        on_vars,
        eligible_indices=[0],
        min_hours=2,
        continuing=False,
    )
    prob += on_vars[0] <= 1
    prob.solve(pulp.PULP_CBC_CMD(msg=False))
    assert on_vars[0].value() == 0
