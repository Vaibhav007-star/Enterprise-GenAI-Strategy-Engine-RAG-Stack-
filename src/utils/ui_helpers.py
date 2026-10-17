import streamlit as st
from pathlib import Path
from typing import Dict, Any, List


def load_custom_css():
    """Inject assets/style.css into Streamlit page."""
    css_path = Path(__file__).resolve().parent.parent.parent / "assets" / "style.css"
    if css_path.exists():
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def render_header(title: str, subtitle: str, badge_text: str = "Enterprise Engine", badge_type: str = "online"):
    """Render modern hero header banner."""
    load_custom_css()
    badge_class = "badge-status-online" if badge_type == "online" else "badge-status-local"
    st.markdown(
        f"""
        <div class="header-hero">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <h1 class="header-title">{title}</h1>
                    <div class="header-subtitle">{subtitle}</div>
                </div>
                <div class="{badge_class}">
                    <span>●</span> {badge_text}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_metric_card(label: str, value: str, delta: str = None):
    """Render a styled metric card."""
    delta_html = f"<div style='font-size: 0.8rem; color: #10b981; margin-top: 0.2rem;'>▲ {delta}</div>" if delta else ""
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True
    )


def render_citation_list(citations: List[Any]):
    """Render clickable or expandable citations with verified source snippets."""
    if not citations:
        st.info("No explicit citations retrieved for this response.")
        return

    st.markdown("#### Traceable Citations & Evidence")
    for cite in citations:
        loc = []
        if getattr(cite, "page_number", None) is not None:
            loc.append(f"Page {cite.page_number}")
        if getattr(cite, "sheet_name", None):
            loc.append(f"Sheet: {cite.sheet_name}")
        if getattr(cite, "section_title", None):
            loc.append(f"Section: {cite.section_title}")
        loc_text = f" ({', '.join(loc)})" if loc else ""

        with st.expander(f"📌 [Source {cite.citation_id}] {cite.document_name}{loc_text} — Relevance: {cite.relevance_score:.3f}"):
            st.markdown(f"**Document ID:** `{cite.document_id}`")
            st.markdown("**Retrieved Evidence Passage:**")
            st.info(cite.snippet)
