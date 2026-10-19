from typing import List, Dict, Any, Optional, Set
from pydantic import BaseModel, Field
from ..utils.logger import get_logger

logger = get_logger("graph_rag")


class GraphNode(BaseModel):
    id: str
    label: str
    category: str  # "Enterprise", "Segment", "Technology", "Risk", "Regulator", "Supplier"
    metrics: Dict[str, Any] = Field(default_factory=dict)
    description: Optional[str] = None


class GraphEdge(BaseModel):
    source: str
    target: str
    relation: str  # "PARTNERED_WITH", "DEPENDS_ON", "COMPETES_WITH", "REGULATES", "EXPOSED_TO", "DRIVES_REVENUE"
    weight: float = 1.0
    evidence_doc: Optional[str] = None


class KnowledgeGraphData(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]


class EnterpriseKnowledgeGraph:
    """BCG X GraphRAG Engine: Maps Fortune 500 value chains, strategic partnerships,
    regulatory exposures, and segment interdependencies for multi-hop reasoning."""

    def __init__(self):
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []
        self._bootstrap_enterprise_ontology()

    def _bootstrap_enterprise_ontology(self):
        """Populate initial grounded knowledge graph from pre-loaded Fortune 500 Form 10-K filings."""
        core_nodes = [
            # Corporates
            GraphNode(id="MSFT", label="Microsoft Corporation", category="Enterprise", metrics={"revenue": "$245.1B", "ebit": "$109.4B", "market": "Tech/Cloud"}),
            GraphNode(id="AAPL", label="Apple Inc.", category="Enterprise", metrics={"revenue": "$391.0B", "services_margin": "74.0%", "market": "Consumer/Tech"}),
            GraphNode(id="NVDA", label="NVIDIA Corporation", category="Supplier", metrics={"gross_margin": "75.0%+", "market": "AI Hardware"}),
            GraphNode(id="OAI", label="OpenAI", category="Partner", metrics={"partnership_type": "Strategic IP / Exclusive Cloud"}),
            GraphNode(id="TSMC", label="TSMC", category="Supplier", metrics={"market_share": ">50% Advanced Foundry"}),
            GraphNode(id="AMZN", label="Amazon (AWS)", category="Enterprise", metrics={"market": "Cloud Infrastructure"}),
            GraphNode(id="GOOGL", label="Alphabet (Google Cloud)", category="Enterprise", metrics={"market": "Cloud & AI Search"}),

            # Segments
            GraphNode(id="SEG_AZURE", label="Intelligent Cloud (Azure)", category="Segment", metrics={"fy24_revenue": "$105.4B", "growth": "19%"}),
            GraphNode(id="SEG_PROD", label="Productivity & Business Processes", category="Segment", metrics={"fy24_revenue": "$77.7B"}),
            GraphNode(id="SEG_IPHONE", label="iPhone Hardware", category="Segment", metrics={"fy24_revenue": "$201.2B"}),
            GraphNode(id="SEG_SERVICES", label="Apple Services", category="Segment", metrics={"fy24_revenue": "$96.2B", "gross_margin": "74.0%"}),

            # Technologies
            GraphNode(id="TECH_COPILOT", label="Microsoft 365 Copilot", category="Technology", metrics={"adoption": "Enterprise Growth Driver"}),
            GraphNode(id="TECH_GPU", label="H100 / Blackwell AI Accelerators", category="Technology", metrics={"status": "Constrained Supply"}),
            GraphNode(id="TECH_RAG", label="Enterprise RAG Architecture", category="Technology", metrics={"token_savings": "38% parent-child"}),

            # Regulators & Regulations
            GraphNode(id="REG_EU_AI", label="EU AI Act", category="Regulator", metrics={"impact": "High-Risk AI Governance & Transparency"}),
            GraphNode(id="REG_EU_DMA", label="EU Digital Markets Act (DMA)", category="Regulator", metrics={"impact": "App Store & Interoperability Compliance"}),
            GraphNode(id="REG_SEC", label="U.S. SEC", category="Regulator", metrics={"mandate": "Audited 10-K & Material Risk Disclosure"}),

            # Strategic Risks
            GraphNode(id="RISK_GPU_BOTTLENECK", label="AI Compute & GPU Allocation Bottleneck", category="Risk", metrics={"severity": "Critical"}),
            GraphNode(id="RISK_ANTITRUST", label="Global Platform Antitrust Scrutiny", category="Risk", metrics={"severity": "Elevated"}),
            GraphNode(id="RISK_CHINA_SUPPLY", label="Greater China Supply Chain Concentration", category="Risk", metrics={"severity": "Moderate-High"})
        ]

        for node in core_nodes:
            self.nodes[node.id] = node

        core_edges = [
            # Corporate Relationships
            GraphEdge(source="MSFT", target="OAI", relation="PARTNERED_WITH", weight=1.0, evidence_doc="MSFT FY24 10-K Item 1"),
            GraphEdge(source="MSFT", target="NVDA", relation="DEPENDS_ON", weight=0.9, evidence_doc="MSFT FY24 10-K Item 1A"),
            GraphEdge(source="NVDA", target="TSMC", relation="MANUFACTURED_BY", weight=1.0, evidence_doc="NVDA 10-K Supply Chain"),
            GraphEdge(source="MSFT", target="AMZN", relation="COMPETES_WITH", weight=0.8, evidence_doc="MSFT FY24 10-K Item 1"),
            GraphEdge(source="MSFT", target="GOOGL", relation="COMPETES_WITH", weight=0.8, evidence_doc="MSFT FY24 10-K Item 1"),

            # Revenue Drivers
            GraphEdge(source="MSFT", target="SEG_AZURE", relation="DRIVES_REVENUE", weight=1.0, evidence_doc="MSFT FY24 10-K Item 7"),
            GraphEdge(source="MSFT", target="SEG_PROD", relation="DRIVES_REVENUE", weight=0.8, evidence_doc="MSFT FY24 10-K Item 7"),
            GraphEdge(source="AAPL", target="SEG_IPHONE", relation="DRIVES_REVENUE", weight=1.0, evidence_doc="AAPL FY24 10-K"),
            GraphEdge(source="AAPL", target="SEG_SERVICES", relation="DRIVES_REVENUE", weight=0.9, evidence_doc="AAPL FY24 10-K"),
            GraphEdge(source="SEG_AZURE", target="TECH_COPILOT", relation="POWERED_BY", weight=0.9, evidence_doc="MSFT FY24 10-K Item 1"),
            GraphEdge(source="TECH_COPILOT", target="OAI", relation="LEVERAGES_IP", weight=1.0, evidence_doc="MSFT FY24 10-K Item 1"),

            # Risk & Regulatory Dependencies
            GraphEdge(source="SEG_AZURE", target="RISK_GPU_BOTTLENECK", relation="VULNERABLE_TO", weight=0.9, evidence_doc="MSFT FY24 10-K Item 1A"),
            GraphEdge(source="RISK_GPU_BOTTLENECK", target="NVDA", relation="TRACEABLE_TO", weight=0.85, evidence_doc="Industry Analysis"),
            GraphEdge(source="MSFT", target="REG_EU_AI", relation="EXPOSED_TO", weight=0.8, evidence_doc="MSFT FY24 10-K Item 1A"),
            GraphEdge(source="AAPL", target="REG_EU_DMA", relation="EXPOSED_TO", weight=0.95, evidence_doc="AAPL FY24 10-K Item 1A"),
            GraphEdge(source="AAPL", target="RISK_CHINA_SUPPLY", relation="EXPOSED_TO", weight=0.85, evidence_doc="AAPL FY24 10-K"),
            GraphEdge(source="AAPL", target="RISK_ANTITRUST", relation="EXPOSED_TO", weight=0.8, evidence_doc="AAPL FY24 10-K")
        ]

        self.edges.extend(core_edges)

    def get_graph_data(self) -> KnowledgeGraphData:
        """Export serialized nodes and edges for visual frontend rendering."""
        return KnowledgeGraphData(
            nodes=list(self.nodes.values()),
            edges=self.edges
        )

    def find_multi_hop_path(self, start_id: str, target_id: str, max_depth: int = 4) -> List[List[Dict[str, str]]]:
        """Find strategic multi-hop causal paths between two entities (e.g. EU AI Act -> Azure)."""
        paths = []
        visited = set()

        def dfs(current: str, target: str, current_path: List[Dict[str, str]], depth: int):
            if depth > max_depth or current in visited:
                return
            if current == target and current_path:
                paths.append(list(current_path))
                return

            visited.add(current)
            # Traverse outgoing and incoming edges
            for edge in self.edges:
                if edge.source == current and edge.target not in visited:
                    next_step = {"from": current, "to": edge.target, "relation": edge.relation}
                    dfs(edge.target, target, current_path + [next_step], depth + 1)
                elif edge.target == current and edge.source not in visited:
                    next_step = {"from": current, "to": edge.source, "relation": f"INVERSE_{edge.relation}"}
                    dfs(edge.source, target, current_path + [next_step], depth + 1)
            visited.remove(current)

        dfs(start_id, target_id, [], 0)
        return paths

    def query_subgraph_for_context(self, query: str) -> str:
        """Find matching entities in query and generate concise graph context to inject into LLM prompts."""
        query_lower = query.lower()
        matched_nodes = []
        for nid, node in self.nodes.items():
            if node.label.lower() in query_lower or nid.lower() in query_lower:
                matched_nodes.append(node)

        if not matched_nodes:
            # Fallback to key anchor nodes
            matched_nodes = [self.nodes["MSFT"], self.nodes["AAPL"]]

        matched_ids = {n.id for n in matched_nodes}
        relevant_edges = [
            e for e in self.edges 
            if e.source in matched_ids or e.target in matched_ids
        ][:6]

        context_lines = ["### Enterprise Value Chain Knowledge Graph Context:"]
        for e in relevant_edges:
            src_lbl = self.nodes.get(e.source, GraphNode(id=e.source, label=e.source, category="")).label
            tgt_lbl = self.nodes.get(e.target, GraphNode(id=e.target, label=e.target, category="")).label
            context_lines.append(f"- **{src_lbl}** --[{e.relation}]--> **{tgt_lbl}** (Evidence: {e.evidence_doc or 'Audited 10-K'})")

        return "\n".join(context_lines)
