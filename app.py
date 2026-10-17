import streamlit as st
from pathlib import Path
import sys

root_path = Path(__file__).resolve().parent
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from src.engine import get_engine
from src.utils.ui_helpers import render_header, render_metric_card, load_custom_css

st.set_page_config(
    page_title="Enterprise GenAI Strategy Engine | BCG Edition",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

load_custom_css()

# Render Hero Banner with BCG Edition badge
render_header(
    title="Enterprise GenAI Strategy Engine",
    subtitle="Transform Corporate Filings into Actionable Strategy • SEC 10-K Intelligence & BCG Advisory Stack",
    badge_text="BCG Executive Edition",
    badge_type="bcg"
)

# Engine initialization
with st.spinner("Connecting to Enterprise Knowledge Base & ChromaDB Vector Index..."):
    engine = get_engine()

# Retrieve real metrics
docs = engine.document_store.get_all_documents()
stats = engine.vector_store.get_collection_stats()
history = engine.document_store.get_query_history(limit=5)

# High-level Metrics Row
col1, col2, col3, col4 = st.columns(4)
with col1:
    render_metric_card("Real Enterprise Filings", str(len(docs)), delta=f"{len(docs)} Audited Datasets" if len(docs) > 0 else None)
with col2:
    render_metric_card("Total Indexed Chunks", str(stats.get("total_chunks", 0)))
with col3:
    render_metric_card("Strategic Queries Executed", str(len(engine.document_store.query_history)))
with col4:
    active_model = engine.settings.llm_model if engine.llm_client.is_available() else "Offline Grounded Engine"
    render_metric_card("LLM Architecture", active_model[:18])

st.markdown("---")

# Strategy Case Study Callout Banner
st.markdown("""
<div class="metric-card" style="border-left: 4px solid #00A35C; margin-bottom: 1.5rem;">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <span style="background: rgba(0, 163, 92, 0.2); color: #86efac; padding: 0.2rem 0.6rem; border-radius: 4px; font-weight: 700; font-size: 0.75rem; text-transform: uppercase;">
                BCG Interview Demo Mode
            </span>
            <h3 style="color: #ffffff; margin: 0.4rem 0 0.2rem 0;">Real-World Fortune 500 Filings & Consulting Frameworks Loaded</h3>
            <p style="color: #94a3b8; font-size: 0.95rem; margin: 0;">
                Pre-indexed with authentic <strong>SEC Form 10-K filings</strong> (Microsoft FY24, Apple FY24), multi-company financial benchmarks (MSFT, AAPL, NVDA, GOOGL, AMZN), and the <strong>BCG Generative AI Enterprise Playbook</strong> (10-20-70 transformation rule).
            </p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Quick Navigation & Feature Highlights
st.markdown("### 🎯 Strategic Enterprise Advisory Modules")

col_left, col_right = st.columns(2)

with col_left:
    st.markdown("""
    <div class="metric-card" style="margin-bottom: 1rem;">
        <h3 style="color: #4ade80; margin-top: 0;">💬 Knowledge Assistant (BCG Partner Lens)</h3>
        <p style="color: #94a3b8; font-size: 0.95rem;">
            Query SEC 10-K annual reports with Pyramidal MECE structuring, parent-child context expansion,
            and exact source line citations down to Form 10-K Item 1A risks and Item 8 financials.
        </p>
    </div>
    
    <div class="metric-card" style="margin-bottom: 1rem;">
        <h3 style="color: #38bdf8; margin-top: 0;">📊 Financial Intelligence & Valuation Lab</h3>
        <p style="color: #94a3b8; font-size: 0.95rem;">
            Interactive Tech Giants Peer Benchmarking (NVDA, MSFT, AAPL, GOOGL, AMZN), Microsoft FY24 P&L
            waterfall bridge ($245.1B to $109.4B), and an EBITDA multiple value creation simulator.
        </p>
    </div>
    
    <div class="metric-card">
        <h3 style="color: #a78bfa; margin-top: 0;">⚖️ Risk & Compliance Scanner</h3>
        <p style="color: #94a3b8; font-size: 0.95rem;">
            Audit regulatory mandates (EU AI Act, GDPR, SEC Item 1A disclosures, China supply chain concentration)
            with findings framed under strict legal and audit verification standards.
        </p>
    </div>
    """, unsafe_allow_html=True)

with col_right:
    st.markdown("""
    <div class="metric-card" style="margin-bottom: 1rem;">
        <h3 style="color: #34d399; margin-top: 0;">🔄 Multi-Document Strategic Comparison</h3>
        <p style="color: #94a3b8; font-size: 0.95rem;">
            Side-by-side contrast of Microsoft vs Apple Form 10-Ks, identifying AI monetization strategies,
            cloud margin divergence (Azure vs Services), and antitrust vulnerabilities.
        </p>
    </div>
    
    <div class="metric-card" style="margin-bottom: 1rem;">
        <h3 style="color: #f472b6; margin-top: 0;">📑 Document Library & Ingestion Vault</h3>
        <p style="color: #94a3b8; font-size: 0.95rem;">
            Drag-and-drop your own corporate documents (PDF, DOCX, CSV, XLSX, Markdown) with SHA-256
            deduplication, customizable chunking (Parent-Child, Structural, Recursive), and instant indexing.
        </p>
    </div>
    
    <div class="metric-card">
        <h3 style="color: #fbbf24; margin-top: 0;">🧪 RAG Evaluation & Telemetry</h3>
        <p style="color: #94a3b8; font-size: 0.95rem;">
            Run empirical benchmark suites testing context precision, context recall, answer faithfulness, citation
            accuracy, latency, and prompt injection defense.
        </p>
    </div>
    """, unsafe_allow_html=True)

# Active Indexed Files Registry
st.markdown("---")
st.markdown("### 🗃️ Active Real Enterprise Filings in Knowledge Base")

if docs:
    for d in docs:
        c_name, c_type, c_size, c_time = st.columns([4, 2, 2, 2])
        c_name.markdown(f"📄 **`{d['file_name']}`**")
        c_type.markdown(f"*{d['file_type'].upper()}*")
        c_size.markdown(f"{d['file_size_bytes'] / 1024:.1f} KB")
        c_time.markdown(f"{d['ingested_at'][:10]}")
else:
    st.info("Loading active files...")

# Sidebar Info
st.sidebar.markdown("### 🏛️ BCG Strategy Engine")
st.sidebar.caption("Enterprise RAG Stack • BCG Interview Edition")
st.sidebar.markdown(f"**Knowledge Base:** `{len(docs)} documents`")
st.sidebar.markdown(f"**Indexed Chunks:** `{stats.get('total_chunks', 0)} chunks`")
st.sidebar.markdown(f"**Embeddings:** `{engine.settings.embedding_model_name}`")
st.sidebar.markdown(f"**Strategy Focus:** Fortune 500 & SEC 10-K")
