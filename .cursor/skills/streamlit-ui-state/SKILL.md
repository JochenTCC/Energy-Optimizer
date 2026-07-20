---
name: streamlit-ui-state
description: >-
  Checklist for Streamlit session_state and widget freshness so editors do not
  show stale selects, labels, or form fields after add/remove/rename/navigation.
  Use when implementing or reviewing ui/** Streamlit forms, Hauskonfigurator,
  Szenarioeditor, planning PV/battery/Verbraucher selects, label_select,
  auto_persist, pending select, dual widget keys, fragments, or dialogs; or when
  the user mentions stale UI, wrong entity after save, ghost fields after delete,
  or Bezeichnung not updating in a dropdown.
---

# Streamlit UI State Checklist

Run **before coding** and again **before calling the change done**. Reuse helpers in `ui/label_select.py`, `ui/house_config_io.py`, and existing `_sync_*_session` / pending-select patterns in planning forms.

## 1. Classify the edit

| Change type | Primary risk |
|-------------|--------------|
| Add entity | Select stays on old id; new entity not editable until manual re-select |
| Remove entity | Form still shows deleted values; select points at missing id |
| Rename Bezeichnung | Closed selectbox keeps old text (`format_func` / stable-id options) |
| Persist field / CSV path | Dual keys: store updated, widget key stale (or reverse) |
| Page / tab navigation | Widget keys dropped; empty or default UI while disk is fine |
| Fragment / dialog | Wrong rerun scope; download+dismiss; widgets outside fragment |

## 2. Mandatory checks (all editor UIs)

Copy and tick:

```
Streamlit freshness:
- [ ] Add → pending select = new id, clear sync, st.rerun(); next run applies pending BEFORE selectbox
- [ ] Remove → pending select = valid fallback; clear sync/file stamp; no ghost widget values for deleted id
- [ ] Rename → options are Bezeichnung strings (label_select); align/refresh session display
- [ ] No st.session_state[widget_key] write after that widget already instantiated this run
- [ ] Scope/file/nav change reseeds via sync + *_widget_state_missing
- [ ] Same pattern considered for sibling editors (PV / battery / Verbraucher / scenario)
```

## 3. Canonical patterns in this repo

### Pending select (add / delete)

1. On mutate: set `_SESSION_SELECT_PENDING_KEY`, update file stamp, set sync key to `None`, `st.rerun()`.
2. At top of render: `_apply_pending_*()` → write select widget key, then build options / selectbox.
3. Do not rely on `index=` alone after the widget key already exists in `session_state`.

Reference: `ui/planning_pv_form.py`, `ui/planning_battery_form.py`.

### Bezeichnung selects

- Use `label_select_choices` / `align_label_select_session` / `resolve_label_select`.
- Do **not** pass stable IDs as options with `format_func` — Streamlit keeps stale closed-dropdown text.

### Session sync / page nav

Reseed when **any** of: scope changed, config file stamp changed, or scoped widget keys missing after navigation.

### Dual keys (paths, mirrors)

If a logical value has a store key and a separate widget `key`, queue an update and apply it on the next run (see `queue_csv_path_update` / `apply_csv_path_pending` in `ui/house_config_io.py`). Bump an uploader nonce when the uploader must remount.

### Fragments & dialogs

- Interactive widgets that own state: only inside their fragment.
- Dialog download + close: prefer save → `st.rerun()` → main-page download (`ui/chart_debug_capture.py` pattern).

## 4. Tests to prefer

When the change touches select/sync/pending:

- Sync reseeds when widget keys missing (see `tests/test_planning_editors.py` patterns).
- Add/remove leaves select on expected id / `— neu —`.
- Label options refresh when Bezeichnung changes (no `format_func`-only assert).

## 5. Out of scope

- Pure chart math / Plotly traces (unless fragment boundary is involved).
- Non-Streamlit CLI or optimizer core — unless it only feeds UI session keys.
