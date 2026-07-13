🗺️ Project Roadmap & Backlog

Completed items → [Backlog-Erledigt.md](Backlog-Erledigt.md)

Open bugfixes → [Backlog-Bugfixes.md](Backlog-Bugfixes.md)

## Research Items

- [ ] **Swim spa:** second heat path into ground (lookup `bodentemperaturen_nach_monat`):
  - 1: 6.5, 2: 5.0, 3: 4.0, 4: 5.5, 5: 8.5, 6: 11.5, 7: 14.0, 8: 16.0, 9: 17.5, 10: 15.5, 11: 12.5, 12: 9.5 (°C)
- [x] Review Smart Energy app for comparison
- [x] Review other providers with flexible prices
- [ ] Adapt business plan
- [ ] **Outreach (not software):** Ask for interested parties in loxforum / reddit — post under “my project”; take interesting chart snapshots (loxforum admins contacted re. best place)



## Reminder für Greenfield Reset

It depends which local Greenfield setup you mean — the project distinguishes venv (:8511) and Docker (:8502).

Local venv Greenfield (port 8511)
Stop any running main.py / Streamlit first, then from the repo root:

Remove-Item -Recurse -Force greenfield\config, greenfield\runtime
mkdir greenfield\config, greenfield\runtime
Then restart via VS Code „main.py + Streamlit (Greenfield :8511)“ (or the individual Greenfield launch configs). Bootstrap runs automatically on startup and recreates the default files.

Docker Greenfield (port 8502)
Manual reset (from docs/einrichtung/greenfield-dev-stack.md):

docker compose -f docker-compose-greenfield.yml down
Remove-Item -Recurse -Force greenfield\config, greenfield\runtime
mkdir greenfield\config, greenfield\runtime
docker compose -f docker-compose-greenfield.yml up -d --build
One-liner (reset + start + smoke checks):

.venv\Scripts\python.exe -m scripts.smoke_greenfield_docker --reset
Use --no-build if you don’t want to rebuild the image:

.venv\Scripts\python.exe -m scripts.smoke_greenfield_docker --reset --no-build
Note: All of these wipe everything under greenfield/config/ and greenfield/runtime/; your normal ./config and ./runtime dev stack is untouched.

Command für boots

For bootstrap (scripts.bootstrap_runtime):

Default dev stack (config/ + runtime/)
.venv\Scripts\python.exe -m scripts.bootstrap_runtime
Creates only missing files; existing ones are not overwritten.

Greenfield (venv, port 8511)
After wiping greenfield\config and greenfield\runtime, either restart via VS Code (main.py + Streamlit Greenfield :8511) — bootstrap runs automatically — or run it manually with Greenfield env vars:

$env:EARNIE_CONFIG_PATH = "greenfield/config/config.json"
$env:EARNIE_RUNTIME_DIR = "greenfield/runtime"
$env:EARNIE_DOTENV_PATH = "greenfield/config/.env"
$env:EARNIE_HOUSE_PROFILES_PATH = "greenfield/config/house_profiles.json"
$env:EARNIE_TARIFFS_PATH = "greenfield/config/tariffs.json"
$env:EARNIE_BACKTESTING_SCENARIOS_PATH = "greenfield/config/backtesting_scenarios.json"
.venv\Scripts\python.exe -m scripts.bootstrap_runtime

## Feature Backlog



### Version 2.0

Branding (Earnie rename) → [Backlog-Erledigt.md](Backlog-Erledigt.md).

**Status (2026-07-12):** P1–P5, **P6a**, and **Components** done (see [Backlog-Erledigt.md](Backlog-Erledigt.md)). Open under 2.0: **P7** + EV nominal voltage + remaining smoke follow-ups. Loxone sidebar bugfix → [Backlog-Erledigt.md](Backlog-Erledigt.md); cons_data ID fix pending verification in [Backlog-Bugfixes.md](Backlog-Bugfixes.md).

