"""Structured editors for plant loxone_blocks and system.event_triggers."""
from __future__ import annotations

import streamlit as st

from ui.form_layout import WIDE_LABEL_RATIOS, labeled_selectbox, labeled_text_input
from ui.house_config_io import load_main_config, save_main_config
from ui.smarthome_marker_fields import LOXONE_BLOCKS_FIELDS, render_marker_text

_SIGNAL_TYPES = ("binary", "text", "analog")
_ON_CHANGE_OPTIONS = ("any", "rising", "falling")


def _normalize_triggers(raw: object) -> list[dict]:
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    for item in raw:
        if isinstance(item, dict):
            out.append(dict(item))
    return out


def render_loxone_blocks_form() -> None:
    """Edit config.json loxone_blocks as Smarthome-Merker role assignments."""
    st.subheader("Anlagen-Merker (`loxone_blocks`)")
    st.caption(
        "Rollen für Batterie, PV, Netz und Steuerbefehl. "
        "Werte = Merkernamen im Loxone Miniserver."
    )
    with st.expander("Merker bearbeiten", expanded=False):
        data = load_main_config()
        blocks = dict(data.get("loxone_blocks") or {})
        edited: dict[str, str] = {}
        for role, label in LOXONE_BLOCKS_FIELDS:
            edited[role] = render_marker_text(
                label,
                blocks.get(role, ""),
                key=f"lm_blocks_{role}",
            )
        if st.button("Anlagen-Merker speichern", key="lm_blocks_save"):
            payload = dict(data)
            payload["loxone_blocks"] = {
                role: edited.get(role, str(blocks.get(role, "")))
                for role, _label in LOXONE_BLOCKS_FIELDS
            }
            save_main_config(payload)
            st.success("Anlagen-Merker gespeichert.")
            st.rerun()


def _render_trigger_body(trigger: dict, index: int) -> dict:
    trig_id = labeled_text_input(
        "ID",
        value=str(trigger.get("id", "")),
        key=f"lm_trig_id_{index}",
        ratios=WIDE_LABEL_RATIOS,
    )
    loxone_name = render_marker_text(
        "Smarthome-Merker",
        trigger.get("loxone_name", ""),
        key=f"lm_trig_name_{index}",
    )
    signal_type = labeled_selectbox(
        "signal_type",
        options=list(_SIGNAL_TYPES),
        index=max(
            0,
            _SIGNAL_TYPES.index(str(trigger.get("signal_type", "binary")))
            if str(trigger.get("signal_type", "binary")) in _SIGNAL_TYPES
            else 0,
        ),
        key=f"lm_trig_type_{index}",
    )
    on_change = labeled_selectbox(
        "on_change",
        options=list(_ON_CHANGE_OPTIONS),
        index=max(
            0,
            _ON_CHANGE_OPTIONS.index(str(trigger.get("on_change", "any")))
            if str(trigger.get("on_change", "any")) in _ON_CHANGE_OPTIONS
            else 0,
        ),
        key=f"lm_trig_chg_{index}",
    )
    label = labeled_text_input(
        "Label",
        value=str(trigger.get("label", "")),
        key=f"lm_trig_label_{index}",
        ratios=WIDE_LABEL_RATIOS,
    )
    return {
        "id": str(trig_id).strip(),
        "loxone_name": loxone_name,
        "signal_type": signal_type,
        "on_change": on_change,
        "label": str(label).strip(),
    }


def render_event_triggers_form() -> None:
    """Edit system.event_triggers list."""
    st.subheader("Event-Trigger")
    st.caption(
        "Smarthome-Merker, deren Änderung einen außerplanmäßigen "
        "Optimierungslauf auslöst."
    )
    data = load_main_config()
    system = dict(data.get("system") or {})
    triggers = _normalize_triggers(system.get("event_triggers"))
    if "lm_triggers_draft" not in st.session_state:
        st.session_state["lm_triggers_draft"] = triggers
    draft: list[dict] = list(st.session_state["lm_triggers_draft"])

    cols_top = st.columns([1, 1, 4])
    with cols_top[0]:
        if st.button("Trigger hinzufügen", key="lm_trig_add"):
            draft.append(
                {
                    "id": f"trigger_{len(draft) + 1}",
                    "loxone_name": "",
                    "signal_type": "binary",
                    "on_change": "any",
                    "label": "",
                }
            )
            st.session_state["lm_triggers_draft"] = draft
            st.rerun()
    with cols_top[1]:
        if st.button("Aus Config laden", key="lm_trig_reload"):
            st.session_state["lm_triggers_draft"] = _normalize_triggers(
                (load_main_config().get("system") or {}).get("event_triggers")
            )
            st.rerun()

    updated: list[dict] = []
    remove_index: int | None = None
    for index, trigger in enumerate(draft):
        exp_col, remove_col = st.columns([4, 1], vertical_alignment="top")
        with remove_col:
            if st.button("Entfernen", key=f"lm_trig_rm_{index}"):
                remove_index = index
        with exp_col:
            with st.expander(
                f"Trigger {index + 1}: {trigger.get('id') or '—'}",
                expanded=False,
                key=f"lm_trig_exp_{index}",
            ):
                updated.append(_render_trigger_body(trigger, index))

    if remove_index is not None:
        del updated[remove_index]
        st.session_state["lm_triggers_draft"] = updated
        st.rerun()

    st.session_state["lm_triggers_draft"] = updated
    if st.button("Event-Trigger speichern", key="lm_trig_save"):
        cleaned = []
        for item in updated:
            if not item.get("id") or not item.get("loxone_name"):
                st.error("Jeder Trigger braucht ID und Merkername.")
                return
            row = {
                "id": item["id"],
                "loxone_name": item["loxone_name"],
                "signal_type": item["signal_type"],
                "on_change": item["on_change"],
            }
            if item.get("label"):
                row["label"] = item["label"]
            cleaned.append(row)
        payload = dict(data)
        system_out = dict(payload.get("system") or {})
        system_out["event_triggers"] = cleaned
        payload["system"] = system_out
        save_main_config(payload)
        st.session_state["lm_triggers_draft"] = cleaned
        st.success("Event-Trigger gespeichert.")
        st.rerun()


def render_marker_config_editors() -> None:
    """Plant markers + event triggers below the live debug block."""
    render_loxone_blocks_form()
    render_event_triggers_form()
