"""Season-mirror cons_data onto a wall-clock calendar window for current tariffs."""
from __future__ import annotations

import pandas as pd

from data.data_loader import last_complete_month_end

_SIMULATION_MONTHS = 12


def is_season_mirror_enabled() -> bool:
    import config

    return bool(
        config.get_scenario_explorer_conf().get("season_mirror_to_last_month", False)
    )


def wall_clock_simulation_window(
    *,
    now: pd.Timestamp | None = None,
) -> tuple[pd.Timestamp, pd.Timestamp]:
    """12 inclusive calendar months ending at last complete month before *now*."""
    today = pd.Timestamp(now or pd.Timestamp.now()).normalize()
    end = last_complete_month_end(today)
    start = (end.to_period("M") - (_SIMULATION_MONTHS - 1)).to_timestamp().normalize()
    return start, end


def _year_covers_month_days(
    index: pd.DatetimeIndex,
    *,
    year: int,
    month: int,
    required_days: set[int],
) -> bool:
    for day in required_days:
        for hour in range(24):
            try:
                src_ts = pd.Timestamp(year=year, month=month, day=day, hour=hour)
            except ValueError:
                return False
            if src_ts not in index:
                return False
    return True


def _source_year_for_month(
    df: pd.DataFrame,
    month: int,
    *,
    required_days: set[int],
) -> int:
    """Most recent year whose calendar month fully covers *required_days* (24h each)."""
    years = sorted(
        {int(ts.year) for ts in df.index if int(ts.month) == month},
        reverse=True,
    )
    if not years:
        raise ValueError(
            f"Season-Mirror: in cons_data fehlt Kalendermonat {month:02d} "
            "(kein Quelljahr verfügbar)."
        )
    for year in years:
        if _year_covers_month_days(
            df.index,
            year=year,
            month=month,
            required_days=required_days,
        ):
            return year
    raise ValueError(
        f"Season-Mirror: kein Quelljahr deckt Kalendermonat {month:02d} "
        f"vollständig ab (benötigte Tage: {sorted(required_days)[:8]}"
        f"{'…' if len(required_days) > 8 else ''})."
    )


def season_mirror_cons_dataframe(
    df: pd.DataFrame,
    *,
    target_start: pd.Timestamp,
    target_end: pd.Timestamp,
) -> pd.DataFrame:
    """
    Map hourly rows by calendar month onto [target_start, target_end] (inclusive days).

    For each target month, use the most recent same calendar month in *df* that
    fully covers the required target days. Hours that do not exist in the target
    month are dropped. Missing source days raise a clear error.
    """
    if df.empty:
        raise ValueError("Season-Mirror: cons_data ist leer.")

    start = pd.Timestamp(target_start).normalize()
    end = pd.Timestamp(target_end).normalize()
    if start > end:
        raise ValueError("Season-Mirror: target_start liegt nach target_end.")

    source = df.copy()
    if not isinstance(source.index, pd.DatetimeIndex):
        raise ValueError("Season-Mirror: cons_data braucht einen DatetimeIndex.")
    source = source[~source.index.duplicated(keep="last")].sort_index()

    target_index = pd.date_range(
        start=start,
        end=end + pd.Timedelta(hours=23),
        freq="h",
    )
    rows: list[pd.Series] = []
    missing: list[str] = []

    required_days_by_month: dict[int, set[int]] = {}
    for ts in target_index:
        required_days_by_month.setdefault(int(ts.month), set()).add(int(ts.day))

    source_year_by_month = {
        month: _source_year_for_month(
            source,
            month,
            required_days=days,
        )
        for month, days in required_days_by_month.items()
    }

    for ts in target_index:
        src_year = source_year_by_month[int(ts.month)]
        try:
            src_ts = ts.replace(year=src_year)
        except ValueError:
            # e.g. Feb 29 → non-leap source year
            missing.append(ts.strftime("%Y-%m-%d %H:%M"))
            continue
        if src_ts not in source.index:
            missing.append(ts.strftime("%Y-%m-%d %H:%M"))
            continue
        row = source.loc[src_ts]
        if isinstance(row, pd.DataFrame):
            row = row.iloc[-1]
        row = row.copy()
        row.name = ts
        rows.append(row)

    if missing:
        sample = ", ".join(missing[:5])
        more = f" (+{len(missing) - 5} weitere)" if len(missing) > 5 else ""
        raise ValueError(
            "Season-Mirror: Quellstunden fehlen in cons_data "
            f"({len(missing)} Lücken, z. B. {sample}{more})."
        )

    mirrored = pd.DataFrame(rows)
    mirrored.index.name = source.index.name or "timestamp"
    return mirrored
