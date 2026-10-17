import streamlit as st
import sys
from pathlib import Path
import plotly.express as px
import pandas as pd

root_path = Path(__file__).resolve().parent.parent
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from src.engine import get_engine
from src.utils.ui_helpers import render_header, render_metric_card, load_custom_css

st.set_page_config(page_title="Executive Dashboard | Strategy Engine", page_icon="📈", layout="wide")
load_custom_css()

render_header(
    title="Executive Dashboard",
    subtitle="High-level operational metrics, knowledge base health, query latency, and document coverage",
    badge_text="Live Telemetry",
    badge_type="online"
)

engine = get_engine()
docs = engine.document_store.get_all_documents()
stats = engine.vector_store.get_collection_stats()
history = engine.document_store.get_query_history(limit=50)

# Metrics Grid
m1, m2, m3, m4 = st.columns(4)
with m1:
    render_metric_card("Total Indexed Documents", str(len(docs)))
with m2:
    render_metric_card("Vector Store Chunks", str(stats.get("total_chunks", 0)))
with m3:
    avg_latency = (
        round(sum(h.get("latency_ms", 0) for h in history) / len(history), 1)
        if history else 0.0
    )
    render_metric_card("Avg Query Latency", f"{avg_latency} ms" if avg_latency > 0 else "N/A")
with m4:
    total_queries = len(engine.document_store.query_history)
    render_metric_card("Historical Queries", str(total_queries))

st.markdown("---")

# Visual Analytics Section
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    st.markdown("#### Document Formats Breakdown")
    if docs:
        format_counts = {}
        for d in docs:
            fmt = d.get("file_type", "unknown").upper()
            format_counts[fmt] = format_counts.get(fmt, 0) + 1
        
        df_formats = pd.DataFrame(list(format_counts.items()), columns=["Format", "Count"])
        fig_pie = px.pie(
            df_formats,
            names="Format",
            values="Count",
            color_discrete_sequence=px.colors.sequential.Teal,
            hole=0.45
        )
        fig_pie.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#94a3b8"),
            margin=dict(t=20, b=20, l=20, r=20)
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("No documents indexed yet to display format distributions.")

with col_chart2:
    st.markdown("#### Query Latency Trends (ms)")
    if history:
        latencies = [
            {"Query #": idx + 1, "Latency (ms)": h.get("latency_ms", 150)}
            for idx, h in enumerate(reversed(history[:15]))
        ]
        df_lat = pd.DataFrame(latencies)
        fig_lat = px.line(
            df_lat,
            x="Query #",
            y="Latency (ms)",
            markers=True,
            line_shape="spline",
            color_discrete_sequence=["#38bdf8"]
        )
        fig_lat.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#94a3b8"),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.08)"),
            margin=dict(t=20, b=20, l=20, r=20)
        )
        st.plotly_chart(fig_lat, use_container_width=True)
    else:
        st.info("Run your first query in Knowledge Assistant to display response latency curves.")

# Recent Query Log Table
st.markdown("---")
st.markdown("#### 🔍 Recent Query Execution Log")

if history:
    history_records = []
    for h in history[:10]:
        history_records.append({
            "Timestamp": h.get("timestamp", "")[:19],
            "Question": h.get("question", ""),
            "Citations Found": h.get("citations_count", 0),
            "Sufficient Evidence": "✅ Yes" if h.get("sufficient_evidence", True) else "⚠️ Incomplete",
            "Latency (ms)": h.get("latency_ms", "N/A")
        })
    st.dataframe(pd.DataFrame(history_records), use_container_width=True, hide_index=True)
else:
    st.info("No query logs recorded yet. Query logs will dynamically appear as questions are processed.")
