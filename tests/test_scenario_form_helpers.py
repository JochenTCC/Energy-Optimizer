"""Tests für ui.scenario_form_helpers."""
from __future__ import annotations

from ui.scenario_form_helpers import (
    NONE_LABEL,
    NEW_SCENARIO_OPTION,
    build_scenario_settings,
    default_label_index,
    lookup_entity_id,
    new_scenario_template,
    normalize_scenario_form_snapshot,
    options_for_entities,
    read_scenario_form_snapshot,
    resolve_scenario_id,
    scenario_form_is_dirty,
    scenario_session_scope,
    scoped_widget_key,
    store_scenario_form_baseline,
)


def test_lookup_entity_id_none_returns_empty():
    mapping = {"Label (bat)": "bat"}
    assert lookup_entity_id(mapping, None) == ""


def test_lookup_entity_id_unknown_returns_empty():
    mapping = {"Label (bat)": "bat"}
    assert lookup_entity_id(mapping, "unbekannt") == ""


def test_lookup_entity_id_resolves_label():
    mapping = {"Meine Batterie (bat1)": "bat1"}
    assert lookup_entity_id(mapping, "Meine Batterie (bat1)") == "bat1"


def test_options_empty_without_allow_none():
    labels, mapping = options_for_entities([], allow_none=False)
    assert labels == []
    assert mapping == {}


def test_options_empty_with_allow_none():
    labels, mapping = options_for_entities([], allow_none=True)
    assert labels == [NONE_LABEL]
    assert mapping[NONE_LABEL] == ""


def test_options_builds_labels_and_mapping():
    items = [{"id": "pv1", "label": "Dach"}]
    labels, mapping = options_for_entities(items)
    assert labels == ["Dach (pv1)"]
    assert mapping["Dach (pv1)"] == "pv1"


def test_default_label_index_finds_id():
    options = ["— keine —", "Batterie (bat)"]
    assert default_label_index(options, "bat") == 1


def test_default_label_index_missing_returns_zero():
    options = ["Batterie (bat)"]
    assert default_label_index(options, "missing") == 0


def test_scenario_session_scope_new_uses_placeholder():
    assert scenario_session_scope(NEW_SCENARIO_OPTION, is_new=True) == "__new__"
    assert scenario_session_scope("live", is_new=False) == "live"


def test_new_scenario_template_clones_live_settings():
    scenarios = [
        {
            "id": "live",
            "label": "Live",
            "settings": {"battery_id": "bat1", "house_profile_id": "home"},
        }
    ]
    template = new_scenario_template("live", scenarios)
    assert template["label"] == "Mein Szenario"
    assert template["settings"]["battery_id"] == "bat1"
    assert template["settings"]["house_profile_id"] == "home"


def test_new_scenario_template_without_live_uses_empty_settings():
    template = new_scenario_template("live", [])
    assert template["label"] == "Mein Szenario"
    assert template["settings"] == {}


def test_resolve_scenario_id_keeps_existing_id():
    assert (
        resolve_scenario_id(
            is_new=False,
            existing_id="live",
            label="Neue Bezeichnung",
            scenario_ids={"live", "other"},
        )
        == "live"
    )


def test_resolve_scenario_id_derives_from_label_for_new():
    assert (
        resolve_scenario_id(
            is_new=True,
            existing_id="",
            label="Ohne PV",
            scenario_ids={"live"},
        )
        == "ohne_pv"
    )


def test_resolve_scenario_id_avoids_collisions_for_new():
    assert (
        resolve_scenario_id(
            is_new=True,
            existing_id="",
            label="Live",
            scenario_ids={"live"},
        )
        == "live_2"
    )


def test_scenario_form_is_dirty_when_label_changed():
    session = {
        scoped_widget_key("live", "scenario_label"): "Geändert",
        scoped_widget_key("live", "scenario_profile"): "— keine —",
        scoped_widget_key("live", "scenario_battery"): "— keine —",
        scoped_widget_key("live", "scenario_pv"): "— keine —",
        scoped_widget_key("live", "scenario_import"): "— keine —",
        scoped_widget_key("live", "scenario_export"): "— keine —",
        scoped_widget_key("live", "scenario_netzentgelt"): 0.0,
        scoped_widget_key("live", "scenario_lat"): 48.0,
        scoped_widget_key("live", "scenario_lon"): 10.0,
        scoped_widget_key("live", "scenario_geo_override"): False,
    }
    store_scenario_form_baseline(
        session,
        "live",
        {"id": "live", "label": "Live", "settings": {}},
    )
    assert scenario_form_is_dirty(
        session,
        "live",
        profiles={},
        batteries=[],
        pv_systems=[],
        import_tariffs=[],
        export_tariffs=[],
    ) is True


def test_scenario_form_is_clean_when_matching_baseline():
    session = {
        scoped_widget_key("live", "scenario_label"): "Live",
        scoped_widget_key("live", "scenario_profile"): "— keine —",
        scoped_widget_key("live", "scenario_battery"): "— keine —",
        scoped_widget_key("live", "scenario_pv"): "— keine —",
        scoped_widget_key("live", "scenario_import"): "— keine —",
        scoped_widget_key("live", "scenario_export"): "— keine —",
        scoped_widget_key("live", "scenario_netzentgelt"): 0.0,
        scoped_widget_key("live", "scenario_lat"): 48.0,
        scoped_widget_key("live", "scenario_lon"): 10.0,
        scoped_widget_key("live", "scenario_geo_override"): False,
    }
    store_scenario_form_baseline(
        session,
        "live",
        {"id": "live", "label": "Live", "settings": {}},
    )
    assert scenario_form_is_dirty(
        session,
        "live",
        profiles={},
        batteries=[],
        pv_systems=[],
        import_tariffs=[],
        export_tariffs=[],
    ) is False


def test_read_scenario_form_snapshot_resolves_entity_ids():
    batteries = [{"id": "bat1", "label": "Speicher"}]
    session = {
        scoped_widget_key("live", "scenario_label"): "Live",
        scoped_widget_key("live", "scenario_profile"): "— keine —",
        scoped_widget_key("live", "scenario_battery"): "Speicher (bat1)",
        scoped_widget_key("live", "scenario_pv"): "— keine —",
        scoped_widget_key("live", "scenario_import"): "— keine —",
        scoped_widget_key("live", "scenario_export"): "— keine —",
        scoped_widget_key("live", "scenario_netzentgelt"): 0.0,
        scoped_widget_key("live", "scenario_lat"): 48.0,
        scoped_widget_key("live", "scenario_lon"): 10.0,
        scoped_widget_key("live", "scenario_geo_override"): False,
    }
    snapshot = read_scenario_form_snapshot(
        session,
        "live",
        profiles={},
        batteries=batteries,
        pv_systems=[],
        import_tariffs=[],
        export_tariffs=[],
    )
    assert snapshot["settings"]["battery_id"] == "bat1"


def test_build_scenario_settings_omits_zero_netzentgelt():
    settings = build_scenario_settings(
        battery_id="",
        pv_system_id="",
        import_tariff_id="imp",
        export_tariff_id="exp",
        house_profile_id="home",
        netzentgelt_cent_kwh_override=0.0,
    )
    assert "netzentgelt_cent_kwh_override" not in settings


def test_normalize_scenario_form_snapshot_keeps_label_and_settings():
    snapshot = normalize_scenario_form_snapshot(
        {"id": "variant_a", "label": "Variante A", "settings": {"battery_id": "bat1"}},
    )
    assert snapshot == {"label": "Variante A", "settings": {"battery_id": "bat1"}}
    assert "id" not in snapshot
