"""
Patch zep_tools.py __init__ to use local Neo4j instead of Zep Cloud.
Monkey-patches the constructor + key methods to bypass Zep Cloud API calls.
"""
import os
import sys
import json
import logging

logger = logging.getLogger(__name__)

NEO4J_URI = os.environ.get('NEO4J_URI', 'bolt://host.docker.internal:7687')
NEO4J_USER = os.environ.get('NEO4J_USER', 'neo4j')
NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD', 'mirofish2026')


def patch_zep_tools():
    """Monkey-patch ZepToolsService to use local Neo4j."""
    try:
        from neo4j import GraphDatabase
    except ImportError:
        logger.error("neo4j driver not installed, cannot patch zep_tools")
        return

    from app.services.zep_tools import ZepToolsService, NodeInfo, EdgeInfo, SearchResult

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    # Save original __init__
    _orig_init = ZepToolsService.__init__

    def _new_init(self, api_key=None, llm_client=None):
        """Patched init - skip Zep Cloud connection, use Neo4j."""
        self.api_key = api_key or "neo4j-local"
        self.client = None  # No Zep client needed
        self._llm_client = llm_client
        self._neo4j_driver = driver
        logger.info("ZepToolsService patched to use local Neo4j")

    def _get_all_nodes(self, graph_id):
        """Get all nodes from local Neo4j."""
        logger.info(f"[Neo4j] Getting all nodes for graph {graph_id}...")
        nodes = []
        with self._neo4j_driver.session() as s:
            result = s.run("MATCH (n:Entity {graph_id: $gid}) RETURN n", gid=graph_id)
            for record in result:
                n = record["n"]
                labels = n.get("labels", [])
                if isinstance(labels, str):
                    labels = [labels]
                attrs = n.get("attributes", "{}")
                if isinstance(attrs, str):
                    try:
                        attrs = json.loads(attrs)
                    except:
                        attrs = {}
                nodes.append(NodeInfo(
                    uuid=n.get("uuid", ""),
                    name=n.get("name", ""),
                    labels=labels,
                    summary=n.get("summary", ""),
                    attributes=attrs,
                ))
        logger.info(f"[Neo4j] Retrieved {len(nodes)} nodes")
        return nodes

    def _get_all_edges(self, graph_id, include_temporal=True):
        """Get all edges from local Neo4j."""
        logger.info(f"[Neo4j] Getting all edges for graph {graph_id}...")
        edges = []
        with self._neo4j_driver.session() as s:
            result = s.run("""
                MATCH (a:Entity {graph_id: $gid})-[r]->(b:Entity {graph_id: $gid})
                RETURN a.uuid AS src, b.uuid AS tgt,
                       type(r) AS rel_type, r.uuid AS uuid,
                       r.fact AS fact, r.name AS name
            """, gid=graph_id)
            for record in result:
                edges.append(EdgeInfo(
                    uuid=record["uuid"] or "",
                    name=record["name"] or record["rel_type"],
                    fact=record["fact"] or "",
                    source_node_uuid=record["src"],
                    target_node_uuid=record["tgt"],
                ))
        logger.info(f"[Neo4j] Retrieved {len(edges)} edges")
        return edges

    def _search_graph(self, graph_id, query, limit=10, scope="edges"):
        """Search graph using local Neo4j keyword matching."""
        logger.info(f"[Neo4j] Searching graph {graph_id}: {query[:50]}...")
        facts = []
        edges_result = []
        nodes_result = []

        query_lower = query.lower()
        keywords = [w.strip() for w in query_lower.replace(',', ' ').split() if len(w.strip()) > 1]

        def match_score(text):
            if not text:
                return 0
            text_lower = text.lower()
            if query_lower in text_lower:
                return 100
            score = 0
            for kw in keywords:
                if kw in text_lower:
                    score += 10
            return score

        if scope in ["edges", "both"]:
            all_edges = self.get_all_edges(graph_id)
            scored = [(match_score(e.fact) + match_score(e.name), e) for e in all_edges]
            scored = [(s, e) for s, e in scored if s > 0]
            scored.sort(key=lambda x: x[0], reverse=True)
            for score, edge in scored[:limit]:
                if edge.fact:
                    facts.append(edge.fact)
                edges_result.append({
                    "uuid": edge.uuid, "name": edge.name, "fact": edge.fact,
                    "source_node_uuid": edge.source_node_uuid,
                    "target_node_uuid": edge.target_node_uuid,
                })

        if scope in ["nodes", "both"]:
            all_nodes = self.get_all_nodes(graph_id)
            scored = [(match_score(n.name) + match_score(n.summary), n) for n in all_nodes]
            scored = [(s, n) for s, n in scored if s > 0]
            scored.sort(key=lambda x: x[0], reverse=True)
            for score, node in scored[:limit]:
                nodes_result.append({
                    "uuid": node.uuid, "name": node.name,
                    "labels": node.labels, "summary": node.summary,
                })
                if node.summary:
                    facts.append(f"[{node.name}]: {node.summary}")

        # If no keyword matches, return top nodes as context
        if not facts:
            all_nodes = self.get_all_nodes(graph_id)
            for node in all_nodes[:limit]:
                if node.summary:
                    facts.append(f"[{node.name}]: {node.summary}")
                nodes_result.append({
                    "uuid": node.uuid, "name": node.name,
                    "labels": node.labels, "summary": node.summary,
                })

        logger.info(f"[Neo4j] Search found {len(facts)} facts")
        return SearchResult(
            facts=facts, edges=edges_result, nodes=nodes_result,
            query=query, total_count=len(facts),
        )

    def _get_graph_statistics(self, graph_id):
        """Get graph statistics from local Neo4j."""
        nodes = self.get_all_nodes(graph_id)
        edges = self.get_all_edges(graph_id)
        entity_types = {}
        for node in nodes:
            for label in node.labels:
                if label not in ["Entity", "Node"]:
                    entity_types[label] = entity_types.get(label, 0) + 1
        relation_types = {}
        for edge in edges:
            relation_types[edge.name] = relation_types.get(edge.name, 0) + 1
        return {
            "graph_id": graph_id,
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "entity_types": entity_types,
            "relation_types": relation_types,
        }

    def _get_node_detail(self, node_uuid):
        """Get node detail from local Neo4j."""
        with self._neo4j_driver.session() as s:
            result = s.run("MATCH (n:Entity {uuid: $uuid}) RETURN n", uuid=node_uuid)
            record = result.single()
            if not record:
                return None
            n = record["n"]
            labels = n.get("labels", [])
            if isinstance(labels, str):
                labels = [labels]
            attrs = n.get("attributes", "{}")
            if isinstance(attrs, str):
                try:
                    attrs = json.loads(attrs)
                except:
                    attrs = {}
            return NodeInfo(
                uuid=n.get("uuid", ""),
                name=n.get("name", ""),
                labels=labels,
                summary=n.get("summary", ""),
                attributes=attrs,
            )

    def _get_node_edges(self, graph_id, node_uuid):
        """Get edges for a specific node from local Neo4j."""
        all_edges = self.get_all_edges(graph_id)
        return [e for e in all_edges if e.source_node_uuid == node_uuid or e.target_node_uuid == node_uuid]

    def _call_with_retry_local(self, func, operation_name, max_retries=None):
        """Simple retry without Zep."""
        try:
            return func()
        except Exception as e:
            logger.error(f"[Neo4j] {operation_name} failed: {e}")
            raise

    # Apply patches
    ZepToolsService.__init__ = _new_init
    ZepToolsService.get_all_nodes = _get_all_nodes
    ZepToolsService.get_all_edges = _get_all_edges
    ZepToolsService.search_graph = _search_graph
    ZepToolsService._local_search = _search_graph
    ZepToolsService.get_graph_statistics = _get_graph_statistics
    ZepToolsService.get_node_detail = _get_node_detail
    ZepToolsService.get_node_edges = _get_node_edges
    ZepToolsService._call_with_retry = _call_with_retry_local

    logger.info("✅ ZepToolsService fully patched to use local Neo4j")
