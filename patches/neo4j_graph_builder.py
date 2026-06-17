"""
Neo4j Graph Builder Service — Drop-in replacement for Zep GraphBuilderService.
Uses local Neo4j instead of Zep Cloud API.
"""

import os
import uuid
import json
import re
import time
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass

from neo4j import GraphDatabase
from openai import OpenAI

from ..config import Config
from ..models.task import TaskManager, TaskStatus
from .text_processor import TextProcessor


# Simple translation fallback
def t(key, **kwargs):
    """Simple translation stub — returns key with kwargs interpolated."""
    msg = key
    for k, v in kwargs.items():
        msg = msg.replace(f'{{{k}}}', str(v))
    return msg


NEO4J_URI = os.environ.get('NEO4J_URI', 'bolt://neo4j:7687')
NEO4J_USER = os.environ.get('NEO4J_USER', 'neo4j')
NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD', 'mirofish2026')


@dataclass
class GraphInfo:
    graph_id: str
    node_count: int
    edge_count: int
    entity_types: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "entity_types": self.entity_types,
        }


class GraphBuilderService:
    """Neo4j-based graph builder — replaces Zep Cloud."""
    
    def __init__(self, api_key: Optional[str] = None):
        # api_key kept for interface compatibility but not used
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        self.openai = OpenAI(api_key=Config.LLM_API_KEY)
        self.llm_model = Config.LLM_MODEL_NAME or 'gpt-4o'
        self.task_manager = TaskManager()

    def create_graph(self, name: str) -> str:
        graph_id = f"mirofish_{uuid.uuid4().hex[:16]}"
        with self.driver.session() as s:
            s.run(
                "CREATE (g:Graph {graph_id: $gid, name: $name, description: 'MiroFish Graph', created_at: datetime()})",
                gid=graph_id, name=name,
            )
        return graph_id

    def set_ontology(self, graph_id: str, ontology: Dict[str, Any]):
        """Store ontology as a node (Neo4j doesn't need Zep ontology setup)."""
        with self.driver.session() as s:
            s.run(
                "CREATE (o:Ontology {graph_id: $gid, data: $data, created_at: datetime()})",
                gid=graph_id, data=json.dumps(ontology),
            )

    def add_text_batches(self, graph_id: str, chunks: List[str], batch_size: int = 3,
                         progress_callback: Optional[Callable] = None) -> List[str]:
        """Extract entities/relationships from text chunks and store in Neo4j."""
        episode_uuids = []
        total = len(chunks)
        all_entities = {}
        all_relations = []

        for i, chunk in enumerate(chunks):
            batch_num = i + 1
            if progress_callback:
                progress_callback(
                    f"Processing batch {batch_num}/{total}",
                    (i + 1) / total
                )

            extracted = self._extract_entities(chunk)
            for ent in extracted.get("entities", []):
                key = ent["name"].lower().strip()
                if key not in all_entities:
                    all_entities[key] = ent
            all_relations.extend(extracted.get("relationships", []))
            episode_uuids.append(str(uuid.uuid4()))

        # Write to Neo4j
        self._write_entities(graph_id, list(all_entities.values()))
        self._write_relationships(graph_id, all_relations)

        return episode_uuids

    def _extract_entities(self, text: str) -> Dict[str, Any]:
        prompt = f"""Extract all entities and relationships from this text. Return valid JSON only.

Text:
{text[:6000]}

Return JSON format:
{{
  "entities": [
    {{"name": "entity name", "type": "Person|Organization|Location|Event|Concept", "summary": "brief description", "attributes": {{}}}}
  ],
  "relationships": [
    {{"source": "entity name", "target": "entity name", "type": "relationship type", "fact": "description"}}
  ]
}}"""

        for attempt in range(3):
            try:
                response = self.openai.chat.completions.create(
                    model=self.llm_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    response_format={"type": "json_object"},
                )
                return json.loads(response.choices[0].message.content)
            except Exception as e:
                if attempt < 2:
                    time.sleep(3)
                else:
                    return {"entities": [], "relationships": []}

    def _write_entities(self, graph_id: str, entities: List[Dict]):
        with self.driver.session() as s:
            for ent in entities:
                uid = str(uuid.uuid4())
                label = re.sub(r'[^A-Za-z0-9_]', '', ent.get("type", "Entity"))
                if not label:
                    label = "Entity"
                try:
                    s.run(
                        f"""CREATE (n:Entity:`{label}` {{
                            uuid: $uuid, graph_id: $gid, name: $name,
                            summary: $summary, labels: $labels,
                            attributes: $attrs, created_at: datetime()
                        }})""",
                        uuid=uid, gid=graph_id, name=ent["name"],
                        summary=ent.get("summary", ""),
                        labels=[label], attrs=json.dumps(ent.get("attributes", {})),
                    )
                except Exception:
                    pass

    def _write_relationships(self, graph_id: str, relations: List[Dict]):
        with self.driver.session() as s:
            for rel in relations:
                uid = str(uuid.uuid4())
                rel_type = re.sub(r'[^A-Za-z0-9_]', '_', rel.get("type", "RELATED_TO").upper().replace(" ", "_"))
                rel_type = re.sub(r'_+', '_', rel_type).strip('_') or "RELATED_TO"
                try:
                    s.run(
                        f"""MATCH (a:Entity {{graph_id: $gid, name: $source}})
                        MATCH (b:Entity {{graph_id: $gid, name: $target}})
                        CREATE (a)-[r:`{rel_type}` {{
                            uuid: $uuid, graph_id: $gid, name: $rtype,
                            fact: $fact, created_at: datetime()
                        }}]->(b)""",
                        uuid=uid, gid=graph_id,
                        source=rel["source"], target=rel["target"],
                        rtype=rel.get("type", "RELATED_TO"),
                        fact=rel.get("fact", ""),
                    )
                except Exception:
                    pass

    def _wait_for_episodes(self, episode_uuids, progress_callback=None, timeout=600):
        """No-op for Neo4j — data is already written synchronously."""
        if progress_callback:
            progress_callback(f"Processing complete ({len(episode_uuids)}/{len(episode_uuids)})", 1.0)

    def _get_graph_info(self, graph_id: str) -> GraphInfo:
        with self.driver.session() as s:
            nodes = list(s.run("MATCH (n:Entity {graph_id: $gid}) RETURN n", gid=graph_id))
            edges = list(s.run(
                "MATCH (a:Entity {graph_id: $gid})-[r]->(b:Entity {graph_id: $gid}) RETURN r",
                gid=graph_id
            ))
            labels = set()
            for r in nodes:
                n_labels = r["n"].get("labels", [])
                if isinstance(n_labels, list):
                    labels.update(n_labels)
        return GraphInfo(
            graph_id=graph_id,
            node_count=len(nodes),
            edge_count=len(edges),
            entity_types=list(labels),
        )

    def get_graph_data(self, graph_id: str) -> Dict[str, Any]:
        nodes = []
        edges = []
        with self.driver.session() as s:
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

        return {
            "graph_id": graph_id,
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
        }

    def delete_graph(self, graph_id: str):
        with self.driver.session() as s:
            s.run("MATCH (n {graph_id: $gid}) DETACH DELETE n", gid=graph_id)
