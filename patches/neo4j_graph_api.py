"""
Neo4j Local Graph API — Drop-in replacement for Zep graph endpoints.
Mounted at /api/neo4j/
"""

import os
import json
import uuid
from flask import Blueprint, request, jsonify
from neo4j import GraphDatabase

neo4j_bp = Blueprint('neo4j_graph', __name__)

# Neo4j connection
NEO4J_URI = os.environ.get('NEO4J_URI', 'bolt://host.docker.internal:7687')
NEO4J_USER = os.environ.get('NEO4J_USER', 'neo4j')
NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD', 'mirofish2026')

def get_driver():
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


@neo4j_bp.route('/graphs', methods=['GET'])
def list_graphs():
    driver = get_driver()
    try:
        with driver.session() as s:
            result = s.run("MATCH (g:Graph) RETURN g ORDER BY g.created_at DESC")
            graphs = []
            for r in result:
                g = r["g"]
                graphs.append({
                    "graph_id": g["graph_id"],
                    "name": g["name"],
                    "description": g.get("description", ""),
                })
        return jsonify({"success": True, "data": graphs, "count": len(graphs)})
    finally:
        driver.close()


@neo4j_bp.route('/data/<graph_id>', methods=['GET'])
def get_graph_data(graph_id):
    driver = get_driver()
    try:
        nodes = []
        edges = []
        with driver.session() as s:
            result = s.run("MATCH (n:Entity {graph_id: $gid}) RETURN n", gid=graph_id)
            for record in result:
                n = record["n"]
                nodes.append({
                    "uuid": n.get("uuid", ""),
                    "name": n.get("name", ""),
                    "labels": n.get("labels", []),
                    "summary": n.get("summary", ""),
                    "attributes": json.loads(n.get("attributes", "{}")),
                    "created_at": str(n.get("created_at", "")),
                })
            
            result = s.run("""
                MATCH (a:Entity {graph_id: $gid})-[r]->(b:Entity {graph_id: $gid})
                RETURN a.name AS source_name, a.uuid AS source_uuid,
                       b.name AS target_name, b.uuid AS target_uuid,
                       type(r) AS rel_type, r.uuid AS uuid, r.fact AS fact,
                       r.name AS name, r.created_at AS created_at
            """, gid=graph_id)
            for record in result:
                edges.append({
                    "uuid": record["uuid"] or "",
                    "name": record["name"] or record["rel_type"],
                    "fact": record["fact"] or "",
                    "fact_type": record["rel_type"],
                    "source_node_uuid": record["source_uuid"],
                    "target_node_uuid": record["target_uuid"],
                    "source_node_name": record["source_name"],
                    "target_node_name": record["target_name"],
                    "attributes": {},
                    "created_at": str(record["created_at"]) if record["created_at"] else None,
                    "valid_at": None, "invalid_at": None, "expired_at": None,
                    "episodes": [],
                })

        return jsonify({
            "success": True,
            "data": {
                "graph_id": graph_id,
                "nodes": nodes,
                "edges": edges,
                "node_count": len(nodes),
                "edge_count": len(edges),
            }
        })
    finally:
        driver.close()


@neo4j_bp.route('/search/<graph_id>', methods=['POST'])
def search_graph(graph_id):
    data = request.get_json() or {}
    query_text = data.get("query", "")
    driver = get_driver()
    try:
        with driver.session() as s:
            result = s.run("""
                MATCH (n:Entity {graph_id: $gid})
                WHERE toLower(n.name) CONTAINS toLower($q)
                   OR toLower(n.summary) CONTAINS toLower($q)
                RETURN n LIMIT 20
            """, gid=graph_id, q=query_text)
            nodes = []
            for record in result:
                n = record["n"]
                nodes.append({
                    "uuid": n.get("uuid", ""),
                    "name": n.get("name", ""),
                    "summary": n.get("summary", ""),
                    "labels": n.get("labels", []),
                })
        return jsonify({"success": True, "data": nodes, "count": len(nodes)})
    finally:
        driver.close()
