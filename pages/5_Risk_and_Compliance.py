import streamlit as st
import sys
from pathlib import Path

root_path = Path(__file__).resolve().parent.parent
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from src.engine import get_engine
from src.utils.ui_helpers import render_header, render_citation_list, load_custom_css

st.set_page_config(page_title="Risk & Compliance | Strategy Engine", page_icon="⚖️", layout="wide")
load_custom_css()

render_header(
    title="Compliance & Risk Intelligence",
    subtitle="Audit enterprise policies for regulatory mandates, retention deadlines, and potential compliance gaps",
    badge_text="Audit & Governance",
    badge_type="online"
)

engine = get_engine()
docs = engine.document_store.get_all_documents()

st.markdown("""
> [!NOTE]
> **Legal Disclaimer:** Potential compliance gaps identified by the Strategy Engine are framed as 
> *findings requiring internal verification* and do not constitute formal legal counsel.
""")

col_left, col_right = st.columns([7, 5])

with col_left:
    st.markdown("#### 🔍 Regulatory & Policy Audit Scanner")
    compliance_topic = st.text_input(
        "Enter Policy Domain or Regulatory Requirement to Audit:",
        value="Data retention schedules, GDPR Right to Erasure, and vendor cloud risk",
        help="Example: GDPR Article 17, SOC 2 audit timelines, PII handling, financial record retention"
    )

    doc_options = {d["document_id"]: d["file_name"] for d in docs}
    selected_doc_ids = st.multiselect(
        "Scope Audit to Specific Documents (Optional):",
        options=list(doc_options.keys()),
        format_func=lambda x: doc_options.get(x, x)
    )

    if st.button("🛡️ Execute Compliance & Risk Audit", type="primary", use_container_width=True):
        with st.spinner("Scanning policies, extracting mandates, and identifying potential gaps..."):
            audit_report = engine.compliance_scanner.audit_risk_and_compliance(
                compliance_topic=compliance_topic,
                document_ids=selected_doc_ids if selected_doc_ids else None
            )
            st.session_state["compliance_report"] = audit_report
            st.session_state["compliance_citations"] = audit_report.citations

    if "compliance_report" in st.session_state:
        st.markdown("---")
        st.markdown(st.session_state["compliance_report"].answer)

with col_right:
    st.markdown("#### 📂 Verified Audit Evidence")
    if "compliance_citations" in st.session_state:
        render_citation_list(st.session_state["compliance_citations"])
    else:
        st.info("Execute an audit scan on the left to inspect citations and policy excerpts.")
