from fastapi.testclient import TestClient
from server import app

client = TestClient(app)


def test_api_stats():
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_documents" in data
    assert "total_chunks" in data


def test_api_query_and_critic():
    payload = {
        "query": "What is Microsoft Intelligent Cloud revenue and growth rate?",
        "persona": "bcg_partner",
        "top_k": 3,
        "user_role": "STRATEGY_CONSULTANT"
    }
    resp = client.post("/api/query", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert "citations" in data
    assert "critic_audit" in data
    assert "telemetry" in data
    assert data["critic_audit"]["status"] in ("PASSED", "PASSED_WITH_CAVEATS", "FLAGGED_REVISION")


def test_api_deck_export():
    payload = {
        "title": "Microsoft vs Apple Cloud Strategy",
        "subtitle": "Audited SEC Form 10-K Strategic Benchmarks",
        "query": "Evaluate Azure cloud segment margins",
        "synthesis_text": "Intelligent Cloud grew 19% reaching $105.4B. Operating margins expanded 190 bps.",
        "metrics": {"Cloud Revenue": "$105.4B", "Gross Margin": "71.2%"},
        "risks": ["GPU Compute Shortages"]
    }
    resp = client.post("/api/export/deck", json=payload)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    assert len(resp.content) > 5000


def test_api_tco_simulate():
    payload = {
        "num_employees": 3000,
        "daily_queries_per_employee": 4.0,
        "total_transformation_budget": 1200000.0
    }
    resp = client.post("/api/tco/simulate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["bcg_10_algorithms_budget"] == 120000.0
    assert data["bcg_20_tech_data_budget"] == 240000.0
    assert data["bcg_70_people_workflows_budget"] == 840000.0
    assert data["annual_hours_saved"] > 0
    assert data["annual_net_ebitda_impact"] > 0


def test_api_scenario_sensitivity():
    payload = {
        "base_ebitda": 109.4,
        "cost_savings_pcts": [2.0, 5.0, 10.0],
        "multiples": [15.0, 20.0, 25.0]
    }
    resp = client.post("/api/scenarios/sensitivity", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["matrix"]) == 3
    assert len(data["matrix"][0]) == 3


def test_api_graph_data_and_path():
    resp = client.get("/api/graph/data")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["nodes"]) >= 10
    assert len(data["edges"]) >= 10

    resp_path = client.get("/api/graph/path?source=MSFT&target=TSMC")
    assert resp_path.status_code == 200
    path_data = resp_path.json()
    assert "paths" in path_data
    assert len(path_data["paths"]) > 0


def test_api_cache_stats_and_clear():
    resp = client.get("/api/cache/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "hit_rate_pct" in data
    assert "estimated_cost_saved_usd" in data

    resp_clear = client.post("/api/cache/clear")
    assert resp_clear.status_code == 200


def test_api_security_roles():
    resp = client.get("/api/security/roles")
    assert resp.status_code == 200
    data = resp.json()
    assert "STRATEGY_CONSULTANT" in data["roles"]
    assert "MA_PARTNER_CLEANROOM" in data["roles"]
