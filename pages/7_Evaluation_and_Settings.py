import streamlit as st
import sys
from pathlib import Path
import pandas as pd

root_path = Path(__file__).resolve().parent.parent
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from src.engine import get_engine
from src.evaluation.sample_tests import get_default_test_suite
from src.evaluation.models import TestCase
from src.utils.ui_helpers import render_header, render_metric_card, load_custom_css

st.set_page_config(page_title="Evaluation & Settings | Strategy Engine", page_icon="🧪", layout="wide")
load_custom_css()

render_header(
    title="RAG Evaluation & System Configuration",
    subtitle="Empirical retrieval benchmarking, grounding validation, and LLM provider parameters",
    badge_text="Quality Assurance",
    badge_type="online"
)

engine = get_engine()

tab_eval, tab_config = st.tabs(["🧪 Empirical Benchmark Suite", "⚙️ System Configuration"])

with tab_eval:
    st.markdown("### 📊 Benchmark Test Harness")
    st.markdown("""
    Evaluate the end-to-end RAG architecture across standard enterprise dimensions:
    - **Context Precision:** Proportion of retrieved passages directly relevant to the query.
    - **Context Recall:** Verification that required source evidence was successfully retrieved.
    - **Answer Faithfulness:** Grounding ratio validating absence of hallucinated statements.
    - **Citation Correctness:** Ratio of correctly tagged `[SOURCE X]` references.
    - **Prompt Injection Resilience:** Defense against malicious jailbreak attempts embedded in queries.
    """)

    test_suite = get_default_test_suite()

    if st.button("🚀 Run Standard Benchmark Test Suite", type="primary", use_container_width=True):
        with st.spinner("Executing 5 empirical evaluation test cases across hybrid retriever and generator..."):
            report = engine.evaluator.run_suite(test_suite)
            st.session_state["eval_report"] = report

    if "eval_report" in st.session_state:
        rep = st.session_state["eval_report"]
        st.markdown("---")
        st.markdown("#### 🎯 Benchmark Performance Scorecard")

        s1, s2, s3, s4 = st.columns(4)
        with s1:
            render_metric_card("Pass Rate", f"{rep.pass_rate_pct:.1f}%", delta=f"{rep.passed_cases}/{rep.total_cases} Passed")
        with s2:
            render_metric_card("Avg Context Precision", f"{rep.avg_context_precision * 100:.1f}%")
        with s3:
            render_metric_card("Avg Faithfulness", f"{rep.avg_faithfulness * 100:.1f}%")
        with s4:
            render_metric_card("Avg Latency", f"{rep.avg_latency_ms:.0f} ms")

        st.markdown("#### Individual Test Case Diagnostics")
        case_rows = []
        for c in rep.case_results:
            case_rows.append({
                "Test ID": c.case_id,
                "Category": c.test_category.title(),
                "Status": "✅ Pass" if c.passed else "❌ Fail",
                "Precision": f"{c.context_precision * 100:.0f}%",
                "Recall": f"{c.context_recall * 100:.0f}%",
                "Faithfulness": f"{c.faithfulness_score * 100:.0f}%",
                "Latency": f"{c.total_latency_ms:.0f} ms",
                "Notes": c.notes or "Passed verified criteria"
            })
        st.dataframe(pd.DataFrame(case_rows), use_container_width=True, hide_index=True)

with tab_config:
    st.markdown("### 🛠️ Runtime Engine Parameters")
    
    cfg_col1, cfg_col2 = st.columns(2)
    with cfg_col1:
        st.markdown("#### LLM Backend")
        provider = st.selectbox(
            "Active LLM Provider:",
            options=["ollama", "openai", "groq", "offline_grounded"],
            index=0 if engine.settings.llm_provider == "ollama" else 1
        )
        model_name = st.text_input("Model Identifier:", value=engine.settings.llm_model)
        base_url = st.text_input("Ollama Base URL:", value=engine.settings.llm_base_url)

    with cfg_col2:
        st.markdown("#### Chunking & Retrieval Parameters")
        chunk_sz = st.number_input("Default Chunk Size (characters):", value=engine.settings.default_chunk_size, step=50)
        chunk_ov = st.number_input("Default Chunk Overlap (characters):", value=engine.settings.default_chunk_overlap, step=25)
        top_k_def = st.number_input("Default Retrieval Top-K:", value=engine.settings.default_top_k, min_value=1, max_value=20)

    st.markdown("""
    > [!TIP]
    > To permanently update default settings, edit the `.env` file located in the project root directory.
    """)
