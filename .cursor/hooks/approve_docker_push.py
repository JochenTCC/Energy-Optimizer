#!/usr/bin/env python3
"""Cursor hook: docker push erfordert explizite User-Bestätigung."""
from __future__ import annotations

import json
import sys


def main() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        print(json.dumps({"permission": "allow"}))
        return 0

    command = payload.get("command") or ""
    if "docker push" in command.lower():
        print(
            json.dumps(
                {
                    "permission": "ask",
                    "user_message": (
                        "Docker-Image nach ghcr.io pushen? "
                        "Nur bestätigen, wenn Phase 2 des Session-Abschlusses gewollt ist."
                    ),
                    "agent_message": (
                        "Session-Abschluss Phase 2: docker push wurde angefordert. "
                        "User-Bestätigung abwarten."
                    ),
                },
                ensure_ascii=False,
            )
        )
        return 0

    print(json.dumps({"permission": "allow"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
