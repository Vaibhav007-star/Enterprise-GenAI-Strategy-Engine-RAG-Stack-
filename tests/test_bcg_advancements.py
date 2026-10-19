import pytest
import io
from pptx import Presentation

from src.generation.agentic_critic import AgenticCriticAuditor, ClaimAudit
from src.generation.llm_client import GroundedOfflineSynthesizer
from src.chunking.models import TextChunk
from src.intelligence.deck_generator import ExecutiveDeckGenerator
from src.intelligence.graph_rag import EnterpriseKnowledgeGraph
from src.financial_analysis.tco_calculator import EnterpriseTCOEngine, TCOInputParameters
from src.financial_analysis.scenario_simulator import ScenarioStressSimulator
from src.security.access_control import VirtualDataRoomRBAC, UserRole, SecurityClearance
from src.retrieval.semantic_cache import SemanticQueryCache
from src.citations.grounding_auditor import GroundingAuditor


def test_agentic_critic_numerical_verification():
    llm = GroundedOfflineSynthesizer()
    auditor = AgenticCriticAuditor(llm)

    context = [
        TextChunk(
            chunk_id="c1",
            document_id="doc1",
            document_name="MSFT Form 10-K FY2024",
            content="Microsoft Intelligent Cloud revenue was $105.4 billion in FY24, an increase of 19%.",
            chunk_type="child"
        )
    ]

    # Test truthful response
    accurate_resp = "Microsoft Intelligent Cloud reached $105.4B in FY24, reflecting 19% growth."
    audit_res = auditor.audit("What was cloud revenue?", accurate_resp, context)
    assert audit_res.numerical_accuracy_score >= 0.9
    assert audit_res.status == "PASSED"

    # Test hallucinated number
    hallucinated_resp = "Microsoft Intelligent Cloud was $199.9B with a 95% operating margin."
    audit_hallucinated = auditor.audit("What was cloud revenue?", hallucinated_resp, context)
    assert audit_hallucinated.numerical_accuracy_score < 0.5
    assert audit_hallucinated.unsupported_claims_count > 0


def test_executive_pptx_deck_generation():
    deck_buffer = ExecutiveDeckGenerator.create_executive_deck(
        title="AI Cloud Transformation Analysis",
        subtitle="Microsoft vs Apple Form 10-K Strategic Benchmarks",
        query="Analyze Azure Cloud margin expansion",
        synthesis_text="Intelligent Cloud delivered $105.4B in revenue. Cloud operating margins expanded 190 bps.",
        metrics={"Cloud Revenue": "$105.4B", "Gross Margin": "71.2%"},
        risks=["AI Accelerator availability bottleneck"]
    )
    assert deck_buffer is not None
    assert deck_buffer.getbuffer().nbytes > 10000

    # Verify generated presentation structure
    prs = Presentation(deck_buffer)
    assert len(prs.slides) == 3
    # Check 16:9 widescreen dimensions (13.33 x 7.5 in)
    assert round(prs.slide_width.inches, 2) == 13.33
    assert round(prs.slide_height.inches, 2) == 7.5


def test_bcg_10_20_70_tco_engine():
    params = TCOInputParameters(
        num_employees=2000,
        daily_queries_per_employee=3.0,
        work_days_per_year=250,
        avg_tokens_per_query=2500,
        total_transformation_budget=1000000.0  # $1M
    )
    res = EnterpriseTCOEngine.calculate_tco(params)

    # 10-20-70 validation
    assert res.bcg_10_algorithms_budget == 100000.0
    assert res.bcg_20_tech_data_budget == 200000.0
    assert res.bcg_70_people_workflows_budget == 700000.0

    # Business case outputs
    assert res.annual_query_volume == 1500000
    assert res.annual_hours_saved > 0
    assert res.annual_net_ebitda_impact > 0
    assert res.payback_period_months > 0


