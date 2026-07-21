"""Globale Streamlit-Styles."""
from __future__ import annotations

import streamlit as st


def inject_compact_top_layout_css() -> None:
    """Reduce Streamlit's default top padding so content starts nearer the toolbar."""
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def inject_compact_numeric_css() -> None:
    """Kleinere Schrift für Metrik-Zahlen und Tabellen; Number-Input ohne ±-Stepper."""
    st.markdown(
        """
        <style>
        [data-testid="stMetricValue"] {
            font-size: 0.95rem;
        }
        [data-testid="stMetricLabel"] {
            font-size: 0.75rem;
        }
        [data-testid="stMetricDelta"] {
            font-size: 0.7rem;
        }
        div[data-testid="stDataFrame"] div[data-testid="stTable"] {
            font-size: 0.8rem;
        }
        /* Hide Streamlit number_input increment/decrement buttons */
        [data-testid="stNumberInput"] button {
            display: none !important;
        }
        [data-testid="stNumberInput"] [data-baseweb="button-group"] {
            display: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def inject_help_hint_css() -> None:
    """Kompakte Hilfe-Popover (Material-Icon, tertiary)."""
    st.markdown(
        """
        <style>
        div[class*="st-key-help_hint__"] button,
        div.st-key-s2_nav_date_popover button {
            min-height: 1.25rem;
            height: 1.25rem;
            padding: 0 0.1rem;
            font-size: 0.9rem;
            line-height: 1;
        }
        div[class*="st-key-help_hint__"] [data-testid="stIconMaterial"],
        div.st-key-s2_nav_date_popover [data-testid="stIconMaterial"] {
            font-size: 0.95rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def inject_single_file_uploader_css() -> None:
    """Hide Streamlit file_uploader '+' (Add files) — app only uses single-file CSV."""
    st.markdown(
        """
        <style>
        /* Streamlit 1.58+ shows "Add files" even when accept_multiple_files=False */
        [data-testid="stFileUploader"] button[aria-label="Add files"] {
            display: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def inject_checkbox_highlight_css() -> None:
    """Subtle grey background on checkboxes so they stand out in dense forms."""
    st.markdown(
        """
        <style>
        [data-testid="stCheckbox"] {
            background-color: rgba(120, 120, 120, 0.14);
            border-radius: 0.4rem;
            padding: 0.35rem 0.55rem;
            margin-bottom: 0.15rem;
        }
        .stApp[data-theme="dark"] [data-testid="stCheckbox"] {
            background-color: rgba(180, 180, 180, 0.16);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
