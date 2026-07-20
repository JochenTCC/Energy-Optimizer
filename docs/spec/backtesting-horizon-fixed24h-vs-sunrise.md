# Backtesting comparison: `fixed_24h` vs `sunrise_window` (sunset2set)

**Date:** 2026-07-20  
**App version:** `2.2.0-alpha.6`  
**Sources:**

| Mode | Log file | `horizon_mode` in JSON |
|------|----------|------------------------|
| Fixed 24 h | `earnie_env/runtime/backtesting_log_fixed24h.json` | `fixed_24h` |
| Sunset2set / sunrise window | `earnie_env/runtime/backtesting_log_sunset2set.json` | `sunrise_window` |

Related specs: [Planning horizon sunset](planning-horizon-sunset.md), [UI Sunset-2-Sunset](ui-sunset2sunset.md).

## 1. Executive summary

On a full year of historical backtesting with **perfect foresight** prices, **`sunrise_window` is economically better on every optimized scenario** (about **€39–91/year** lower net cost). Gains are largest with a battery and concentrate in spring–autumn. Winter is nearly flat.

**Compute trade-off:** full-year wall clock was similar (~2 h for both multi-scenario runs), but `sunrise_window` produced **far more `strict_slow` events** (59 vs 1), almost all on battery scenarios. Problem-window CBC elapsed time jumped from ~2.7 s aggregate (fixed) to ~120 s (sunrise). Live and second-PV-only scenarios had **no** CBC problem events under sunrise.

**Bottom line:** Prefer `sunrise_window` for economic benefit in Scenario Explorer / planning; expect higher MILP pressure on battery-heavy scenarios (more hits of the ~2 s strict limit).

## 2. Experiment setup (identical unless noted)

| Parameter | Value |
|-----------|--------|
| Period | `2025-07-21` → `2026-07-20` |
| Windows / hours | 365 / 8760 |
| Price source / strategy | `api` / `perfect` |
| Scenarios | Live, Mit 15 kWh Speicher (`mit_10_kwh_speicher`), Mit zweiter PV-Anlage, Zweite PV + 15 kWh (`mein_szenario`) |
| References | Historisch, `ref:live`, `ref:mit_zweiter_pv_anlage` (unchanged between runs) |

### Mode definitions (engine)

From `simulation/engine.py`:

- **`fixed_24h`:** MILP on `[anchor−24h, anchor)`; SOC free at window end (EV-style anchor).
- **`sunrise_window`:** MILP from now → **SA₂** (second sunrise); hard **SOC_min** at the next sunrise; chart/backtest **output still 24 h per step**.

The sunset2set log file name maps to internal id `sunrise_window` (not a separate JSON enum value).

## 3. Annual costs and optimization benefit

Lower net cost (€) is better; negative = net credit.

### 3.1 Total net cost (€/year)

| Scenario | `fixed_24h` | `sunrise_window` | Δ (sunrise − fixed) |
|----------|------------:|-----------------:|--------------------:|
| Live | 464.96 | 426.08 | **−38.88** |
| Mit 15 kWh Speicher | 373.84 | 292.05 | **−81.78** |
| Mit zweiter PV-Anlage | 57.17 | 11.42 | **−45.75** |
| Zweite PV + 15 kWh | 12.27 | **−78.34** | **−90.61** |

References (same in both logs): Historisch 1831.55 · ref:live 1116.51 · ref:2nd PV 655.59.

### 3.2 Optimization benefit vs matching reference

Benefit = reference − optimized (€/year). Higher = more value from MILP.

| Scenario | Reference | Benefit `fixed_24h` | Benefit `sunrise_window` | Extra from sunrise |
|----------|-----------|--------------------:|-------------------------:|-------------------:|
| Live | ref:live | 651.55 | 690.43 | **+38.88** |
| 15 kWh Speicher | ref:live | 742.67 | 824.46 | **+81.78** |
| 2nd PV | ref:2nd PV | 598.42 | 644.17 | **+45.75** |
| 2nd PV + 15 kWh | ref:2nd PV | 643.32 | 733.93 | **+90.61** |

