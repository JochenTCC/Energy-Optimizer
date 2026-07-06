#!/usr/bin/env python3
"""Trainiert das OLS-Preisprognosemodell aus einem Training-CSV."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from data.price_forecast_eval import chronological_split_evaluate
from data.price_forecast_model import (
    fit_price_model,
    load_training_dataset,
    regression_metrics,
    save_price_model,
    predict_prices,
)


def _default_dataset() -> Path:
    cache = Path("data/cache")
    candidates = sorted(cache.glob("price_training_*.csv"), key=lambda p: p.stat().st_mtime)
    if not candidates:
        raise FileNotFoundError(
            "Kein Training-Dataset in data/cache/. "
            "Zuerst: python -m scripts.build_price_training_dataset"
        )
    return candidates[-1]


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="OLS-Preisprognose trainieren (Spec: price-forecast-renewables.md)"
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=None,
        help="Training-CSV (Standard: neuestes data/cache/price_training_*.csv)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/cache/price_model_coefficients.json"),
        help="Ziel-JSON mit Koeffizienten",
    )
    parser.add_argument(
        "--holdout-ratio",
        type=float,
        default=0.2,
        help="Anteil am Ende fuer Holdout-Metriken (0 = kein Holdout)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        dataset_path = args.dataset or _default_dataset()
        frame = load_training_dataset(dataset_path)
    except (OSError, ValueError, FileNotFoundError) as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 1

    holdout_ratio = float(args.holdout_ratio)
    if holdout_ratio > 0.0:
        train_ratio = 1.0 - holdout_ratio
        if len(frame) * holdout_ratio < 24:
            print(
                "Warnung: Holdout zu klein -- trainiere auf vollem Dataset.",
                file=sys.stderr,
            )
            train_frame = frame
            holdout_report = None
        else:
            split = int(len(frame) * train_ratio)
            train_frame = frame.iloc[:split]
            holdout_report = chronological_split_evaluate(frame, train_ratio=train_ratio)
    else:
        train_frame = frame
        holdout_report = None

    model = fit_price_model(train_frame)
    save_price_model(model, args.output)

    in_sample = regression_metrics(
        train_frame["price_epex_cent_kwh"].to_numpy(),
        predict_prices(model, train_frame),
    )

    print(f"Dataset: {dataset_path} ({len(frame)} h)")
    print(f"Modell: {args.output} ({model.training_rows} Trainingszeilen)")
    print("In-sample:", json.dumps(in_sample, ensure_ascii=False))
    if holdout_report is not None:
        print("Holdout:", json.dumps(holdout_report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
