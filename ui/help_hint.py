"""Kleine Hilfe-Icons per Popover (Streamlit ≥ 1.30)."""
from __future__ import annotations

import streamlit as st

from ui.doc_links import PageDocs, get_page_docs, markdown_doc_link

_HELP_ICON = ":material/help_outline:"
_DOC_ICON = ":material/menu_book:"
_HELP_POPOVER_PREFIX = "help_hint__"
_DOC_LINK_PREFIX = "doc_link__"


def _help_popover_key(key: str) -> str:
    return f"{_HELP_POPOVER_PREFIX}{key}"


def _doc_link_key(key: str) -> str:
    return f"{_DOC_LINK_PREFIX}{key}"


def _resolve_page_docs(
    page_docs_key: str | None,
    page_docs: PageDocs | None,
) -> PageDocs | None:
    if page_docs is not None:
        return page_docs
    if page_docs_key:
        return get_page_docs(page_docs_key)
    return None


def _append_doc_links_markdown(body: str, docs: PageDocs) -> str:
    """Append secondary (and primary if only one) doc links under Dokumentation."""
    links = list(docs.secondaries)
    if not links:
        links = [docs.primary]
    else:
        # Primary is the book icon; still list it first in the popover for context.
        links = [docs.primary, *links]
    lines = [body.rstrip(), "", "**Dokumentation**"]
    for link in links:
        lines.append(f"- {markdown_doc_link(link)}")
    return "\n".join(lines)


def render_help_hint(body: str, *, key: str) -> None:
    """Zeigt ein kompaktes Hilfe-Icon — Inhalt erscheint im Popover."""
    with st.popover(
        "",
        icon=_HELP_ICON,
        type="tertiary",
        help="Hilfe anzeigen",
        key=_help_popover_key(key),
        width="content",
    ):
        st.markdown(body)


def render_doc_link_button(docs: PageDocs, *, key: str) -> None:
    """Book icon that opens the primary documentation URL."""
    st.link_button(
        "",
        docs.primary.url,
        icon=_DOC_ICON,
        type="tertiary",
        help=docs.primary.label,
        key=_doc_link_key(key),
    )


def render_title_with_help(title: str, help_text: str, *, key: str) -> None:
    """Überschrift mit Hilfe-Icon in einer Zeile."""
    with st.container(horizontal=True, vertical_alignment="center", gap="small"):
        st.markdown(f"**{title}**")
        render_help_hint(help_text, key=key)


def render_page_title_with_help(
    title: str,
    help_text: str,
    *,
    key: str,
    page_docs_key: str | None = None,
    page_docs: PageDocs | None = None,
) -> None:
    """Seiten-Titel mit Hilfe-Icon und optionalem Dokumentations-Link."""
    docs = _resolve_page_docs(page_docs_key, page_docs)
    popover_body = help_text
    if docs is not None:
        popover_body = _append_doc_links_markdown(help_text, docs)
    with st.container(horizontal=True, vertical_alignment="bottom", gap="small"):
        st.title(title)
        render_help_hint(popover_body, key=key)
        if docs is not None:
            render_doc_link_button(docs, key=key)


def render_status_with_help(
    message: str,
    help_text: str,
    *,
    key: str,
    prominent: bool = False,
) -> None:
    """Statuszeile sichtbar, Erklärung im Hilfe-Popover."""
    with st.container(horizontal=True, vertical_alignment="center", gap="small"):
        if prominent:
            st.info(message)
        else:
            st.caption(message)
        render_help_hint(help_text, key=key)
