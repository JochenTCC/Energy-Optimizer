"""Live-Vorbereitung: Preisprognose für fehlende Day-Ahead-Slots (Phase 3)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from data.market_prices import PRICE_SOURCE_DAY_AHEAD, PRICE_SOURCE_MIRRORED
from data.price_forecast_model import (
    PriceForecastModel,
    load_price_model,
    predict_prices,
)

from data.market_prices import PRICE_SOURCE_PREDICTED
MISSING_PRICE_STRATEGY_MIRROR = "mirror"
MISSING_PRICE_STRATEGY_FORECAST = "forecast"
DEFAULT_MODEL_PATH = Path("data/cache/price_model_coefficients.json")


def get_missing_price_strategy() -> str:
    """
    Liest market_prices.missing_price_strategy aus config.json.
    Standard: mirror (kein Verhaltenswechsel ohne explizite Config).
    """
    import config

    block = config.Config._read_json_dict(str(config.CONFIG_JSON_PATH)).get("market_prices")
    if not isinstance(block, dict):
        return MISSING_PRICE_STRATEGY_MIRROR
    strategy = str(block.get("missing_price_strategy", MISSING_PRICE_STRATEGY_MIRROR)).strip()
    if strategy not in (MISSING_PRICE_STRATEGY_MIRROR, MISSING_PRICE_STRATEGY_FORECAST):
        raise ValueError(
            "market_prices.missing_price_strategy muss 'mirror' oder 'forecast' sein."
        )
    return strategy


def get_forecast_model_path() -> Path:
    import config

    block = config.Config._read_json_dict(str(config.CONFIG_JSON_PATH)).get("market_prices")
    if isinstance(block, dict) and block.get("forecast_model_path"):
        return Path(str(block["forecast_model_path"]))
    return DEFAULT_MODEL_PATH


def load_configured_model() -> PriceForecastModel | None:
    path = get_forecast_model_path()
    if not path.exists():
        return None
    return load_price_model(path)


def predict_epex_cent_for_features(frame: pd.DataFrame, model: PriceForecastModel) -> list[float]:
    return [float(v) for v in predict_prices(model, frame)]


def build_predicted_slot(
    slot_datetime,
    epex_cent: float,
    *,
    model_path: Path | None = None,
) -> dict[str, Any]:
    """Erzeugt einen resolve_market_slots-kompatiblen Preis-Slot."""
    from data.market_prices import epex_to_brutto_cent

    row: dict[str, Any] = {
        "slot_datetime": slot_datetime,
        "hour": slot_datetime.hour,
        "price_buy": round(float(epex_cent), 4),
        "price_source": PRICE_SOURCE_PREDICTED,
        "k_act": epex_to_brutto_cent(float(epex_cent)),
    }
    if model_path is not None:
        row["forecast_model_path"] = str(model_path)
    return row


def is_extrapolated_source(price_source: str | None) -> bool:
    """Chart/UI: extrapoliert = gespiegelt oder prognostiziert."""
    return price_source in (PRICE_SOURCE_MIRRORED, PRICE_SOURCE_PREDICTED)