Recommended order (2.0): smoke-test **next actions** (below) → **P7** README / evaluations → propose `version.py` → `2.0.0` (user approval). **P6b** live cutover → **2.+1** (first item after 2.0 release).

Critical path: **fixed-tariff SE investigation**, then **P7**. Open bugs → [Backlog-Bugfixes.md](Backlog-Bugfixes.md).

**Decisions (2026-07-11):**


| Topic                            | Decision                                                                                                                                                                                                                |
| -------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `EARNIE_UI_MODES` key            | Hard rename `backtesting` **→** `scenario_exploration` — no alias; update compose, launch configs, docs, tests in same PR (P2)                                                                                          |
| Scenario id `runtime_settings`   | **Remove in 2.0** — live baseline is a normal scenario entry (default id `live`) selected via `live_scenario_id` in `config.json`; update scripts/tests/fixtures in same release (P2)                                   |
| Battery without PV               | **Allowed** — battery still required for MILP / planning readiness; PV optional (zero PV forecast when `pv_system_id` unset) (P1)                                                                                       |
| **7g-a** before P6               | **Skip for 2.0** — parallel NAS stack after local silent acceptance; 7g-a remains in Packaging backlog, not a 2.0 gate                                                                                                  |
| **P6 NAS deploy**                | **Parallel stack** — deploy validated `silent-migration-test/` to a new NAS folder; legacy `docker/earnie/` unchanged for rollback; **P6a** silent trial done; **P6b** non-silent cutover → **2.+1**                    |
| `sunrise_window` **rename (P4)** | Hard rename `sunset_window` **→** `sunrise_window` — no alias; internal symbols renamed; prod deploy only with P6a config migration                                                                                     |
| **2.0 release gate**             | `version.py` **→** `2.0.0` after **P7** acceptance (user approval); **P6b** not required for 2.0 release                                                                                                                |
| `components.json` **sidecar**    | **Hard cutover in 2.0** — `batteries[]` / `pv_systems[]` only in `config/components.json`; startup error if keys remain in `config.json`; no alias/fallback (same pattern as `runtime_settings`, global `battery_wear`) |




### Version 2.0 — smoke-test follow-ups

Components (`components.json` sidecar) → [Backlog-Erledigt.md](Backlog-Erledigt.md).

- [ ] **Scenario-Exploration without PV** — optimization/backtesting path incomplete when `pv_system_id` unset (P1 allows battery-only; simulation/MILP gaps remain)
- [ ] **EV nominal voltage for power calculation** — configurable per EV consumer (house profile + `flexible_consumers`); replace hardcoded 230 V in A→kW conversion (`integrations/loxone_client.py`); shared helper for live and planning paths; default 230 V / 1 phase when unset



#### Smoketest Findings — next actions (2026-07-12)

Ordered work plan after greenfield smoke. **Bugfix** items → [Backlog-Bugfixes.md](Backlog-Bugfixes.md); **UX/copy** here; **investigation** ties to *Backtesting Tests* below.

**Phase B — Scenario-Exploration credibility (fixed tariffs)**

1. [ ] **SE higher cost after optimization with** `fixed_24h` **+ fixed-price tariffs** — deviations note *extra consumption*; greenfield scenario uses `fixed_25ct` / `fixed_37ct`
  - Reproduce: scenario **without EV** and **with EV** (see *Backtesting Tests* below)
  - Per bad window: `scripts/diag_single_window.py --anchor …`; check plausibility / deviation list vs reference (`historical_reference`)
  - Answer: is there optimization potential with flat import prices? (expect mainly PV self-consumption / export spread, not import timing)
  - If plausibility fails → bugfix + regression; if consumption matches but cost higher → battery wear / terminal SOC / export math
  - **Dump for single days:** CLI exists (`diag_single_window.py`); optional follow-up: expose from SE deviation detail (not a new dump format)
  - **Multiple scenarios for testing:** already supported in Szenarieneditor + `backtesting_scenarios.json`; document adding comparison entries (greenfield currently only `live`)