def test_scenario_stress_matrix():
    res = ScenarioStressSimulator.run_sensitivity_matrix(
        base_ebitda_billions=100.0,
        cost_savings_pcts=[2.0, 5.0, 10.0],
        multiples=[10.0, 20.0]
    )
    assert len(res.matrix) == 3
    assert len(res.matrix[0]) == 2
    # Row 0: 2% improvement -> adjusted EBITDA = 102.0. At multiple 10 -> 1020.0; at 20 -> 2040.0
    assert res.matrix[0][0] == 1020.0
    assert res.matrix[0][1] == 2040.0
    assert res.delta_value_matrix[0][0] == 20.0


def test_virtual_data_room_rbac():
    chunks = [
        TextChunk(chunk_id="c1", document_id="d1", document_name="MSFT Form 10-K", content="Public SEC 10-K data", chunk_type="child"),
        TextChunk(chunk_id="c2", document_id="d2", document_name="Project Titan M&A Deal Room Clean Room", content="Confidential Deal Room M&A Targets", chunk_type="child"),
        TextChunk(chunk_id="c3", document_id="d3", document_name="BCG AI Strategy Framework Playbook", content="Restricted Strategy Playbook", chunk_type="child")
    ]

    # Public Analyst should only see public 10-K
    allowed_pub, log_pub = VirtualDataRoomRBAC.filter_chunks_by_role(chunks, user_role=UserRole.PUBLIC_ANALYST)
    assert len(allowed_pub) == 1
    assert log_pub.redacted_chunks_count == 2

    # M&A Partner Clean Room should see confidential deal chunks
    allowed_ma, log_ma = VirtualDataRoomRBAC.filter_chunks_by_role(chunks, user_role=UserRole.MA_PARTNER_CLEANROOM)
    assert len(allowed_ma) == 3
    assert log_ma.redacted_chunks_count == 0


def test_semantic_query_cache():
    cache = SemanticQueryCache(similarity_threshold=0.90, max_entries=50)

    emb_1 = [0.1, 0.2, 0.3, 0.4]
    emb_close = [0.105, 0.198, 0.302, 0.395]  # Highly similar cosine similarity > 0.99
    emb_far = [-0.5, 0.1, 0.0, -0.2]

    cache.store(
        query="What is Microsoft cloud revenue?",
        embedding=emb_1,
        response_text="Intelligent cloud was $105.4B.",
        citations=[]
    )

    # Lookup with similar query
    hit = cache.lookup("What is MSFT Azure cloud revenue?", emb_close)
    assert hit is not None
    entry, sim = hit
    assert sim > 0.95
    assert entry.response_text == "Intelligent cloud was $105.4B."

    # Lookup with unrelated query
    miss = cache.lookup("Unrelated question", emb_far)
    assert miss is None

    stats = cache.get_stats()
    assert stats.hits == 1
    assert stats.misses == 1


def test_knowledge_graph_and_pathfinding():
    graph = EnterpriseKnowledgeGraph()
    data = graph.get_graph_data()
    assert len(data.nodes) >= 10
    assert len(data.edges) >= 10

    # Test multi-hop path finding from MSFT to TSMC
    paths = graph.find_multi_hop_path("MSFT", "TSMC", max_depth=3)
    assert len(paths) > 0
    # Expected path: MSFT -> NVDA -> TSMC
    first_path = paths[0]
    assert first_path[0]["from"] == "MSFT"
    assert first_path[-1]["to"] == "TSMC"


def test_grounding_auditor():
    context = [
        TextChunk(
            chunk_id="c1",
            document_id="d1",
            document_name="AAPL Form 10-K FY2024",
            content="Apple Services revenue set an all-time record of $96.2 billion with 74.0% gross margin.",
            chunk_type="child"
        )
    ]

    report = GroundingAuditor.audit_spans(
        text="Apple Services revenue was $96.2 billion with 74.0% gross margin. Total company operations performed strongly.",
        context_chunks=context
    )
    assert report.green_count == 1
    assert report.red_count == 1
    assert report.overall_grounding_score == 0.5
    assert report.spans[0].status == "GROUNDED_GREEN"
    assert report.spans[1].status == "UNVERIFIED_RED"

