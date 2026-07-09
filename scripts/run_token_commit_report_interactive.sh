#!/bin/sh
# Interaktiver Aufruf von scripts.token_commit_report (post-commit oder manuell).
set -e

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

if [ -n "${CI:-}" ] || [ ! -t 0 ]; then
  echo "post-commit: Kein interaktives Terminal — Token-Report übersprungen."
  exit 0
fi

if [ -x ".venv/Scripts/python.exe" ]; then
  PYTHON=".venv/Scripts/python.exe"
elif [ -x ".venv/bin/python" ]; then
  PYTHON=".venv/bin/python"
else
  PYTHON="python"
fi

if ! command -v "$PYTHON" >/dev/null 2>&1 && ! [ -x "$PYTHON" ]; then
  echo "post-commit: Python nicht gefunden — Token-Report übersprungen." >&2
  exit 0
fi

DOWNLOADS="${USERPROFILE:-$HOME}/Downloads"
CURSOR_USAGE_URL="https://cursor.com/settings"

find_latest_csv() {
  ls -t "$DOWNLOADS"/usage-events-*.csv 2>/dev/null | head -1
}

open_usage_page() {
  case "$(uname -s 2>/dev/null)" in
    MINGW*|MSYS*|CYGWIN*)
      cmd.exe //c start "" "$CURSOR_USAGE_URL" >/dev/null 2>&1 || true
      ;;
    Darwin)
      open "$CURSOR_USAGE_URL" >/dev/null 2>&1 || true
      ;;
    *)
      xdg-open "$CURSOR_USAGE_URL" >/dev/null 2>&1 || true
      ;;
  esac
}

run_report() {
  csv_path="$1"
  if [ -z "$csv_path" ] || [ ! -f "$csv_path" ]; then
    echo "post-commit: Keine usage-events-*.csv in $DOWNLOADS gefunden." >&2
    return 1
  fi
  echo "post-commit: Token-Report mit $csv_path"
  "$PYTHON" -m scripts.token_commit_report --usage-csv "$csv_path" --include-head
}

printf '%s\n' \
  "" \
  "post-commit: Token-Report (Cursor Usage → Minor-Kapitel)" \
  "  [d] Neuen CSV-Export laden (Browser öffnen), dann ausführen" \
  "  [v] Neueste usage-events-*.csv aus Downloads nutzen" \
  "  [s] Überspringen" \
  "Auswahl [d/v/s]: "
IFS= read -r choice || choice="s"
choice=$(printf '%s' "$choice" | tr '[:upper:]' '[:lower:]')

case "$choice" in
  d)
    open_usage_page
    printf '%s\n' \
      "Browser: Cursor Settings → Usage → CSV exportieren nach:" \
      "  $DOWNLOADS" \
      "Dateiname: usage-events-*.csv" \
      "Enter drücken, wenn der Export gespeichert ist (oder Strg+C zum Abbrechen) ..."
    IFS= read -r _ || exit 0
    csv=$(find_latest_csv)
    run_report "$csv" || exit 0
    ;;
  v)
    csv=$(find_latest_csv)
    run_report "$csv" || exit 0
    ;;
  s|"")
    echo "post-commit: Token-Report übersprungen."
    ;;
  *)
    echo "post-commit: Ungültige Auswahl — Token-Report übersprungen." >&2
    ;;
esac

exit 0