**Pattern:** Battery amplifies the sunrise-horizon advantage (longer look-ahead + sunrise SOC floor).

## 4. Monthly cost deltas

Δ = sunrise − fixed (€). Negative = sunrise cheaper that month.

| Month | Live | 15 kWh | 2nd PV | 2nd PV + 15 kWh |
|-------|-----:|-------:|-------:|----------------:|
| 2025-07 | −1.80 | −4.03 | −1.86 | −4.35 |
| 2025-08 | −3.88 | −9.64 | −5.47 | −10.76 |
| 2025-09 | −3.57 | −8.51 | −4.66 | −9.63 |
| 2025-10 | −1.69 | −3.63 | −2.57 | −4.51 |
| 2025-11 | −0.46 | −0.45 | −0.91 | −2.94 |
| 2025-12 | **+0.52** | −0.83 | +0.04 | −1.99 |
| 2026-01 | **+0.12** | −0.88 | −0.49 | −2.69 |
| 2026-02 | −1.02 | −0.65 | −1.50 | −3.00 |
| 2026-03 | −5.24 | −6.63 | −6.09 | −13.04 |
| 2026-04 | −4.54 | −8.94 | −6.91 | −13.49 |
| 2026-05 | −5.44 | −13.38 | −7.06 | −14.54 |
| 2026-06 | −7.77 | −15.77 | −3.29 | −5.02 |
| 2026-07 | −4.12 | −8.44 | −4.99 | −4.63 |

**Seasonality:** Largest gains Mar–Jun and Aug–Sep. Deep winter (Dec–Jan) is near zero; Live alone is slightly worse under sunrise in Dec/Jan only.

## 5. Computing demands

### 5.1 Wall-clock (full multi-scenario year)

Timestamps from log headers (`created_at` → `written_at`):

| Run | Created | Written | Approx. duration |
|-----|---------|---------|------------------|
| `fixed_24h` | 2026-07-20T11:26:07Z | 2026-07-20T13:26:08 | **~2 h 0 min** |
| `sunrise_window` | 2026-07-20T17:50:14Z | 2026-07-20T19:50:15 | **~2 h 0 min** |

Both full-year runs (4 optimized scenarios + shared references) finished in roughly the **same wall-clock time**. Overall batch runtime is therefore not a strong differentiator for this machine/config; load is dominated by shared I/O and the large number of normal (fast) windows.

### 5.2 CBC / MILP problem events (compute pressure)

CBC event summaries count windows where the strict solver path was slow, fell back, or returned no optimal:

| Metric | `fixed_24h` | `sunrise_window` |
|--------|------------:|-----------------:|
| `strict_slow` | 1 | **59** |
| `strict_fallback` | 56 | 37 |
| `milp_no_optimal` | 56 | 37 |
| Critical cases (all kinds) | 146 | 155 |
| Distinct critical windows | 75 | **46** |

By scenario (`cbc_events_summary`):

| Scenario | fixed: fallback / no_opt / slow | sunrise: fallback / no_opt / slow |
|----------|--------------------------------:|----------------------------------:|
| Live | 5 / 5 / 0 | **0 / 0 / 0** |
| Mit zweiter PV | 33 / 33 / 0 | **0 / 0 / 0** |
| Mit 15 kWh Speicher | 4 / 4 / 1 | 18 / 18 / **37** |
| Zweite PV + 15 kWh | 14 / 14 / 0 | 19 / 19 / **22** |

**Interpretation:** Sunrise shifts pressure onto **battery** scenarios (longer horizon → harder MILP). Live and PV-only are *cleaner* under sunrise (no CBC problem events in this run). Fixed had many infeasibility/fallback pairs on 2nd-PV.

### 5.3 Strict solve elapsed time (problem windows only)

