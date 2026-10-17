import streamlit as st
import sys
import time
import datetime
from pathlib import Path

root_path = Path(__file__).resolve().parent.parent
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from src.engine import get_engine
from src.utils.ui_helpers import render_header, render_citation_list, load_custom_css

st.set_page_config(page_title="Knowledge Assistant | Strategy Engine", page_icon="💬", layout="wide")
load_custom_css()

render_header(
    title="Enterprise Knowledge Assistant",
    subtitle="Strategic C-suite intelligence powered by real SEC Form 10-K filings and BCG advisory frameworks",
    badge_text="BCG Strategy Edition",
    badge_type="bcg"
)

engine = get_engine()
docs = engine.document_store.get_all_documents()

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "latest_citations" not in st.session_state:
    st.session_state.latest_citations = []
if "latest_diagnostics" not in st.session_state:
    st.session_state.latest_diagnostics = {}

# Sidebar Controls & Strategic Options
st.sidebar.markdown("### 🏛️ Strategic Advisory Persona")
persona = st.sidebar.selectbox(
    "Advisory Analytical Lens:",
    options=[
        "BCG Senior Partner (MECE & Value at Stake)",
        "Private Equity / Due Diligence (EBITDA & Downside)",
        "Technical Architect (RAG Benchmarks & Latency)"
    ],
    help="Select the analytical persona to customize the structure and depth of the generated response."
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎛️ Knowledge Base Scoping")

# Multi-select document filter
doc_options = {d["document_id"]: d["file_name"] for d in docs}
selected_doc_ids = st.sidebar.multiselect(
    "Filter by Real Enterprise Filing:",
    options=list(doc_options.keys()),
    format_func=lambda x: doc_options.get(x, x),
    help="Restrict retrieval to specific SEC filings or strategy playbooks."
)

# Retrieval parameters
use_hybrid = st.sidebar.checkbox("Enable Hybrid BM25 Search", value=True)
top_k = st.sidebar.slider("Top-K Retrieved Evidence Passages", min_value=2, max_value=12, value=6)
use_reranker = st.sidebar.checkbox("Enable Cross-Encoder Reranker", value=False)

if st.sidebar.button("🧹 Clear Consultation Session", use_container_width=True):
    st.session_state.messages = []
    st.session_state.latest_citations = []
    st.session_state.latest_diagnostics = {}
    st.rerun()

# Layout: Main Area (7 cols) + Evidence & Strategic Metrics (5 cols)
main_col, evidence_col = st.columns([7, 5])

with main_col:
    st.markdown("#### 🎯 Strategic Consultation Workflow")

    # High-impact BCG Interview Case Prompts
    st.markdown("**1-Click Real Enterprise Case Prompts:**")
    prompt_rows = [
        ("Compare Microsoft vs Apple AI Strategy and Cloud Margins from their FY2024 10-K Filings", "MSFT vs AAPL 10-K"),
        ("What are Microsoft's top risk factors in Item 1A regarding AI regulatory scrutiny and GPUs?", "MSFT AI Risks (Item 1A)"),
        ("According to the BCG Enterprise AI Strategy report, what is the 10-20-70 transformation rule?", "BCG 10-20-70 Playbook"),
        ("Evaluate Apple's EU Digital Markets Act (DMA) regulatory antitrust exposure and App Store impact", "AAPL EU DMA Antitrust")
    ]

    cols_p = st.columns(2)
    selected_suggestion = None
    for idx, (p_text, p_label) in enumerate(prompt_rows):
        with cols_p[idx % 2]:
            if st.button(f"📌 {p_label}", key=f"sugg_{idx}", help=p_text, use_container_width=True):
                selected_suggestion = p_text

    st.markdown("---")

    # Display chat conversation
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # User Input Handling
    user_query = st.chat_input("Enter strategic question across SEC 10-Ks, P&L reports, and BCG frameworks...")
    query_to_process = user_query or selected_suggestion

    if query_to_process:
        # Add user query to conversation
        st.session_state.messages.append({"role": "user", "content": query_to_process})
        with st.chat_message("user"):
            st.markdown(query_to_process)

        # Generate Grounded Response with Persona Directives
        with st.chat_message("assistant"):
            with st.spinner("Synthesizing evidence across SEC 10-K filings and strategy matrices..."):
                start_t = time.perf_counter()

                # Add persona custom prompt
                if "BCG Senior Partner" in persona:
                    custom_prompt = (
                        "Adopt the persona of a BCG Senior Strategy Partner. Structure the response using the Pyramidal Principle:\n"
                        "1. EXECUTIVE STRATEGY RECOMMENDATION (Top-down direct answer)\n"
                        "2. QUANTITATIVE PILLARS & FINANCIAL EVIDENCE (Audited numbers with [SOURCE X] citations)\n"
                        "3. VALUE CREATION LEVERS (Identified strategic upside)\n"
                        "4. DOWNSIDE RISK & MITIGATION FRAMEWORK (Regulatory, geopolitical, operational)\n"
                        "Ensure the answer is Mutually Exclusive and Collectively Exhaustive (MECE)."
                    )
                elif "Private Equity" in persona:
                    custom_prompt = (
                        "Adopt the persona of an M&A / Private Equity Due Diligence Principal:\n"
                        "1. INVESTMENT THESIS & CORE CONCLUSION\n"
                        "2. REVENUE RECURRENCE & SEGMENT MARGIN QUALITY (Audited 10-K data with [SOURCE X])\n"
                        "3. CAPEX INTENSITY & FREE CASH FLOW CONVERSION\n"
                        "4. DOWNSIDE VULNERABILITIES & REGULATORY EXPOSURE\n"
                    )
                else:
                    custom_prompt = (
                        "Focus on technical accuracy, citation precision, token economy, and specific page/item references."
                    )

                # 1. Retrieve hybrid candidates
                retrieval_output = engine.retriever.retrieve(
                    query=query_to_process,
                    top_k=top_k,
                    use_hybrid=use_hybrid,
                    use_reranker=use_reranker,
                    filter_document_ids=selected_doc_ids if selected_doc_ids else None,
                    expand_parent_context=True
                )
                retrieved_chunks = retrieval_output["results"]

                # 2. Generate Grounded Answer
                grounded_response = engine.generator.generate_answer(
                    query=query_to_process,
                    retrieved_chunks=retrieved_chunks,
                    conversation_context=st.session_state.messages[:-1],
                    custom_instructions=custom_prompt
                )
                elapsed_ms = round((time.perf_counter() - start_t) * 1000.0, 1)

                st.markdown(grounded_response.answer)

                # Persist in session state
                st.session_state.messages.append({"role": "assistant", "content": grounded_response.answer})
                st.session_state.latest_citations = grounded_response.citations
                st.session_state.latest_diagnostics = {
                    **retrieval_output["diagnostics"],
                    **grounded_response.diagnostics,
                    "persona": persona,
                    "total_pipeline_time_ms": elapsed_ms
                }

                # Log to DocumentStore history
                engine.document_store.log_query({
                    "timestamp": datetime.datetime.now().isoformat(),
                    "question": query_to_process,
                    "answer_preview": grounded_response.answer[:120],
                    "citations_count": len(grounded_response.citations),
                    "sufficient_evidence": grounded_response.has_sufficient_evidence,
                    "latency_ms": elapsed_ms
                })

with evidence_col:
    st.markdown("#### 📂 SEC 10-K Traceability & Citations")

    if st.session_state.latest_citations:
        render_citation_list(st.session_state.latest_citations)
    else:
        st.info("Source citations and extracted 10-K passages will dynamically render here.")

    # Strategic Metadata & Telemetry Box
    with st.expander("📊 Executive Telemetry & Retrieval Weights"):
        if st.session_state.latest_diagnostics:
            diag = st.session_state.latest_diagnostics
            st.markdown(f"**Applied Strategy Lens:** `{diag.get('persona', persona)}`")
            st.markdown(f"**Total Query Latency:** `{diag.get('total_pipeline_time_ms', 0)} ms`")
            st.markdown(f"**Vector Candidates:** `{diag.get('vector_candidates_count', 0)}`")
            st.markdown(f"**BM25 Candidates:** `{diag.get('bm25_candidates_count', 0)}`")
            st.markdown(f"**Reciprocal Rank Fusion:** `{diag.get('hybrid_fused_count', 0)} merged chunks`")
            st.markdown(f"**LLM Backend Engine:** `{diag.get('llm_client', 'GroundedSynthesizer')}`")
            
            if diag.get("vector_results"):
                st.markdown("**Top Dense Semantic Vector Matches:**")
                for vr in diag["vector_results"][:3]:
                    st.caption(f"- `{vr['doc']}` (Score: {vr['score']:.3f})")
        else:
            st.caption("Telemetry will be recorded on query execution.")
