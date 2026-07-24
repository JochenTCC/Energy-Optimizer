# Loxone-Com (Debug-Seite)

Die Seite **Loxone-Com** unter **Daemon Control** zeigt den Live-Zustand aller konfigurierten Smarthome-Merker (Backend: Loxone) und die Schreibvorgänge des letzten Produktiv-Laufs von `main.py`. Zusätzlich können Sie die zentralen Anlagen-Merker (`loxone_blocks`) und Event-Trigger (`system.event_triggers`) strukturiert bearbeiten.

## Aufruf

1. Streamlit starten: `python -m scripts.run_streamlit`
2. Navigation: **Daemon Control → Loxone-Com**

Die Seite ist auch während der Einrichtung sichtbar (eingeschränkte Navigation), sobald Loxone-Zugangsdaten in `config/.env` hinterlegt sind.

## Live-Cockpit noch gesperrt (Greenfield)

Nach abgeschlossener Planungs-Konfiguration (Hauskonfigurator + Live-Szenario im Szenarienkonfigurator) erscheint **Szenario-Explorer**, aber **Live-Cockpit** (Monitor / Manuelle Geräte) bleibt bewusst ausgeblendet, solange die Smarthome-Merker für den Live-Betrieb nicht vollständig und korrekt sind.

Auf dieser Seite erscheint dann ein Hinweis. Nutzen Sie **Smarthome-Merker testen**, die Tabelle **Live-Lesen** sowie die Formulare **Anlagen-Merker** / **Event-Trigger**, um Platzhalter oder falsche Namen in `loxone_blocks` (`config.json`) und in den Verbraucher-Merkern des Hausprofils zu korrigieren. Erst danach wird der Abschnitt Live-Cockpit freigeschaltet.

## Bereiche der Seite

### Statusleiste

- **Silent-Modus aktiv:** Steuerwerte werden nicht an den Miniserver geschrieben; nur Sollwerte werden angezeigt.
- **Live-Modus:** `main.py` sendet Steuerwerte an Loxone.
- **Letzter main.py-Lauf:** Zeitstempel und Alter des letzten erfolgreichen Optimierungsdurchlaufs.

### Live-Lesen

Alle aus `config.json` abgeleiteten Eingänge werden periodisch (Standard: alle 10 Sekunden) vom Miniserver gelesen.

| Spalte | Bedeutung |
|--------|-----------|
| Label | Bezeichnung aus der Konfiguration (z. B. Batterie-SoC, Verbraucher-Leistung) |
| IO-Name | Smarthome-Merkername (Loxone) |
| Status | OK, Warnung oder Fehler |
| Detail | Rohwert oder parsebarer Wert |
| Zuletzt gelesen | Zeitpunkt des letzten Abrufs auf dieser Seite |

Mit **Smarthome-Merker testen** starten Sie eine einmalige Prüfung aller konfigurierten Merker (Ergebnis als farbige Meldungen). Die Tabelle darunter wird zusätzlich automatisch aktualisiert (Standard: alle 10 Sekunden).

Lesefehler bedeuten: Merkername falsch, Miniserver nicht erreichbar, oder Wert nicht parsebar — nicht dass `main.py` fehlgeschlagen ist.

### Live-Schreiben

Daten stammen aus `runtime/optimizer_run_state.json` des **letzten** `main.py`-Laufs.

**Live-Modus** (`runtime/local_settings.json`: `"loxone_silent_mode": false` oder Eintrag entfernt):

| Spalte | Bedeutung |
|--------|-----------|
| IO-Name | Virtueller Eingang in Loxone |
| Wert | Gesendeter numerischer Wert |
| Erfolg | Ja/Nein — HTTP-Schreibvorgang an den Miniserver |
| Gesendet um | Zeitstempel des einzelnen Schreibvorgangs |

**Silent-Modus** (`"loxone_silent_mode": true`):

- Keine Schreibbestätigungen — es wurden keine HTTP-Schreibvorgänge ausgeführt.
- Tabelle **Sollwert (nicht gesendet)** zeigt die geplanten Werte aus `loxone_sent` des letzten Laufs.

### Expander: Lese-Snapshot aus run_state

Kompakte JSON-Ansicht der beim letzten Lauf gespeicherten Aggregatwerte (SoC, Flex-Leistungen, Event-Trigger, Verbrauchs-Snapshot).

### Anlagen-Merker (`loxone_blocks`)

Kapitelüberschrift mit strukturiertem Formular (Expander **Merker bearbeiten**) für Batterie-/PV-/Netz- und Steuerbefehl-Rollen. Werte sind Miniserver-Merkernamen; Speichern schreibt `config.json` und lädt die Runtime-Konfiguration neu. Die Roh-JSON-Bearbeitung unter Konfiguration bleibt als Escape Hatch.

### Event-Trigger

Kapitelüberschrift mit Liste der Signale (je Trigger ein Expander), die außerplanmäßige Optimierungsläufe auslösen (`id`, Merkername, `signal_type`, `on_change`, `label`). Siehe auch [Loxone-Signale](../referenz/loxone-signale.md#event-trigger-systemevent_triggers).

## Silent-Modus vs. Live-Modus

| | Silent-Modus | Live-Modus |
|---|--------------|------------|
| Lesen | Immer aktiv (auch auf dieser Seite) | Immer aktiv |
| Schreiben durch `main.py` | Nein | Ja |
| Schreib-Tabelle | Nur Sollwerte | Wert + Erfolg + Zeitstempel |
| Typischer Einsatz | Migrations-Test, paralleler Legacy-Betrieb | Produktiv nach Cutover |

Silent-Modus wird in `runtime/local_settings.json` gesetzt (Priorität vor veraltetem `system.loxone_silent_mode` in `config.json`). Standard ohne Datei: **Silent-Modus an**.

## Cutover-Checkliste

Nach Deaktivierung des Silent-Modus und Neustart von `main.py`:

1. **Live-Lesen:** alle relevanten Merker Status **OK**
2. **Live-Schreiben:** alle Einträge **Erfolg = Ja**
3. **Cockpit / Sankey:** Soll-Werte passen zu Live (siehe [Charts & Panels](charts.md))

Bei Schreibfehlern: Netzwerk, Merkernamen in `config.json`, Miniserver-Logs prüfen; Details auch in `runtime/earnie.log`.

## Siehe auch

- [Loxone-Anbindung](../einrichtung/loxone-anbindung.md)
- [Loxone-Signale](../referenz/loxone-signale.md)
- [Betrieb](../einrichtung/betrieb.md) — `main.py`-Takt und Laufzeitdateien
- CLI-Alternative: `python -m scripts.verify_loxone_setup`
