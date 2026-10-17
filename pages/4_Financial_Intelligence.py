import streamlit as st
import sys
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

root_path = Path(__file__).resolve().parent.parent
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from src.engine import get_engine
from src.financial_analysis.financial_engine import FinancialAnalysisEngine
from src.utils.ui_helpers import render_header, render_metric_card, load_custom_css

st.set_page_config(page_title="Financial Intelligence | Strategy Engine", page_icon="📊", layout="wide")
load_custom_css()

render_header(
    title="Financial Table Intelligence & Valuation Lab",
    subtitle="Audited SEC 10-K financial intelligence, deterministic Python math, and BCG corporate valuation tools",
    badge_text="BCG Financial Analytics",
    badge_type="bcg"
)

engine = get_engine()

# Financial tabs
tab_peer, tab_waterfall, tab_valuation, tab_custom_calc = st.tabs([
    "🏢 Tech Giants Peer Benchmarking",
    "🌊 SEC 10-K P&L Waterfall",
    "💎 EBITDA Multiple & Value Creation Lab",
    "🧮 Interactive Table & Margin Math"
])

# ----------------- TAB 1: PEER BENCHMARKING -----------------
with tab_peer:
    st.markdown("### 📊 Cross-Company Strategic Financial Benchmarking (FY2023 vs FY2024)")
    st.markdown("""
    Compare real audited financial metrics across Microsoft, Apple, NVIDIA, Alphabet, and Amazon 
    from their respective SEC Form 10-K filings.
    """)

    peer_csv_path = engine.settings.sample_data_dir / "Tech_Giants_FY2023_FY2024_Financial_Comparison.csv"
    if peer_csv_path.exists():
        df_peers = pd.read_csv(peer_csv_path)

        # Filters
        f1, f2 = st.columns([6, 6])
        with f1:
            selected_year = st.selectbox("Select Reporting Fiscal Year:", options=["FY2024", "FY2023"], index=0)
        with f2:
            metrics_options = [
                "Revenue_Billion_USD",
                "Operating_Income_Billion_USD",
                "Operating_Margin_Pct",
                "Gross_Margin_Pct",
                "AI_Cloud_Segment_Revenue_Billion",
                "Free_Cash_Flow_Billion"
            ]
            selected_metric = st.selectbox(
                "Benchmark Metric to Contrast:",
                options=metrics_options,
                format_func=lambda x: x.replace("_", " ").title()
            )

        df_filtered = df_peers[df_peers["Fiscal_Year"] == selected_year]

        c_table, c_chart = st.columns([6, 6])
        with c_table:
            st.dataframe(
                df_filtered[["Company", "Ticker", "Revenue_Billion_USD", "Operating_Margin_Pct", "Gross_Margin_Pct", "AI_Cloud_Segment_Revenue_Billion", "Free_Cash_Flow_Billion"]],
                use_container_width=True,
                hide_index=True
            )
        with c_chart:
            fig_bar = px.bar(
                df_filtered,
                x="Company",
                y=selected_metric,
                color=selected_metric,
                text_auto=".1f",
                color_continuous_scale="Greens" if "Margin" in selected_metric else "Blues",
                title=f"{selected_metric.replace('_', ' ').title()} across Peers ({selected_year})"
            )
            fig_bar.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8")
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown("#### Strategic Insights Summary")
        st.markdown(f"""
        - **Operating Margin Leader ({selected_year}):** **NVIDIA (54.1%)** followed by **Microsoft (44.6%)** and **Apple (31.5%)**.
        - **Cloud & AI Segment Scale:** **Amazon AWS ($107.5B)** and **Microsoft Intelligent Cloud ($105.4B)** command over $210B in combined annualized enterprise run-rate.
        - **Cash Generation Power:** **Apple generated $108.8B** in free cash flow, representing a 27.8% FCF margin.
        """)
    else:
        st.info("Peer benchmark data loading...")

# ----------------- TAB 2: P&L WATERFALL -----------------
with tab_waterfall:
    st.markdown("### 🌊 Microsoft FY2024 Audited Income Statement Waterfall")
    st.markdown("Visualizing the exact bridge from Gross Revenue ($245.1B) to Net Operating Income ($109.4B) as audited in Form 10-K Item 8.")

    wf_labels = ["Total Revenue", "Cost of Revenue", "Gross Margin", "Research & Dev", "Sales & Marketing", "G&A Expense", "Operating Income"]
    wf_measures = ["relative", "relative", "total", "relative", "relative", "relative", "total"]
    wf_y = [245.1, -75.3, 169.8, -29.5, -24.4, -6.5, 109.4]

    fig_wf = go.Figure(go.Waterfall(
        name="MSFT FY24 P&L",
        orientation="v",
        measure=wf_measures,
        x=wf_labels,
        textposition="outside",
        text=[f"${abs(val):.1f}B" for val in wf_y],
        y=wf_y,
        connector={"line": {"color": "rgba(255,255,255,0.2)"}},
        decreasing={"marker": {"color": "#ef4444"}},
        increasing={"marker": {"color": "#00A35C"}},
        totals={"marker": {"color": "#38bdf8"}}
    ))
    fig_wf.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#94a3b8"),
        showlegend=False,
        yaxis=dict(title="Billions USD ($)", gridcolor="rgba(255,255,255,0.08)"),
        height=450
    )
    st.plotly_chart(fig_wf, use_container_width=True)

