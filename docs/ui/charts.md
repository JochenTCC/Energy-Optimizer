# Charts & Panels

Gilt für den Produktiv-Modus **Sunset-2-Sunset** (`ui/simulation_results.py`, `ui/charts.py`, `ui/live_mode.py`). Modus-Übersicht: [Betriebsmodi](betriebsmodi.md). Der Modus **Backtesting** nutzt teils dieselben Chart-Komponenten, eigene Kosten- und Monatscharts.

## Seitenaufbau (Sunset-2-Sunset)

| Bereich | Inhalt |
|---------|--------|
| Kopf | Seitentitel, **?** mit Modus-Scope (Sunset-2-Sunset / Backtesting) |
| Sidebar | **Version** (Caption oben), Navigation, Betriebsparameter (PV, Batterie, Runtime) |
| Charts | Chart 1 → Navigation ←/→ → Chart 2 |
| Darunter | Simulations-Tabelle, Energievergleich (Expander) |
| Sankey | Live-Energiefluss (Loxone) |
| Footer | Trennlinie → **Datenbasis** (Expander, Log-Pfad) → Optimierungs-Takt / Countdown |

Bei Wartezeit auf **main.py**: blauer Sync-Hinweis **über** den Charts (Countdown + **?**); im Footer zusätzlich **?** beim nächsten main.py-Takt.

## Chart 1: Leistung, SoC & Preis

**Überschrift:** Segment-Label (z. B. „SA₀→SA₁ (Live) · Datumsbereich“) mit **?** (Hintergrundzonen grau/neutral/grün, Navigation).

**Linke Y-Achse (kW):**

| Spur | Darstellung | Bedeutung |
|------|-------------|-----------|
| PV | Gelbe Linie | PV-Prognose / Log-Ist |
| Energiebilanz | Rauf/Runter-Balken (gestapelt) | **↑ kräftig** PV (gelb), Netzbezug (blau); **↓ kräftig** Grundlast (braun), Flex; **gedämpft** Batterie→Last grün, Netz→Batterie cyan, PV→Batterie gelb-grün, PV→Netz blassgelb — Up- und Down-Säule gleich hoch |

### Rauf/Runter-Algorithmus (Wasserfall)

Pro Slot werden Leistungen aus den Chart-Feldern auf Flüsse verteilt (`ui/flow_balance_allocate.py`):

```
PV-Rest  := PV − min(PV, Last)
Last-Rest nach PV-Deckung
Netz     → min(Netzbezug, Last-Rest)
Entladen → min(Batterie-Entladen, verbleibende Last)
Laden    ← min(Laden, PV-Rest); PV-Rest reduzieren
Einspeisung (PV) ← min(Einspeisung, PV-Rest)
Einspeisung (Batterie) ← Rest der Einspeisung (≤ Entlade-Rest)
Entladen → Last ← verbleibende Entladung
```

**Sonderfälle:** `Netzbezug` und `Geplante Batterie-Aktion` sind vorzeichenkodiert (Bezug/Laden positiv, Einspeisung/Entladen negativ). Fehlt eine explizite Einspeisung in der Zeile, wird PV-Überschuss (`offset_kw > 0`) als gedämpfte PV-Einspeisung gezeichnet. **Grauer Bereich (Produktiv-Log):** PV, Last, Netz, Batterieflüsse und **Flex-Verbraucher** nutzen Ist-Werte aus `consumption_snapshot` / `flex_live_kw` — die Aufteilung Laden/Einspeisung leitet sich aus gemessener Batterieleistung (`Ist Batterie-Leistung (kW)`) ab, nicht aus `battery_plan_kw`. **MILP/neutral/grün:** geplanter Batteriewert; am oberen/unteren SoC-Limit wird geplanter Lade-/Entladeanteil nicht gezeichnet, Überschuss erscheint als PV-Einspeisung bzw. Netzbezug. Im neutralen MILP-Bereich wird `Netzbezug` nach Live-Overlay aus Last, Flex, PV und Batterie neu abgeleitet.

| Segment (Chart) | Farbe gedämpft | Bedeutung |
|-----------------|----------------|-----------|
| `battery_charge_pv` | Gelb-Grün | Laden aus PV-Rest |
| `battery_charge_grid` | Cyan | Laden aus Netz |
| `export_pv` | Blassgelb | PV direkt ins Netz |
| `export_battery` | Cyan | Einspeisung aus Entladung (Batterie→Netz) |
| `battery_discharge_load` | Grün | Entladen in die Last (0-Bilanz) |

**Flexible Verbraucher** (gestapelte Down-Segmente): Farbe aus fester **8er-Palette** in `ui/chart_colors.py` (`CONSUMER_PALETTE`, Hue **260→40**, S≈90, L≈50). In `config.json` je Verbraucher **`chart_color_index`** (0–7), nicht mehr freies Hex. Auflösung zentral über `consumer_chart_color()` — Chart 1 und Sankey nutzen dieselben Vollfarben.

**Zonenabhängige Sättigung (nur Chart-1-Flex-Balken):** Grauer Bereich (Vergangenheit) volle Palette-Sättigung; neutraler Bereich (laufender Plan) und grüner Bereich (Preis-Prognose) gemeinsam gedämpft (`CONSUMER_CHART_SATURATION_MUTED`, derzeit 0,6). Slot → Zone über `chart_zone_kind_for_slot_start()` / `UiChartZones`; Legende bleibt in Vollfarbe (`visible='legendonly'`). Sankey unverändert volle Sättigung.

**Rechte Y-Achse (0–100, skaliert):**

