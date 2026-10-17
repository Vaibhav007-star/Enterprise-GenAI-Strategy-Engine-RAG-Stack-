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
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd

from src.engine import get_engine
from src.security.sanitizer import SecuritySanitizer
from src.financial_analysis.financial_engine import FinancialAnalysisEngine
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
    """Execute grounded question answering with customizable strategy persona."""
    clean_query = SecuritySanitizer.sanitize_user_query(req.query)
    if not clean_query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    # Persona custom instruction prompt
    if req.persona == "bcg_partner":
        persona_directive = (
            "Adopt the persona of a senior Boston Consulting Group (BCG) Strategy Partner. "
            "Structure the response using the Pyramidal Principle:\n"
            "1. EXECUTIVE STRATEGY RECOMMENDATION (Top-down direct answer)\n"
            "2. QUANTITATIVE PILLARS & FINANCIAL EVIDENCE (Audited SEC Form 10-K numbers with [SOURCE X] citations)\n"
            "3. VALUE CREATION LEVERS (Identified commercial upside)\n"
            "4. DOWNSIDE RISK & MITIGATION FRAMEWORK (Regulatory, supply chain, geopolitical)\n"
            "Ensure the analysis is Mutually Exclusive and Collectively Exhaustive (MECE)."
        )
    elif req.persona == "private_equity":
        persona_directive = (
            "Adopt the persona of a Private Equity / M&A Due Diligence Principal:\n"
            "1. INVESTMENT THESIS & CORE VERDICT\n"
            "2. RECURRING REVENUE QUALITY & SEGMENT MARGINS (Audited 10-K data with [SOURCE X])\n"
            "3. CAPEX INTENSITY & FREE CASH FLOW CONVERSION\n"
            "4. DOWNSIDE VULNERABILITIES & REGULATORY EXPOSURES\n"
        )
    else:
        persona_directive = "Focus strictly on technical accuracy, token economy, and specific page/item references."

    start_t = time.perf_counter()

    # 1. Retrieve hybrid candidates
    retrieval_output = engine.retriever.retrieve(
        query=clean_query,
        top_k=req.top_k,
        use_hybrid=req.use_hybrid,
        use_reranker=req.use_reranker,
        filter_document_ids=req.document_ids,
        expand_parent_context=True
    )
    retrieved_chunks = retrieval_output["results"]

    # 2. Generate Grounded Answer
    grounded_resp = engine.generator.generate_answer(
        query=clean_query,
        retrieved_chunks=retrieved_chunks,
        custom_instructions=persona_directive
    )
    elapsed_ms = round((time.perf_counter() - start_t) * 1000.0, 1)

    # 3. Log query to document store history
    engine.document_store.log_query({
        "timestamp": datetime.datetime.now().isoformat(),
        "question": clean_query,
        "answer_preview": grounded_resp.answer[:120],
        "citations_count": len(grounded_resp.citations),
        "sufficient_evidence": grounded_resp.has_sufficient_evidence,
        "latency_ms": elapsed_ms
    })

    return {
        "answer": grounded_resp.answer,
        "citations": [
            {
                "id": c.citation_id,
                "document_name": c.document_name,
                "document_id": c.document_id,
                "page_number": c.page_number,
                "section_title": c.section_title,
                "sheet_name": c.sheet_name,
                "snippet": c.snippet,
                "relevance_score": round(c.relevance_score, 3)
            }
            for c in grounded_resp.citations
        ],
        "has_sufficient_evidence": grounded_resp.has_sufficient_evidence,
        "diagnostics": {
            **retrieval_output["diagnostics"],
            **grounded_resp.diagnostics,
            "persona": req.persona,
            "total_latency_ms": elapsed_ms
        }
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
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
def serve_index():
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Enterprise GenAI Strategy Engine API running. Create static/index.html to view UI."}


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

