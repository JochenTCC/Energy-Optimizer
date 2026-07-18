"""Compact label|input rows for Streamlit form editors."""
from __future__ import annotations

from typing import Any, Sequence

import streamlit as st

DEFAULT_RATIOS: tuple[float, float] = (2.0, 3.0)
WIDE_LABEL_RATIOS: tuple[float, float] = (3.0, 5.0)


def form_row(
    label: str,
    *,
    ratios: Sequence[float] = DEFAULT_RATIOS,
) -> Any:
    """Side-by-side label|input row; returns the input column."""
    col_label, col_input = st.columns(list(ratios), vertical_alignment="center")
    col_label.markdown(label)
    return col_input


def _with_collapsed_label(kwargs: dict[str, Any]) -> dict[str, Any]:
    out = dict(kwargs)
    out["label_visibility"] = "collapsed"
    return out


def labeled_text_input(
    label: str,
    *,
    ratios: Sequence[float] = DEFAULT_RATIOS,
    **kwargs: Any,
) -> Any:
    col = form_row(label, ratios=ratios)
    return col.text_input(label, **_with_collapsed_label(kwargs))


def labeled_number_input(
    label: str,
    *,
    ratios: Sequence[float] = DEFAULT_RATIOS,
    **kwargs: Any,
) -> Any:
    col = form_row(label, ratios=ratios)
    return col.number_input(label, **_with_collapsed_label(kwargs))


def labeled_selectbox(
    label: str,
    *,
    ratios: Sequence[float] = DEFAULT_RATIOS,
    **kwargs: Any,
) -> Any:
    col = form_row(label, ratios=ratios)
    return col.selectbox(label, **_with_collapsed_label(kwargs))


def labeled_multiselect(
    label: str,
    *,
    ratios: Sequence[float] = DEFAULT_RATIOS,
    **kwargs: Any,
) -> Any:
    col = form_row(label, ratios=ratios)
    return col.multiselect(label, **_with_collapsed_label(kwargs))


def labeled_checkbox(
    label: str,
    *,
    ratios: Sequence[float] = DEFAULT_RATIOS,
    **kwargs: Any,
) -> Any:
    """Native checkbox with visible label (not the label|input column split).

    ``ratios`` is accepted for API compatibility with other ``labeled_*`` helpers
    but unused — collapsing the checkbox label left only a tiny square and made
    long labels (e.g. Gesamt-CSV) hard to see.
    """
    del ratios  # API compat only; native checkbox keeps label beside the box
    return st.checkbox(label, **kwargs)
