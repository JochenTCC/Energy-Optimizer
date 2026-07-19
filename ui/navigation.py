"""Seiten-Registry für die native Menüstruktur (st.navigation / st.Page).

Das Env-/Config-Gating (EARNIE_UI_MODES / ENERGY_OPTIMIZER_UI_MODES,
ui.price_forecast_page_enabled) steuert, welche Seiten registriert werden:
Betrieb (Monitor, Manuelle Geräte) braucht ``sunset2sunset``; Echtzeit-Umgebung
braucht ``live_environment``; Szenario-Explorer und Preis-Prognose (Dev) folgen
ihren Keys. Planungs-Seiten bleiben über Setup-Readiness gesteuert.

Nach Minimal-Bootstrap (Greenfield) sind bis zur vollständigen Planungs-Konfiguration
nur Hauskonfigurator und ggf. Echtzeit-Umgebung sichtbar (Szenarieneditor nach
Hausprofil). Danach wird Analyse freigeschaltet; Betrieb erst nach vollständiger
Loxone-Merker-Konfiguration und wenn ``sunset2sunset`` in EARNIE_UI_MODES steht.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ui.setup_readiness import (
    is_betrieb_unlocked,
    is_planning_ready,
    is_scenario_editor_unlocked,
    is_setup_navigation_restricted,
)

SECTION_PLANUNG = "Planung"
SECTION_ECHTZEIT = "Echtzeit-Umgebung"


@dataclass(frozen=True)
class PageSpec:
    """Beschreibt eine registrierbare Seite unabhängig von Streamlit."""

    render: Callable[[], None]
    title: str
    icon: str
    section: str
    url_path: str
    default: bool = False


def _planung_page_specs(*, house_config_default: bool) -> list[PageSpec]:
    from ui.pages import page_house_config, page_scenario_editor

    specs = [
        PageSpec(
            page_house_config.render,
            "Hauskonfigurator",
            "🏠",
            SECTION_PLANUNG,
            "house-config",
            default=house_config_default,
        ),
    ]
    if is_scenario_editor_unlocked():
        specs.append(
            PageSpec(
                page_scenario_editor.render,
                "Szenarieneditor",
                "🧪",
                SECTION_PLANUNG,
                "scenario-editor",
            )
        )
    return specs


def _echtzeit_page_specs() -> list[PageSpec]:
    from ui.pages import page_daemon, page_live_environment, page_loxone_debug

    return [
        PageSpec(
            page_live_environment.render,
            "Live-Konfiguration",
            "⚡",
            SECTION_ECHTZEIT,
            "live-environment",
        ),
        PageSpec(
            page_daemon.render,
            "Optimierer-Dienst",
            "🛠️",
            SECTION_ECHTZEIT,
            "optimizer-daemon",
        ),
        PageSpec(
            page_loxone_debug.render,
            "Loxone-Kommunikation",
            "🔗",
            SECTION_ECHTZEIT,
            "loxone-debug",
        ),
    ]


def _append_planung_and_echtzeit(
    specs: list[PageSpec],
    enabled_mode_keys: list[str],
    *,
    house_config_default: bool,
    force_echtzeit: bool = False,
) -> None:
    specs.extend(_planung_page_specs(house_config_default=house_config_default))
    if force_echtzeit or "live_environment" in enabled_mode_keys:
        specs.extend(_echtzeit_page_specs())


def _restricted_page_specs(enabled_mode_keys: list[str]) -> list[PageSpec]:
    # Onboarding always needs Live-Konfiguration / daemon / Loxone pages,
    # even when EARNIE_UI_MODES is explorer-only (no live_environment key).
    specs: list[PageSpec] = []
    _append_planung_and_echtzeit(
        specs,
        enabled_mode_keys,
        house_config_default=True,
        force_echtzeit=True,
    )
    return specs


def build_page_specs(enabled_mode_keys: list[str]) -> list[PageSpec]:
    """Liefert die zu registrierenden Seiten anhand des Modus-Gatings."""
    if is_setup_navigation_restricted():
        return _restricted_page_specs(enabled_mode_keys)

    from ui.pages import (
        page_backtesting,
        page_cockpit,
        page_consumer_analysis,
        page_devices,
        page_price_forecast,
    )

    specs: list[PageSpec] = []
    betrieb_shown = (
        is_betrieb_unlocked() and "sunset2sunset" in enabled_mode_keys
    )
    if betrieb_shown:
        specs.extend(
            [
                PageSpec(
                    page_cockpit.render,
                    "Monitor",
                    "🔋",
                    "Betrieb",
                    "cockpit",
                    default=True,
                ),
                PageSpec(
                    page_devices.render,
                    "Manuelle Geräte",
                    "🔌",
                    "Betrieb",
                    "devices",
                ),
            ]
        )

    scenario_explorer_allowed = (
        "scenario_explorer" in enabled_mode_keys and is_planning_ready()
    )
    analyse_default = not betrieb_shown
    if scenario_explorer_allowed:
        specs.append(
            PageSpec(
                page_backtesting.render,
                "Szenario-Explorer",
                "📊",
                "Analyse",
                "scenario-explorer",
                default=analyse_default,
            )
        )
        analyse_default = False
    if "price_forecast" in enabled_mode_keys:
        specs.append(
            PageSpec(
                page_price_forecast.render,
                "Preis-Prognose (Dev)",
                "💹",
                "Analyse",
                "price-forecast",
                default=analyse_default,
            )
        )
        analyse_default = False
    specs.append(
        PageSpec(
            page_consumer_analysis.render,
            "Verbraucheranalyse",
            "📈",
            "Analyse",
            "consumer-analysis",
            default=analyse_default,
        )
    )
    _append_planung_and_echtzeit(
        specs, enabled_mode_keys, house_config_default=False
    )
    return specs


def build_navigation(enabled_mode_keys: list[str]):
    """Erzeugt die st.navigation-Struktur aus den aktiven Seiten-Specs."""
    import streamlit as st

    sections: dict[str, list] = {}
    for spec in build_page_specs(enabled_mode_keys):
        page = st.Page(
            spec.render,
            title=spec.title,
            icon=spec.icon,
            url_path="" if spec.default else spec.url_path,
            default=spec.default,
        )
        sections.setdefault(spec.section, []).append(page)
    return st.navigation(sections)
