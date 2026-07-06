"""Tests für Preisprognose-Visualisierung und Live-Vorbereitung."""
from __future__ import annotations

from data.price_forecast_live import is_extrapolated_source
from data.price_forecast_model import TARGET_COLUMN
from data.price_forecast_viz import attach_forecast_columns, build_forecast_evaluation
from tests.test_price_forecast_model import _synthetic_frame


def test_is_extrapolated_source_accepts_mirror_and_predicted():
    assert is_extrapolated_source("mirrored") is True
    assert is_extrapolated_source("predicted") is True
    assert is_extrapolated_source("day_ahead") is False
    assert is_extrapolated_source(None) is False


def test_build_forecast_evaluation_adds_prediction_columns():
    frame = _synthetic_frame(96)
    evaluation = build_forecast_evaluation(frame, train_ratio=0.75)
    assert "model_cent_kwh" in evaluation.test.columns
    assert "mirror_cent_kwh" in evaluation.test.columns
    assert evaluation.model_metrics["mae_cent_kwh"] >= 0.0
