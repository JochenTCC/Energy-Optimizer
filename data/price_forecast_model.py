"""OLS-Preisprognosemodell (EU-Wetter & Erzeugung) — Spec: price-forecast-renewables."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

MODEL_VERSION = 1
TARGET_COLUMN = "price_epex_cent_kwh"
RAW_FEATURE_COLUMNS: tuple[str, ...] = (
    "eu_wind_mw",
    "eu_solar_mw",
    "eu_wind_speed_kmh",
    "eu_shortwave_radiation_wm2",
)
DERIVED_FEATURE_COLUMNS: tuple[str, ...] = (
    "hour_sin",
    "hour_cos",
    "weekday",
    "month",
)
FEATURE_COLUMNS: tuple[str, ...] = RAW_FEATURE_COLUMNS + DERIVED_FEATURE_COLUMNS


@dataclass(frozen=True)
class PriceForecastModel:
    """Trainiertes lineares Preismodell (EPEX Cent/kWh)."""

    version: int
    feature_names: tuple[str, ...]
    coefficients: tuple[float, ...]
    trained_range_start: str
    trained_range_end: str
    training_rows: int

    def predict_matrix(self, features: np.ndarray) -> np.ndarray:
        if features.shape[1] != len(self.coefficients):
            raise ValueError(
                f"Feature-Matrix hat {features.shape[1]} Spalten, "
                f"erwartet {len(self.coefficients)}."
            )
        return features @ np.asarray(self.coefficients, dtype=float)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "feature_names": list(self.feature_names),
            "coefficients": list(self.coefficients),
            "trained_range_start": self.trained_range_start,
            "trained_range_end": self.trained_range_end,
            "training_rows": self.training_rows,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> PriceForecastModel:
        return cls(
            version=int(payload["version"]),
            feature_names=tuple(payload["feature_names"]),
            coefficients=tuple(float(c) for c in payload["coefficients"]),
            trained_range_start=str(payload["trained_range_start"]),
            trained_range_end=str(payload["trained_range_end"]),
            training_rows=int(payload["training_rows"]),
        )


def load_training_dataset(path: Path) -> pd.DataFrame:
    """Lädt ein von build_price_training_dataset erzeugtes CSV."""
    if not path.exists():
        raise FileNotFoundError(f"Training-Dataset nicht gefunden: {path}")
    frame = pd.read_csv(path, parse_dates=["slot_datetime"])
    frame = frame.set_index("slot_datetime").sort_index()
    missing = [col for col in (*RAW_FEATURE_COLUMNS, TARGET_COLUMN) if col not in frame.columns]
    if missing:
        raise ValueError(f"Dataset-Spalten fehlen: {', '.join(missing)}")
    return frame


def enrich_model_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Ergänzt zyklische Stundenfeatures; weekday/month aus Index falls nötig."""
    enriched = frame.copy()
    if "hour" not in enriched.columns:
        enriched["hour"] = enriched.index.hour
    if "weekday" not in enriched.columns:
        enriched["weekday"] = enriched.index.weekday
    if "month" not in enriched.columns:
        enriched["month"] = enriched.index.month
    hours = enriched["hour"].to_numpy(dtype=float)
    enriched["hour_sin"] = np.sin(2.0 * math.pi * hours / 24.0)
    enriched["hour_cos"] = np.cos(2.0 * math.pi * hours / 24.0)
    return enriched


def build_feature_matrix(frame: pd.DataFrame) -> np.ndarray:
    """Design-Matrix inkl. Intercept (erste Spalte)."""
    enriched = enrich_model_features(frame)
    columns = [np.ones(len(enriched), dtype=float)]
    for name in FEATURE_COLUMNS:
        columns.append(enriched[name].to_numpy(dtype=float))
    return np.column_stack(columns)


def feature_column_names() -> tuple[str, ...]:
    return ("intercept",) + FEATURE_COLUMNS


def fit_price_model(frame: pd.DataFrame) -> PriceForecastModel:
    """OLS auf dem übergebenen DataFrame."""
    if frame.empty:
        raise ValueError("fit_price_model erfordert mindestens eine Zeile.")
    matrix = build_feature_matrix(frame)
    targets = frame[TARGET_COLUMN].to_numpy(dtype=float)
    coefficients, _, _, _ = np.linalg.lstsq(matrix, targets, rcond=None)
    index = frame.index
    return PriceForecastModel(
        version=MODEL_VERSION,
        feature_names=feature_column_names(),
        coefficients=tuple(float(c) for c in coefficients),
        trained_range_start=index[0].isoformat(),
        trained_range_end=index[-1].isoformat(),
        training_rows=len(frame),
    )


def predict_prices(model: PriceForecastModel, frame: pd.DataFrame) -> np.ndarray:
    matrix = build_feature_matrix(frame)
    return model.predict_matrix(matrix)


def save_price_model(model: PriceForecastModel, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(model.to_dict(), handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def load_price_model(path: Path) -> PriceForecastModel:
    with open(path, encoding="utf-8") as handle:
        payload = json.load(handle)
    model = PriceForecastModel.from_dict(payload)
    if model.version != MODEL_VERSION:
        raise ValueError(
            f"Preismodell-Version {model.version} wird nicht unterstützt "
            f"(erwartet {MODEL_VERSION})."
        )
    return model


def regression_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    """MAE, RMSE und MAPE (nur wo |actual| > 0.5 Cent/kWh)."""
    if len(actual) != len(predicted):
        raise ValueError("actual und predicted müssen gleiche Länge haben.")
    if len(actual) == 0:
        raise ValueError("Keine Werte für Metriken.")
    errors = predicted - actual
    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(errors ** 2)))
    mask = np.abs(actual) > 0.5
    if np.any(mask):
        mape = float(
            np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])) * 100.0
        )
    else:
        mape = float("nan")
    return {"mae_cent_kwh": mae, "rmse_cent_kwh": rmse, "mape_percent": mape}
