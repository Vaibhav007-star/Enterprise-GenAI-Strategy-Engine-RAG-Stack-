import os
import sys
import time
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import shutil

# Ensure workspace root is in path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, Response, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd

from src.engine import get_engine
from src.security.sanitizer import SecuritySanitizer
from src.security.access_control import UserRole
from src.financial_analysis.financial_engine import FinancialAnalysisEngine
from src.financial_analysis.tco_calculator import TCOInputParameters
from src.evaluation.sample_tests import get_default_test_suite
from src.utils.logger import get_logger

logger = get_logger("web_server")

app = FastAPI(title="Enterprise GenAI Strategy Engine - Web Platform", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Backend Engine Singleton
engine = get_engine()

# Request Models
class QueryRequest(BaseModel):
    query: str
    persona: str = "bcg_partner"
    top_k: int = 6
    use_hybrid: bool = True
    use_reranker: bool = False
    document_ids: Optional[List[str]] = None
    user_role: str = "STRATEGY_CONSULTANT"
    bypass_cache: bool = False


class DeckExportRequest(BaseModel):
    title: str = "Executive Strategy Briefing"
    subtitle: str = "Fortune 500 Strategic Analysis & Financial Assessment"
    query: str
    synthesis_text: str
    metrics: Optional[Dict[str, Any]] = None
    recommendations: Optional[List[str]] = None
    risks: Optional[List[str]] = None


class TCOApiRequest(BaseModel):
    num_employees: int = 2500
    daily_queries_per_employee: float = 4.0
    work_days_per_year: int = 250
    avg_tokens_per_query: int = 3000
    api_cost_per_million_tokens: float = 2.00
    self_hosted_gpu_cluster_annual_cost: float = 120000.0
    employee_hourly_cost: float = 85.0
    minutes_saved_per_query: float = 12.0
    total_transformation_budget: float = 1500000.0


class ScenarioApiRequest(BaseModel):
    base_ebitda: float = 109.4
    cost_savings_pcts: Optional[List[float]] = None
    multiples: Optional[List[float]] = None


class GrowthRequest(BaseModel):
    base_val: float
    current_val: float
    metric_name: str = "Metric"
    period_1: str = "Period 1"
    period_2: str = "Period 2"


class MarginRequest(BaseModel):
    revenue: float
    costs: float


class ValuationRequest(BaseModel):
    base_ebitda: float
    cost_out_pct: float
    multiple: float


class ComparisonRequest(BaseModel):
    doc_id_1: str
    doc_id_2: str
    focus_aspect: str


class ComplianceRequest(BaseModel):
    compliance_topic: str
    document_ids: Optional[List[str]] = None



# ---------------- API ENDPOINTS ----------------

@app.get("/api/stats")
def get_system_stats():
    """Return top-level telemetry and collection metrics."""
    docs = engine.document_store.get_all_documents()
    col_stats = engine.vector_store.get_collection_stats()
    history = engine.document_store.get_query_history(limit=10)
    
    avg_latency = (
        round(sum(h.get("latency_ms", 0) for h in history) / len(history), 1)
        if history else 0.0
    )

    return {
        "total_documents": len(docs),
        "total_chunks": col_stats.get("total_chunks", 0),
        "total_queries": len(engine.document_store.query_history),
        "avg_latency_ms": avg_latency,
        "active_model": engine.settings.llm_model if engine.llm_client.is_available() else "Offline Grounded Synthesizer",
        "embedding_model": engine.settings.embedding_model_name
    }


@app.get("/api/documents")
def get_documents():
    """Return list of all registered documents."""
    return engine.document_store.get_all_documents()


@app.post("/api/query")
def execute_query(req: QueryRequest):
    """Execute grounded question answering with customizable strategy persona and BCG X Multi-Agent Audit."""
    clean_query = SecuritySanitizer.sanitize_user_query(req.query)
    if not clean_query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    # Parse user role
    role = UserRole.STRATEGY_CONSULTANT
    try:
        role = UserRole(req.user_role)
    except ValueError:
        pass

    # Execute through unified BCG X engine
    result = engine.query_enterprise(
        query=clean_query,
        persona=req.persona,
        top_k=req.top_k,
        use_hybrid=req.use_hybrid,
        use_reranker=req.use_reranker,
        document_ids=req.document_ids,
        user_role=role,
        bypass_cache=req.bypass_cache
    )

    # Log query in document store history
    engine.document_store.log_query({
        "timestamp": datetime.datetime.now().isoformat(),
        "question": clean_query,
        "answer_preview": result["answer"][:120],
        "citations_count": len(result.get("citations", [])),
        "sufficient_evidence": bool(result.get("citations")),
        "latency_ms": result["telemetry"].get("total_latency_ms", 0.0),
        "is_cache_hit": result.get("is_cache_hit", False)
    })

    # Format citations for frontend compatibility
    formatted_citations = []
    for c in result.get("citations", []):
        formatted_citations.append({
            "id": c.get("citation_id", c.get("id", "SOURCE")),
            "document_name": c.get("document_name", c.get("source_doc_title", "Audited 10-K")),
            "document_id": c.get("document_id", ""),
            "page_number": c.get("page_number", 1),
            "section_title": c.get("section_title", "Item 7 MD&A / Financials"),
            "sheet_name": c.get("sheet_name", ""),
            "snippet": c.get("snippet", c.get("text", "")[:240]),
            "relevance_score": round(c.get("relevance_score", 0.95), 3)
        })

    return {
        "answer": result["answer"],
        "hardened_answer": result.get("hardened_answer"),
        "citations": formatted_citations,
        "has_sufficient_evidence": len(formatted_citations) > 0,
        "critic_audit": result.get("critic_audit"),
        "grounding_report": result.get("grounding_report"),
        "rbac_audit": result.get("rbac_audit"),
        "telemetry": result.get("telemetry"),
        "graph_context": result.get("graph_context"),
        "is_cache_hit": result.get("is_cache_hit", False),
        "cache_similarity": result.get("cache_similarity", 0.0),
        "diagnostics": {
            "persona": req.persona,
            "total_latency_ms": result["telemetry"].get("total_latency_ms", 0.0),
            "is_cache_hit": result.get("is_cache_hit", False)
        }
    }


@app.post("/api/export/deck")
def export_executive_deck(req: DeckExportRequest):
    """Generate and download a boardroom-ready 16:9 widescreen PowerPoint presentation (.pptx)."""
    try:
        buffer = engine.deck_generator.create_executive_deck(
            title=req.title,
            subtitle=req.subtitle,
            query=req.query,
            synthesis_text=req.synthesis_text,
            metrics=req.metrics,
            recommendations=req.recommendations,
            risks=req.risks
        )
        pptx_bytes = buffer.getvalue()
        filename = f"BCG_Executive_Briefing_{int(time.time())}.pptx"
        return Response(
            content=pptx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        logger.error(f"Deck generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate PowerPoint deck: {str(e)}")


@app.post("/api/tco/simulate")
def simulate_enterprise_tco(req: TCOApiRequest):
    """BCG 10-20-70 GenAI Total Cost of Ownership (TCO) & Value Realization simulator."""
    params = TCOInputParameters(
        num_employees=req.num_employees,
        daily_queries_per_employee=req.daily_queries_per_employee,
        work_days_per_year=req.work_days_per_year,
        avg_tokens_per_query=req.avg_tokens_per_query,
        api_cost_per_million_tokens=req.api_cost_per_million_tokens,
        self_hosted_gpu_cluster_annual_cost=req.self_hosted_gpu_cluster_annual_cost,
        employee_hourly_cost=req.employee_hourly_cost,
        minutes_saved_per_query=req.minutes_saved_per_query,
        total_transformation_budget=req.total_transformation_budget
    )
    result = engine.tco_engine.calculate_tco(params)
    return result.model_dump()


@app.post("/api/scenarios/sensitivity")
def compute_sensitivity_matrix(req: ScenarioApiRequest):
    """Generate 2D sensitivity matrix of Cloud Margin Efficiency vs Valuation Exit Multiples."""
    result = engine.scenario_simulator.run_sensitivity_matrix(
        base_ebitda_billions=req.base_ebitda,
        cost_savings_pcts=req.cost_savings_pcts,
        multiples=req.multiples
    )
    return result.model_dump()


@app.get("/api/graph/data")
def get_knowledge_graph_data():
    """Retrieve full Fortune 500 value chain and risk topology graph."""
    graph_data = engine.knowledge_graph.get_graph_data()
    return graph_data.model_dump()


@app.get("/api/graph/path")
def find_graph_path(source: str, target: str):
    """Find multi-hop causal paths between strategic entities."""
    paths = engine.knowledge_graph.find_multi_hop_path(source, target)
    return {"source": source, "target": target, "paths": paths}


@app.get("/api/cache/stats")
def get_cache_stats():
    """Retrieve Semantic Query Cache metrics (hit rate, tokens saved, USD saved)."""
    return engine.semantic_cache.get_stats().model_dump()


@app.post("/api/cache/clear")
def clear_semantic_cache():
    """Reset the semantic query cache."""
    engine.semantic_cache.clear()
    return {"status": "cleared", "message": "Semantic cache successfully purged."}


@app.get("/api/security/roles")
def get_security_roles():
    """Return available Virtual Data Room user roles and security clearances."""
    from src.security.access_control import ROLE_PERMISSIONS
    return {
        "roles": [r.value for r in UserRole],
        "permissions": {r.value: [c.value for c in perms] for r, perms in ROLE_PERMISSIONS.items()}
    }



@app.get("/api/financial/peers")
def get_tech_peers_benchmark():
    """Return multi-company Tech Giants financial comparison data."""
    csv_path = engine.settings.sample_data_dir / "Tech_Giants_FY2023_FY2024_Financial_Comparison.csv"
    if not csv_path.exists():
        return []
    df = pd.read_csv(csv_path)
    return df.to_dict(orient="records")


@app.post("/api/financial/growth")
def compute_growth(req: GrowthRequest):
    """Deterministic period-over-period growth calculation."""
    res = FinancialAnalysisEngine.compute_growth(
        base_value=req.base_val,
        current_value=req.current_val,
        metric_name=req.metric_name,
        period_1=req.period_1,
        period_2=req.period_2
    )
    return {
        "metric_name": res.metric_name,
        "period_1": res.period_1,
        "value_1": res.value_1,
        "period_2": res.period_2,
        "value_2": res.value_2,
        "absolute_change": res.absolute_change,
        "percentage_change": res.percentage_change,
        "trend": res.trend
    }


@app.post("/api/financial/valuation")
def compute_valuation(req: ValuationRequest):
    """Simulate Enterprise Value (EV) creation levers from EBITDA and exit multiples."""
    incremental_ebitda = req.base_ebitda * (req.cost_out_pct / 100.0)
    adjusted_ebitda = req.base_ebitda + incremental_ebitda
    implied_ev_base = req.base_ebitda * req.multiple
    implied_ev_adjusted = adjusted_ebitda * req.multiple
    value_unlocked = implied_ev_adjusted - implied_ev_base

    return {
        "base_ebitda": req.base_ebitda,
        "cost_out_pct": req.cost_out_pct,
        "multiple": req.multiple,
        "incremental_ebitda": round(incremental_ebitda, 2),
        "adjusted_ebitda": round(adjusted_ebitda, 2),
        "implied_ev_base": round(implied_ev_base, 2),
        "implied_ev_adjusted": round(implied_ev_adjusted, 2),
        "value_unlocked": round(value_unlocked, 2)
    }


@app.post("/api/compare")
def compare_documents(req: ComparisonRequest):
    """Execute side-by-side multi-document comparative analysis."""
    docs = {d["document_id"]: d["file_name"] for d in engine.document_store.get_all_documents()}
    name_1 = docs.get(req.doc_id_1, "Document A")
    name_2 = docs.get(req.doc_id_2, "Document B")

    res = engine.comparator.compare_documents(
        doc_id_1=req.doc_id_1,
        doc_name_1=name_1,
        doc_id_2=req.doc_id_2,
        doc_name_2=name_2,
        focus_aspect=req.focus_aspect
    )

    return {
        "report": res.answer,
        "citations": [
            {
                "id": c.citation_id,
                "document_name": c.document_name,
                "snippet": c.snippet,
                "relevance_score": round(c.relevance_score, 3)
            }
            for c in res.citations
        ]
    }


@app.post("/api/compliance")
def audit_compliance(req: ComplianceRequest):
    """Audit documents for regulatory mandates and policy gaps."""
    res = engine.compliance_scanner.audit_risk_and_compliance(
        compliance_topic=req.compliance_topic,
        document_ids=req.document_ids
    )
    return {
        "report": res.answer,
        "citations": [
            {
                "id": c.citation_id,
                "document_name": c.document_name,
                "snippet": c.snippet,
                "relevance_score": round(c.relevance_score, 3)
            }
            for c in res.citations
        ]
    }


@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    chunk_strategy: str = Form("parent_child"),
    force_reindex: bool = Form(False)
):
    """Handle enterprise document upload, validation, parsing, and indexing."""
    valid, err = SecuritySanitizer.validate_file_upload(file.filename, 1024)
    if not valid:
        raise HTTPException(status_code=400, detail=err)

    dest_path = engine.settings.upload_dir / file.filename
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    result = engine.ingestion_pipeline.ingest_file(
        source_path=dest_path,
        chunking_strategy=chunk_strategy,
        force_reindex=force_reindex
    )
    engine.retriever.refresh_bm25_index()

    return {
        "file_name": result.file_name,
        "success": result.success,
        "document_id": result.document_id,
        "chunks_indexed": result.chunks_indexed,
        "tables_indexed": result.tables_indexed,
        "is_duplicate": result.is_duplicate,
        "warning": result.warning,
        "error": result.error
    }


@app.delete("/api/documents/{doc_id}")
def delete_document(doc_id: str):
    """Purge document and chunks from index and registry."""
    success = engine.ingestion_pipeline.delete_document(doc_id)
    if success:
        engine.retriever.refresh_bm25_index()
        return {"status": "deleted", "document_id": doc_id}
    raise HTTPException(status_code=404, detail="Document not found.")


@app.post("/api/evaluation/run")
def run_evaluation_suite():
    """Run empirical benchmark evaluation test suite."""
    test_suite = get_default_test_suite()
    report = engine.evaluator.run_suite(test_suite)
    return {
        "total_cases": report.total_cases,
        "passed_cases": report.passed_cases,
        "pass_rate_pct": report.pass_rate_pct,
        "avg_context_precision": report.avg_context_precision,
        "avg_context_recall": report.avg_context_recall,
        "avg_faithfulness": report.avg_faithfulness,
        "avg_latency_ms": report.avg_latency_ms,
        "cases": [
            {
                "case_id": c.case_id,
                "query": c.query,
                "category": c.test_category,
                "passed": c.passed,
                "context_precision": c.context_precision,
                "context_recall": c.context_recall,
                "faithfulness": c.faithfulness_score,
                "latency_ms": c.total_latency_ms,
                "notes": c.notes
            }
            for c in report.case_results
        ]
    }


# Static Files & Frontend Mount
static_dir = BASE_DIR / "static"
if not static_dir.exists():
    static_dir = BASE_DIR / "public" / "static"
if not static_dir.exists():
    static_dir = Path("static")
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", response_class=HTMLResponse)
def serve_index():
    index_file = static_dir / "index.html"
    if not index_file.exists():
        index_file = Path("static/index.html")
    if index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Enterprise GenAI Strategy Engine Web Platform</h1>"


def find_available_port(preferred_port: int = 8000) -> int:
    import socket
    for port in [preferred_port, 8001, 8080, 8502]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            if s.connect_ex(('127.0.0.1', port)) != 0:
                return port
    return preferred_port


if __name__ == "__main__":
    import uvicorn
    chosen_port = find_available_port(int(os.environ.get("PORT", 8000)))
    print(f"\n==========================================================")
    print(f"🚀 BCG Strategy Engine Web Application is launching on:")
    print(f"👉 http://localhost:{chosen_port}")
    print(f"==========================================================\n")
    uvicorn.run("server:app", host="0.0.0.0", port=chosen_port, reload=False)