##### Plan of Attack

1. [ ] **SE higher cost after optimization with** `fixed_24h` **+ fixed-price tariffs** — deviations note *extra consumption*; greenfield scenario uses `fixed_25ct` / `fixed_37ct`
  **Goal:** (1) Is simulation plausible (kWh within tolerance)? (2) If plausible, why is € worse — bug, reference mismatch, or expected economics on flat import?
   **Phase 0 — Test matrix** (`greenfield/config/backtesting_scenarios.json`; pattern in `config/backtesting_scenarios.example.json`):
  - [x] `fixed_full` — `fixed_25ct` / `fixed_37ct`, full house (heat + PV + battery + EV)
  - [x] `fixed_no_pv` — `pv_system_id` unset
  - [x] `fixed_no_battery` — `battery_id` unset
  - [x] `fixed_no_pv_no_battery` — no battery, no EV
  - All runs: `--horizon-mode fixed_24h` (not `sunrise_window`)
   **Phase 1 — Bulk reproduce & classify**
  - [ ] Run per scenario: `scripts/run_backtesting.py --horizon-mode fixed_24h --start-month 1 --end-month 12`
  - [ ] Record: total € vs `historical_reference`, plausibility ok/total, deviation kinds (`consumption_tolerance` vs CBC)
  - [ ] Many consumption deviations → Phase 3A; plausibility clean but € worse → Phase 3B; use `scripts/analyze_plausibility_failures.py` if needed
    **Phase 2 — Reference fairness (do first — high leverage)**
  - [ ] `compute_historical_reference_costs` in `scripts/run_backtesting.py` is called **without** scenario tariff context → reference uses default/live import pricing while optimized scenario uses `fixed_25ct` / `fixed_37ct`
  - [ ] Recompute one window: reference cost **with** scenario tariffs vs optimized; if Δ€ collapses → fix is per-scenario reference tariffs (design), not MILP
    **Phase 3A — Plausibility failures (*extra consumption*)**
  - [ ] Per bad window: `scripts/diag_single_window.py --anchor … --scenario …`
  - [ ] Compare historical vs optimized kWh (tolerance: 0.5 kWh or 5% — `CONSUMPTION_TOLERANCE_*` in `simulation/engine.py`); split baseload vs flex (EV + `ready_by_hour` under `fixed_24h` is regression-sensitive — cf. 1.25.d)
  - [ ] Confirmed bug → [Backlog-Bugfixes.md](Backlog-Bugfixes.md) + pytest regression
    **Phase 3B — Plausible but more expensive**
  - [ ] Per 24h window decompose: consumer kWh, grid import/export kWh, import €, export €, end SOC vs start (`terminal_soc_percent` under `fixed_24h`)
  - [ ] Expected ceiling with flat import: savings only from PV self-consumption vs export spread (~12 ct/kWh at 25/37 ct), minus battery round-trip losses — **no import-timing arbitrage**
  - [ ] Tools: `diag_single_window.py`, window snapshots (`backtesting_window_snapshots.jsonl`), optional `scripts/analyze_benchmark_window.py`
    **Phase 4 — Sanity table (one month)**
  - [ ] `fixed_no_pv` / `fixed_no_battery` / `fixed_baseload_only` → Δ€ ≈ 0 expected
  - [ ] Document answer: optimization potential with flat import = small, bounded; negative Δ€ with matched kWh may be legitimate
    **Phase 5 — Outcomes**
  - Consumption mismatch → bugfix + regression
  - Reference tariff mismatch → pass resolved scenario tariffs into reference (or per-scenario reference field)
  - Matched kWh, small negative Δ€ → close as expected; SE caption / user doc
  - Matched kWh, large negative Δ€ → export / SOC / cost-row deep dive
  - Optional UX: expose `diag_single_window` from SE deviation detail (no new dump format)
   **Existing bullets (unchanged scope):**
  - Reproduce: scenario **without EV** and **with EV** (see *Backtesting Tests* below)
  - **Multiple scenarios:** Szenarieneditor + `backtesting_scenarios.json` (greenfield currently only `live`)

