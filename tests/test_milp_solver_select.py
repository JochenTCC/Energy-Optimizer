from __future__ import annotations

import os

import pulp
import pytest

from optimizer.cbc_solver import (
    DEFAULT_MILP_SOLVER,
    ENV_MILP_SOLVER,
    build_highs_solver_cmd,
    clear_cbc_solver_env,
    reset_milp_solver_override,
    resolve_milp_solver,
    set_milp_solver_override,
    solve_with_strict_fallback,
)


@pytest.fixture(autouse=True)
def _clear_env():
    clear_cbc_solver_env()
    yield
    clear_cbc_solver_env()


def test_default_milp_solver_is_highs():
    assert resolve_milp_solver() == DEFAULT_MILP_SOLVER
    assert resolve_milp_solver() == "highs"


def test_env_overrides_milp_solver():
    os.environ[ENV_MILP_SOLVER] = "cbc"
    assert resolve_milp_solver() == "cbc"


def test_context_override_when_env_unset():
    token = set_milp_solver_override("cbc")
    try:
        assert resolve_milp_solver() == "cbc"
    finally:
        reset_milp_solver_override(token)
    assert resolve_milp_solver() == "highs"


def test_env_wins_over_context_override():
    os.environ[ENV_MILP_SOLVER] = "highs"
    token = set_milp_solver_override("cbc")
    try:
        assert resolve_milp_solver() == "highs"
    finally:
        reset_milp_solver_override(token)


def test_invalid_milp_solver_raises():
    os.environ[ENV_MILP_SOLVER] = "gurobi"
    with pytest.raises(ValueError, match="Unknown MILP solver"):
        resolve_milp_solver()


def test_highs_without_highspy_raises_clear_error(monkeypatch):
    class _FakeHiGHS:
        def __init__(self, *args, **kwargs):
            pass

        def available(self):
            return False

    monkeypatch.setattr(pulp, "HiGHS", _FakeHiGHS)
    with pytest.raises(RuntimeError, match="pip install highspy"):
        build_highs_solver_cmd(msg=False, gap_rel=0.1)


def test_highs_solves_tiny_mip():
    os.environ["EARNIE_CBC_STRICT_TIME_LIMIT_SEC"] = "0"
    prob = pulp.LpProblem("t_highs", pulp.LpMinimize)
    x = pulp.LpVariable("x", lowBound=0, cat="Integer")
    prob += x
    prob += x >= 1
    status = solve_with_strict_fallback(prob, msg=False)
    assert status == "Optimal"
    assert x.value() == pytest.approx(1.0)