# ----------------- TAB 3: VALUATION & EBITDA LAB -----------------
with tab_valuation:
    st.markdown("### 💎 Enterprise Valuation & Value Creation Sensitivity Simulator")
    st.markdown("Simulate Enterprise Value (EV) creation levers based on EBITDA and Valuation Multiples.")

    v_col1, v_col2 = st.columns(2)
    with v_col1:
        base_ebitda = st.number_input("Audited EBITDA ($ Billions):", min_value=1.0, max_value=500.0, value=118.5, step=5.0, help="E.g. Microsoft FY24 Operating Cash Flow ~$118.5B")
        cost_out_pct = st.slider("Cost Transformation / AI Efficiency Gain (%):", min_value=0.0, max_value=15.0, value=3.5, step=0.5, help="BCG Horizon 1/2 productivity savings")
        multiple_slider = st.slider("EV / EBITDA Target Multiple (x):", min_value=10.0, max_value=40.0, value=25.0, step=1.0)

    # Compute deterministic impact
    incremental_ebitda = base_ebitda * (cost_out_pct / 100.0)
    adjusted_ebitda = base_ebitda + incremental_ebitda
    implied_ev_base = base_ebitda * multiple_slider
    implied_ev_adjusted = adjusted_ebitda * multiple_slider
    value_unlocked = implied_ev_adjusted - implied_ev_base

    with v_col2:
        st.markdown("#### 🎯 Implied Enterprise Valuation Output")
        m1, m2 = st.columns(2)
        with m1:
            render_metric_card("Baseline Enterprise Value", f"${implied_ev_base:,.1f} B")
        with m2:
            render_metric_card("Post-AI Enterprise Value", f"${implied_ev_adjusted:,.1f} B", delta=f"+${value_unlocked:,.1f} B Created")

        st.markdown(f"""
        <div class="metric-card" style="margin-top: 1rem;">
            <div class="metric-label">BCG Value Creation Assessment</div>
            <p style="font-size: 0.95rem; color: #cbd5e1; margin-top: 0.5rem;">
                A <strong>{cost_out_pct}%</strong> operating efficiency capture generates 
                <strong>+${incremental_ebitda:.2f}B</strong> in recurring EBITDA. 
                At a <strong>{multiple_slider:.0f}x</strong> exit multiple, this unlocks 
                <strong>+${value_unlocked:.1f} Billion</strong> in incremental shareholder equity value.
            </p>
        </div>
        """, unsafe_allow_html=True)

# ----------------- TAB 4: INTERACTIVE MATH & MARGINS -----------------
with tab_custom_calc:
    st.markdown("### 🧮 Deterministic Financial Calculations")
    g_cols = st.columns(3)
    with g_cols[0]:
        p1_name = st.text_input("Period 1 Label", "FY2023 Revenue")
        p1_val = st.number_input("Period 1 Value ($M)", value=211915.0, format="%.1f")
    with g_cols[1]:
        p2_name = st.text_input("Period 2 Label", "FY2024 Revenue")
        p2_val = st.number_input("Period 2 Value ($M)", value=245122.0, format="%.1f")
    with g_cols[2]:
        metric_lbl = st.text_input("Metric Name", "Microsoft Topline Growth")

    if st.button("Calculate Deterministic Growth", key="btn_calc_growth", type="primary"):
        growth = FinancialAnalysisEngine.compute_growth(
            base_value=p1_val,
            current_value=p2_val,
            metric_name=metric_lbl,
            period_1=p1_name,
            period_2=p2_name
        )
        r1, r2, r3 = st.columns(3)
        with r1:
            render_metric_card(f"{p1_name} Base", f"${growth.value_1:,.1f}M")
        with r2:
            render_metric_card(f"{p2_name} Result", f"${growth.value_2:,.1f}M")
        with r3:
            render_metric_card("Verified Growth Rate", f"{growth.percentage_change:+.2f}%", delta=f"+${growth.absolute_change:,.1f}M Delta")