**Phase C — polish (may slip to 2.+1)**

1. [ ] **Speichern** always at eye level in Hauskonfigurator (sticky top bar or duplicate save on long tabs: Hausprofil / PV / Batterien) or shortkey (Ctrl-S)

**Open findings (unchanged scope, tracked above)**

- [ ] Backtesting Tests
  - [ ] Test mit Standard-Setting (inkl. Haus Wärme / PV / Batterie)
    - Optimization delivers higher costs than baseline
  - [ ] Test ohne Haus Wärme
  - [ ] Test ohne PV
  - [ ] Test ohne Batterie
  - [ ] Test ohne PV und Batterie

- [ ] **Version 2.0 P7 — Documentation & evaluations**
  - Expand README with motivation / benefits — sensible order of use; less technical background than install/configuration hints
  - Build additional container for Windows as pure Python environment (if that makes sense) — spike vs local venv; go/no-go note
  - Evaluate running Scenario-Exploration as "web app" in Streamlit Community Cloud — secrets, no Loxone, demo feasibility



### Version 2.+1

- [ ] **P6b — Live cutover (non-silent)** *(former 2.0 P6b; first post-2.0 prod step)*
  - **Stop legacy worker**; remove silent mode on new stack (delete or set `loxone_silent_mode: false` in `local_settings.json`); restart new worker
  - Switch daily use to new stack (UI port); keep old `docker/earnie/` stopped but intact for rollback window
  - Rollback: stop new containers, start legacy compose on `docker/earnie/`, UI on 8501



### Version 2.+1 — Quality epic / post-migration cleanup

After 2.0 release: dead code, obsolete tests, and leftover patches from pre-1.26.0 data model (1.26.0 P6 removed runtime fallbacks; this epic mops up the rest)

- [ ] Evaluate option for code coverage testing and identification of deprecated code / tests (especially due to substantial data model change) / obsolete patches because of legacy data model
- [ ] Thorough code review and refactoring
- [ ] Search for deprecated and unnecessary files and remove them
- [ ] Evaluate option for automated UI testing



### Version 2.+1

- [ ] **SwimSpa case B — follow-up review historical power & Loxone separation**
  - Check whether historical SwimSpa power logs (`thermal_control.history_logs.power_csv` = `..._SwimSpa_Leistung_...csv`, source `Ernie_Swim-Spa-P_act`) also contain the **filter share** (case B). If yes: assess impact on **thermal model calibration** (`heat_loss_kw_per_k` etc.) — filter (~0.18 kW) would be misinterpreted as heating power.
  - **Fundamental question:** Should heating/filter separation happen **directly in Loxone** (separate heating power marker without filter) instead of software-side via `subtract_consumer_ids`? Advantage: consistent live **and** historical data at the source.
  - Reference: case B correction (live actual) already implemented; thermal calibration see **Thermals P1** (Swim-Spa)



### Version 2.+1