Logged `strict_elapsed_sec` exists only for CBC/critical events that recorded a strict solve — **not** every window. Still useful as a hardness proxy (strict limit ≈ **2.0 s**).

| Aggregate over logged strict solves | `fixed_24h` | `sunrise_window` |
|-------------------------------------|------------:|-----------------:|
| Count `n` | 57 | 96 |
| Sum (s) | 2.69 | **120.32** |
| Mean (s) | 0.047 | **1.25** |
| Median (s) | 0.010 | **2.025** |
| Max (s) | 2.021 | 2.155 |
| Solves ≥ 1 s | 1 | **59** |
| Solves ≥ 2 s | 1 | **55** |

Per scenario (sunrise; fixed almost always ~10 ms except one slow hit):

| Scenario | Sunrise sum (s) | Sunrise mean (s) | Sunrise ≥ 2 s |
|----------|----------------:|-----------------:|--------------:|
| Live | — (no timed CBC events) | — | 0 |
| Mit zweiter PV | — | — | 0 |
| Mit 15 kWh Speicher | 75.40 | 1.37 | 34 |
| Zweite PV + 15 kWh | 44.92 | 1.10 | 21 |

**Live / production implication:** A single live planning step under `sunrise_window` can hit the ~2 s strict budget more often when a battery is in the model. For offline backtesting of a full year, total wall clock stayed comparable because most windows remain fast and slow windows cap near the limit.

### 5.4 Plausibility (consumption balance)

| Scenario | fixed ok / fail | sunrise ok / fail |
|----------|----------------:|------------------:|
| Live | 358 / 7 | 357 / 8 |
| Mit 15 kWh | 358 / 7 | 359 / 6 |
| Mit zweiter PV | 351 / **14** | 361 / **4** |
| Zweite PV + 15 kWh | 360 / 5 | 361 / 4 |

Sunrise improved consumption-tolerance outcomes especially for **2nd PV** (14 → 4 failures). Critical `consumption_tolerance` counts: 33 (fixed) vs 22 (sunrise).

## 6. Synthesis: benefit vs compute

| Dimension | Winner | Notes |
|-----------|--------|--------|
| Annual € (all scenarios) | **`sunrise_window`** | +€39 … +€91 vs fixed |
| Battery scenarios | **`sunrise_window`** | Largest € gain; highest slow-MILP rate |
| Live without battery | **`sunrise_window`** | +€39; CBC clean in this run |
| Winter months | Tie / slight fixed for Live | Dec–Jan negligible |
| Batch wall clock (year × 4) | Tie | ~2 h both |
| Peak / hard-window CPU | **`fixed_24h` lighter** | 1 vs 59 `strict_slow` |
| Plausibility (2nd PV) | **`sunrise_window`** | Fewer consumption fails |

**Recommendation for Scenario Explorer / planning default:** use **`sunrise_window`** when economic fidelity matters. Monitor MILP time limits on battery scenarios; consider documenting that community/backtesting users may see more `strict_slow` flags without a large increase in full-year batch duration.

## 7. Caveats

1. **Perfect foresight** (`price_strategy: perfect`) overstates absolute € vs live imperfect forecasts; **relative** mode ranking is still informative.
2. House / tariff / geo (astral sunrise) are specific to this Earnie env — do not treat € deltas as universal.
3. CBC timings cover **problem events only**, not mean solve time over all 365×4 MILP calls.
4. Wall-clock equality may differ on other CPUs or with different CBC time limits.
5. Log naming: file `backtesting_log_sunset2set.json` ↔ engine mode `sunrise_window`.

## 8. Reproduction pointers

- Horizon parsing / matrix: `simulation/horizon_mode.py`, `simulation/engine.py` (`build_sunrise_window_matrix`, `run_historical_simulation`).
- Tests: `tests/test_backtesting_horizon_mode.py` (includes a short runtime regression: sunrise must not be drastically slower than fixed on a tiny sample).
- Logs under `earnie_env/runtime/` (local, not committed).
