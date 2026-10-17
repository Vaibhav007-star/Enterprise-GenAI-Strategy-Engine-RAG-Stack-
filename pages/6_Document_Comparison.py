import streamlit as st
import sys
from pathlib import Path

root_path = Path(__file__).resolve().parent.parent
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from src.engine import get_engine
from src.utils.ui_helpers import render_header, render_citation_list, load_custom_css

st.set_page_config(page_title="Document Comparison | Strategy Engine", page_icon="🔄", layout="wide")
load_custom_css()

render_header(
    title="Multi-Document Strategic Comparison",
    subtitle="Side-by-side contrast of real SEC Form 10-K filings, corporate disclosures, and BCG advisory playbooks",
    badge_text="BCG Due Diligence",
    badge_type="bcg"
)

engine = get_engine()
docs = engine.document_store.get_all_documents()

if len(docs) < 2:
    st.warning("At least two documents must be indexed to perform comparative analysis.")
else:
    doc_map = {d["document_id"]: d["file_name"] for d in docs}
    doc_ids = list(doc_map.keys())

    # Quick Case Comparison Presets
    st.markdown("#### ⚡ 1-Click Executive Comparison Presets")
    col_pre1, col_pre2 = st.columns(2)
    
    preset_focus = None
    with col_pre1:
        if st.button("📊 MSFT 10-K vs AAPL 10-K (AI Strategy, Margins & Antitrust)", use_container_width=True):
            preset_focus = "AI strategy, cloud versus hardware segment margins, and geopolitical risk exposure"
    with col_pre2:
        if st.button("📑 BCG Framework vs Enterprise Q4 Review (10-20-70 Rule)", use_container_width=True):
            preset_focus = "BCG 10-20-70 transformation rule and enterprise cloud vendor risk"

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        # Find index for MSFT if available
        default_idx1 = 0
        for i, did in enumerate(doc_ids):
            if "MSFT" in doc_map[did]:
                default_idx1 = i
                break
        doc1_id = st.selectbox("Baseline Document (A):", options=doc_ids, index=default_idx1, format_func=lambda x: doc_map[x])
    with c2:
        default_idx2 = min(1, len(doc_ids)-1)
        for i, did in enumerate(doc_ids):
            if "AAPL" in doc_map[did] and i != default_idx1:
                default_idx2 = i
                break
        doc2_id = st.selectbox("Comparison Target Document (B):", options=doc_ids, index=default_idx2, format_func=lambda x: doc_map[x])

    focus_area = st.text_input(
        "Strategic Comparison Focus:",
        value=preset_focus or "Segment revenue growth, operating margins, capital expenditure, and risk factors",
        help="Specify the business domain or metrics you want to contrast between the two documents."
    )

    if st.button("⚖️ Generate Comparative Analysis Matrix", type="primary", use_container_width=True):
        if doc1_id == doc2_id:
            st.error("Please select two distinct documents for comparison.")
        else:
            with st.spinner("Extracting parallel passages, identifying divergences, and synthesizing comparative matrix..."):
                comp_result = engine.comparator.compare_documents(
                    doc_id_1=doc1_id,
                    doc_name_1=doc_map[doc1_id],
                    doc_id_2=doc2_id,
                    doc_name_2=doc_map[doc2_id],
                    focus_aspect=focus_area
                )
                st.session_state["comparison_result"] = comp_result
                st.session_state["comparison_citations"] = comp_result.citations

    st.markdown("---")
    res_col, cite_col = st.columns([7, 5])

    with res_col:
        st.markdown("#### 📋 Comparative Synthesis Report")
        if "comparison_result" in st.session_state:
            st.markdown(st.session_state["comparison_result"].answer)
        else:
            st.info("Select two documents above and click **Generate Comparative Analysis Matrix**.")

    with cite_col:
        st.markdown("#### 📂 Verified Cross-Document Evidence")
        if "comparison_citations" in st.session_state:
            render_citation_list(st.session_state["comparison_citations"])
        else:
            st.info("Source citations from both filings will appear here.")