- [ ] **Thermals P1** — Isolated single-node models
  - **Follow-up (1.26.0 P0 smoke, decision #11):** legacy RC / `thermal_control` models (SwimSpa, freezer, etc.) from `flexible_consumers` — not in 1.26.0 P3b
  - **Migrate existing consumers** — move prod entries from `config.json` → `flexible_consumers[]` into `house_profiles.json` (`profiles[].consumers[]`) where they belong in the planning model; keep live Loxone/MILP bindings explicit (no duplicate Hausprofil clutter); migration script or one-time cutover doc alongside new thermal schema (follow-up to **2.0 P6a** silent migration test)
  - Variable heat paths (against infinity); replaces single-path special case in `optimizer/thermal_model.py`
  - **Freezer** (former 0.+1 Prio2) — second isolated reference model; acceptance: calibration/backtest against historical Loxone CSV logs



### Version 2.+1

- [ ] Define CSV data format for consumer annual demand (except house and EV) and provide import option (in addition to rated values). Annual profile from rated values can be compared graphically and in summary with measured profile.
- [ ] Set up debug page for Loxone communication showing read data with last update, whether data was sent to Loxone successfully (with value and timestamp — when silentmode==false)



### Version 2.+1

- [ ] **Recommendation mode smart/adaptive devices** (follow-up to recommendation mode manual devices)
  - Adaptive re runtime/energy per run; smart devices instead of manual input
  - Adaptation algo maintains `appliances[].default_power_kw` from Loxone power markers (`loxone_power_name`) — reserved so far, no live use
  - Dishwasher power possibly via Hue



### Version 2.+1

- [ ] **Debug dump phase 2 — sharpen dump formats and reproduction**
  - Goal: a debug dump should make a case **traceable and as reproducible as possible** later without searching prod files again
  - Clearly separate dump types:
    - **Chart debug dump** for UI/display bugs
    - **Prod dump archive** for domain/optimizer-related failure cases
  - Per dump type define:
    - required files
    - optional additional files
    - manifest fields / schema
  - Evaluate whether a **replay/recalculation path** from a dump should be documented or partially automated
  - Add further inputs only if proven relevant for real failure cases



### Version 2.+1 — Epics **Adaptation** & **Thermals** (architecture first)

Recommended order: **SwimSpa case B** (optional precursor) → **Thermals P1** (post-P6a migration follow-up) → **Adaptation P1 → Adaptation P2 → Adaptation P3 → Thermals P2 → Thermals P3 → Adaptation P4**

- [ ] **Adaptation P1** — Generic adaptation model (skeleton)
  - Common structure for parameter adaptation of various forecast models:
    - Reference value (target for adaptation)
    - Variable parameters (with bounds)
    - Time horizon (e.g. 24 h for PV/freezer, 1 year for swim spa/house)
    - Start parameters from `config.json`; adaptation history **separate**; correct live parameters only when needed (rhythm oriented to horizon)
  - Target models (connect later): PV yield, thermal models, solar collector



### Version 2.+1

- [ ] **Adaptation P2** — PV adaptation (new approach) — first pilot on Adaptation P1
  - Replaces sidebar PV tuning (removed with UI Sunset-2-Sunset); see `runtime/pv_accuracy_log.csv`
  - Replace or integrate old `pv_tuner` path into Adaptation P1



### Version 2.+1

- [ ] **Adaptation P3** — Adaptation algorithm (PV pilot)
  - Concrete update loop on Adaptation P2; thermal models remain **linear** (thermal adaptation only in Thermals P3)



### Version 2.+1

- [ ] **Thermals P2** — Coupled single-node models
  - House ↔ heat storage ↔ solar system
  - House parameters from energy certificate (`C:\Users\joche\Documents\Hausbau\Hausbau_Köhler_Schreyögg\Energieausweis_komplett_EFH-Köhler_Dornbirn-2014.pdf`)
  - Prepare air conditioning as thermal consumer



### Version 2.+1

- [ ] **Thermals P3** — Thermal parameter adaptation (on Adaptation P1)
  - `heat_loss_kw_per_k` and further linear model parameters; horizon per consumer (24 h / 1 year)



### Version 2.+1

- [ ] **Adaptation P4** — UI visualization adaptation algos (after Adaptation P3 and Thermals P3)



### Version 2.+1

- [ ] Generic EV model — for better reusability



### Version 2.+1

- [ ] Better consumption optimization with temperature-control devices
  - [ ] Heat pump (Prio3) — only indirect control via setpoint adjustment (after **Thermals P2**)



### Version 2.+1

- [ ] Visualization of actual consumer behavior possibly with recommendations



### Version 2.+1

- [ ] **Optional: live planning horizon switchable via** `config.json` (`planning_horizon.mode`: `fixed_24h` | `sunrise_window`)
  - **Prerequisite:** Version 2.0 P4 rename done (`sunrise_window` in schema/code/docs)
  - After 2.0 rename: live only `sunrise_window` today; backtesting already supports both modes — live branching still to implement (`main.py`, `profile_manager`, UI chart, aWATTar window)
  - Mode `fixed_24h`**:** end-SOC behavior **fixed in mode** — economically equivalent to former `battery_end_soc_equals_start: true` (start SOC at horizon end), **or** introduce hard equality constraint via existing `battery_wear` penalty that appropriately "punishes" lower end SOC (choose one variant, not both in parallel)
  - Mode `sunrise_window`**:** unchanged **SOC_min at sunrise** (hard)
  - Extend spec, live tests for both modes



### Version 2.+1 — follow-ups (low priority; confirm after 2.0)

- [ ] **Recalculation "historical day" into backtesting** (dev-only)
  - Arbitrary calendar day from `cons_data_hourly.csv` + historical prices; implementation to clarify later (replaces sidebar mode "historical day")
- [ ] **Target/actual hint rules** — category "hint" once concrete non-critical cases identified (follow-up epic target/actual; after **Debug dump phase 2**)
- [ ] **Target/actual recalculation (backtesting)** — rule set batch-wise over historical JSONL / prod dumps; statistics per category (follow-up epic target/actual; after **Debug dump phase 2**)



## Packaging & Deployment

Recommended open order: **7e** → **7g**

- [x] **7a–7d** — pyproject, bootstrap, build pipeline, Streamlit external ([container.md](docs/einrichtung/container.md))
- [ ] **7e — Prod/dev data sync** — script runtime/ + CSVs; documented dev ↔ prod workflow
- [ ] **7g — Local dev stacks (staging, from 1.25)**
  **Scope:** Additional container stacks on **local dev PC** — **not** greenfield (**1.24.c**), **not** pytest fixture configs, **not** data sync (`7e`). `config/` remains untouched on image updates.
  **Phases:** 7g-a silent (prod Loxone) → 7g-b simulated (later).
  **Not a Version 2.0 gate** — P6a (NAS silent stack) done; 7g-a remains useful post-2.0 for local staging.
  **Acceptance:** silent stack reads productive Loxone instance, does not write (`loxone_silent_mode: true`); simulated stack only after Loxone simulator.
  - [ ] **7g-a — Silent stack** (prod Loxone, deploy-safe)
    - Own compose folder: separate `config/` + `runtime/`, distinct `container_name` and UI port
    - `runtime/local_settings.json`: `loxone_silent_mode: true` — read access to **productive Loxone instance**, no writes to miniserver/Huawei/consumers
    - Prod `config.json` as template or via `ENERGY_OPTIMIZER_CONFIG_PATH`; image updates (`pull`/`up -d`) do not overwrite existing `config/`
  - [ ] **7g-b — Simulated stack** (follow-up, after Loxone simulator)
    - Own stack without real Loxone connection; fully synthetic "house" (signals, consumers, possibly backtesting fixtures)
    - Prerequisite: Loxone simulator available — leave open until then



## Reference



### Log files (review 2026-06)


| File                                   | Status                     | Action                        |
| -------------------------------------- | -------------------------- | ----------------------------- |
| `runtime/optimization_history.jsonl`   | **canonical**              | Prod history                  |
| `runtime/earnie.log`                   | **active**                 | Rotating 5×5 MB               |
| `runtime/optimizer_run_state.json`     | **active**                 | Last main run                 |
| `runtime/live_optimization_debug.json` | **active**                 | App 24h debug                 |
| `runtime/system_history_log.csv`       | **legacy, read-only**      | Archive when JSONL sufficient |
| `runtime/pv_accuracy_log.csv`          | **read active, write off** | see epic **Adaptation P2**    |
| `backtesting_log.json`                 | **dev only**               | not for prod NAS              |


