"""Tests für diag_single_window-Helfer in der SE-Detaillansicht."""
from __future__ import annotations

from ui.backtesting_diag_single_window import (
    build_diag_single_window_argv,
    format_diag_single_window_command,
)


def test_build_diag_single_window_argv_includes_anchor_and_scenario():
    meta = {
        "period": {
            "start_month": 1,
            "end_month": 3,
        },
    }
    argv = build_diag_single_window_argv(
        "2025-01-02T07:00:00",
        "live",
        meta,
        initial_soc=55.5,
    )
    assert any("diag_single_window.py" in part for part in argv)
    assert "--anchor" in argv
    assert "2025-01-02 07:00:00" in argv
    assert "--scenario" in argv
    assert "live" in argv
    assert "--initial-soc" in argv
    assert "55.5" in argv
    assert "--start-month" in argv
    assert "1" in argv
    assert "--end-month" in argv
    assert "3" in argv


def test_format_diag_single_window_command():
    argv = ["python", "scripts/diag_single_window.py", "--scenario", "live"]
    command = format_diag_single_window_command(argv)
    assert "diag_single_window.py" in command
    assert "live" in command