| Spur | Darstellung | Bedeutung |
|------|-------------|-----------|
| SoC (optimiert) | Grüne Linie (`_HSL_SOC` in `ui/chart_colors.py`) | Simulierter Batterie-SOC |
| SoC BL Ziel | Dieselbe Farbe, gestrichelt | Referenz-SOC (Baseline) |
| Preis (rot) | Strompreis skaliert | Hover: Cent/kWh |

**Hintergrundzonen** (Details im **?** der Chart-1-Überschrift): grau = Vergangenheit (Log), neutral = laufende Stunde, grün = extrapolierte Preise bis Fensterrand.

Vertikale Marker **SA₀**, **SA₁**, **SA₂**; **Jetzt** nur im Live-Segment SA₀→SA₁.

**Soll/Ist-Icons** im grauen Log-Bereich (nur Slots mit echtem Produktiv-Eintrag, `slot_quality == present`):

| Symbol | Kategorie | Farbe | Bedeutung |
|--------|-----------|-------|-----------|
| ▲ | Hinweis | gelb | Unkritische Abweichung (z. B. Wärmepumpe: Freigabe ohne Anlauf) |
| ◆ | Warnung | orange | Erwartete Abweichung — Loxone handelt bewusst anders |
| ⬡ | Fehler | rot | Anweisung von Ernie nicht befolgt |

Marker liegen oberhalb der Chart-Fläche; **Hover** zeigt Kategorie-Label und Regeltext. Mehrere Icons pro Slot möglich (verschiedene Scopes, z. B. Batterie + E-Auto).

**Regelwerk:** `config/deviation_rules.json` (Schema: `deviation_rules.schema.json`). Pflegehinweis: [Spec Soll-Ist §5.3](../spec/soll-ist-abweichung.md).

**Aktive Regeln (Stand Epic-Abschluss):**

| Regel-ID | Scope | Kategorie |
|----------|-------|-----------|
| `swimspa_thermal_band_ok` | swimspa | Warnung |
| `eauto_pv_follow_missing` | eauto | Fehler |
| `eauto_should_charge` | eauto | Fehler |
| `battery_forced_discharge_missing` | battery | Fehler |
| `battery_forced_charge_missing` | battery | Fehler |
| `waermepumpe_enable_no_start` | waermepumpe | Hinweis |
| `swimspa_filter_should_run_missing` | swimspa_filter | Fehler |
| `swimspa_filter_runs_unexpectedly` | swimspa_filter | Fehler |
| `swimspa_filter_over_nominal` | swimspa_filter | Warnung |

**Entwickler-Test:** VS Code Launch **Streamlit app.py (Deviation-Test)** — seedet fiktives Log (`scripts/seed_deviation_test_log.py`) in lokales `runtime/` und startet Streamlit. Manuell: `python -m scripts.seed_deviation_test_log --force`.

**Rauf/Runter-Balken (Szenarien A–H):** Launch **Streamlit app.py (Flow-Balance-Test)** (`scripts/seed_flow_balance_test_log.py`) oder HTML-Vorschau: `python -m scripts.export_flow_balance_chart_html --open` → `runtime/flow_balance_preview.html`.

## Navigation zwischen Chart 1 und Chart 2

| Steuerung | Verhalten |
|-----------|-----------|
| ← Zurück | Weitere SA-Zyklen zurück im Produktiv-Log |
| Vor → | SA₀→SA₁ ↔ SA₁→SA₂ bzw. einen Zyklus Richtung Live |

Kompakte Buttons in einer Zeile **ohne** Fließtext dazwischen (mobil-tauglich).

## Chart 2: Kumulierte Kosten & Verbrauch

**Überschrift** mit **?** (Ist vs. Prognose, orange Lücken) — im S-2-Split-Modus getrennte Kurven:

| Bereich | Kurven |
|---------|--------|
| Grau (Log) | **Ist bisher** — kumuliert aus Produktiv-Log |
| Neutral/Grün | **Prognose** — BL Ziel / optimiert ab Log-Grenze (ohne Anschluss an Ist) |

Fehlende Log-Slots: orange Markierung, Lücken in Ist-Kurven.

Kennzahlen **BL Ziel**, **Optimiert**, **Ersparnis** beziehen sich auf den Horizont **Jetzt → SA₂** (nicht nur das sichtbare Chart-Segment). Linienfarben: `_HSL_COST_*` in `ui/chart_colors.py`.

## Expander: Simulations-Details

Rohdaten-Tabelle aller Slots im sichtbaren S-2-Fenster (15-min Log + MILP); Spalte **Datenquelle**; orange Zeilen = fehlende Log-Einträge. Erklär-Markdown bleibt im Expander.

## Expander: Energievergleich Baseline vs. Optimierung

Tabelle je flexiblem Verbraucher über Horizont Jetzt→SA₂:

- **BL Profil**, **BL Ziel**, **Optimierung** (kWh)

## Energiefluss (Live-Sankey)

Sankey aus **aktuellen Loxone-Leistungswerten**; Produktiv-Overlay aus `runtime/optimizer_run_state.json` (Soll vs. Ist an Batterie/Flex). Aktualisierung ca. alle 10 Sekunden. Flex-Knotenfarben: dieselbe **`chart_color_index`**-Palette wie Chart 1 (`consumer_chart_color`).

## Footer

| Element | Inhalt |
|---------|--------|
| **Datenbasis** | Expander: eingeklappt Produktiv-Log-Pfad; ausgeklappt Runtime, Merge-Pfad, Flex-Soll |
| **Optimierungs-Takt** | Viertelstunden; letzter Lauf main.py/App |
| **Nächster main.py-Takt** | Countdown + **?** (Sync-Erklärung) |

## Backtesting

Eigene Charts und Monatsauswertung aus `backtesting_log.json` — ohne S-2-Navigation und ohne Produktiv-Log-Merge.
