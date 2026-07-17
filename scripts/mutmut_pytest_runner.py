"""Normalize pytest exit codes for mutmut (collection errors must count as killed)."""
from __future__ import annotations

import subprocess
import sys


TESTS = [
    "tests/test_cons_data_house_profile.py",
    "tests/test_backtesting_cons_data.py",
    "tests/test_thermal_flex_bridge.py",
    "tests/test_appliance_config.py",
    "tests/test_config_runtime_resolution.py",
]


def main() -> int:
    cmd = [sys.executable, "-m", "pytest", *TESTS, "-x", "-q"]
    completed = subprocess.run(cmd, check=False)
    # mutmut 2.x only reliably treats exit code 1 as "killed"; pytest uses
    # 2 (usage), 3 (internal), 4 (collection) for other failures.
    if completed.returncode == 0:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
