"""Bootstrap migration: OeMAG keys scenarios → tariffs (earnie_data_model v2)."""
from __future__ import annotations

import json
from pathlib import Path

from runtime_store import bootstrap
from settings.json_io import read_json_dict

_OEMAG_RATES = [
    {"year": 2025, "month": m, "tariff_cent_kwh": float(m)}
    for m in range(1, 13)
]


def _env(monkeypatch, tmp_path: Path) -> Path:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    monkeypatch.setenv("EARNIE_ENV_PATH", str(tmp_path))
    monkeypatch.setenv("EARNIE_CONFIG_PATH", str(config_dir))
    return config_dir


def test_migrate_copies_oemag_from_scenarios_and_strips(tmp_path, monkeypatch):
    config_dir = _env(monkeypatch, tmp_path)
    scenarios = config_dir / "backtesting_scenarios.json"
    tariffs = config_dir / "tariffs.json"
    scenarios.write_text(
        json.dumps(
            {
                "earnie_data_model": 1,
                "oemag_monthly_feed_in_rates": _OEMAG_RATES,
                "monthly_float_reference_cent_kwh": 7.15,
                "scenarios": [],
            }
        ),
        encoding="utf-8",
    )
    tariffs.write_text(
        json.dumps(
            {
                "earnie_data_model": 1,
                "import_tariffs": [],
                "export_tariffs": [],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("EARNIE_TARIFFS_PATH", str(tariffs))
    monkeypatch.setenv("EARNIE_BACKTESTING_SCENARIOS_PATH", str(scenarios))

    modified = bootstrap._migrate_oemag_data_model_v2()
    assert str(tariffs) in modified
    assert str(scenarios) in modified

    tariffs_doc = read_json_dict(str(tariffs))
    scenarios_doc = read_json_dict(str(scenarios))
    assert len(tariffs_doc["oemag_monthly_feed_in_rates"]) == 12
    assert tariffs_doc["monthly_float_reference_cent_kwh"] == 7.15
    assert tariffs_doc["earnie_data_model"] == 2
    assert "oemag_monthly_feed_in_rates" not in scenarios_doc
    assert "monthly_float_reference_cent_kwh" not in scenarios_doc
    assert scenarios_doc["earnie_data_model"] == 2
    assert bootstrap._migrate_oemag_data_model_v2() == []


def test_migrate_strips_scenarios_when_tariffs_already_have_keys(tmp_path, monkeypatch):
    config_dir = _env(monkeypatch, tmp_path)
    scenarios = config_dir / "backtesting_scenarios.json"
    tariffs = config_dir / "tariffs.json"
    scenarios.write_text(
        json.dumps(
            {
                "earnie_data_model": 1,
                "oemag_monthly_feed_in_rates": _OEMAG_RATES,
                "monthly_float_reference_cent_kwh": 9.99,
                "scenarios": [],
            }
        ),
        encoding="utf-8",
    )
    tariffs.write_text(
        json.dumps(
            {
                "earnie_data_model": 1,
                "oemag_monthly_feed_in_rates": _OEMAG_RATES,
                "monthly_float_reference_cent_kwh": 7.15,
                "import_tariffs": [],
                "export_tariffs": [],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("EARNIE_TARIFFS_PATH", str(tariffs))
    monkeypatch.setenv("EARNIE_BACKTESTING_SCENARIOS_PATH", str(scenarios))

    modified = bootstrap._migrate_oemag_data_model_v2()
    assert str(scenarios) in modified

    tariffs_doc = read_json_dict(str(tariffs))
    scenarios_doc = read_json_dict(str(scenarios))
    assert tariffs_doc["monthly_float_reference_cent_kwh"] == 7.15
    assert "oemag_monthly_feed_in_rates" not in scenarios_doc
    assert "monthly_float_reference_cent_kwh" not in scenarios_doc
    assert scenarios_doc["earnie_data_model"] == 2
    assert tariffs_doc["earnie_data_model"] == 2
