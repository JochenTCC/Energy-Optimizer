# earnie_env_se_m2

M2 SE matrix cell as a full env: `use_profile_csv` on for `wp_heating`, `ev`, `swimspa`.
Scenarios: **Live only** (full set backed up as `config/backtesting_scenarios.full_backup.json`).

## Start Streamlit on this env

Stop any Streamlit still bound to `earnie_env`. PowerShell (from repo root):

```powershell
Remove-Item Env:EARNIE_HOUSE_PROFILES_PATH -ErrorAction SilentlyContinue
Remove-Item Env:ENERGY_OPTIMIZER_HOUSE_PROFILES_PATH -ErrorAction SilentlyContinue
Remove-Item Env:EARNIE_BACKTESTING_SCENARIOS_PATH -ErrorAction SilentlyContinue
$env:EARNIE_ENV_PATH = (Resolve-Path 'earnie_env_se_m2').Path
$env:ENERGY_OPTIMIZER_ENV_PATH = $env:EARNIE_ENV_PATH
.venv\Scripts\python.exe -m scripts.run_streamlit
```

Then open **Szenario-Explorer → Analyse** (backtesting charts). Results: `runtime/backtesting_log.json` (full year 2025, Live only, M2 CSV).

Re-run SE:

```powershell
$env:EARNIE_ENV_PATH = (Resolve-Path 'earnie_env_se_m2').Path
.venv\Scripts\python.exe -m scripts.run_se_m2_year --year 2025
```

Do **not** leave `EARNIE_HOUSE_PROFILES_PATH` pointing at `earnie_env/runtime/se_calc_test/cells/…` (that forced the first bad M0-like run).
