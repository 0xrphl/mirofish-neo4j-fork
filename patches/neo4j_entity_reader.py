"""
Neo4j Entity Reader — Drop-in replacement for ZepEntityReader.
Reads entities/edges from local Neo4j instead of Zep Cloud.
"""
import os, json, logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from neo4j import GraphDatabase

logger = logging.getLogger(__name__)

NEO4J_URI = os.environ.get('NEO4J_URI', 'bolt://host.docker.internal:7687')
NEO4J_USER = os.environ.get('NEO4J_USER', 'neo4j')
NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD', 'mirofish2026')


@dataclass
class FilteredEntities:
    """Container for filtered entity results."""
    agents: List[Dict[str, Any]] = field(default_factory=list)
    environments: List[Dict[str, Any]] = field(default_factory=list)
    total_count: int = 0
    agent_count: int = 0
    environment_count: int = 0
    entity_types: Dict[str, int] = field(default_factory=dict)

    @property
    def filtered_count(self) -> int:
        return self.agent_count + self.environment_count

    @property
    def entities(self) -> List['EntityNode']:
        """All filtered entities (agents + environments) as EntityNode objects."""
        return self.agents + self.environments

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agents": self.agents,
            "environments": self.environments,
            "total_count": self.total_count,
            "agent_count": self.agent_count,
            "environment_count": self.environment_count,
            "filtered_count": self.filtered_count,
            "entity_types": self.entity_types,
        }


@dataclass
class EntityNode:
    """Represents a single entity node."""
    uuid: str = ""
    name: str = ""
    labels: List[str] = field(default_factory=list)
    summary: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    edges: List[Dict[str, Any]] = field(default_factory=list)
    edge_count: int = 0
    related_edges: List[Dict[str, Any]] = field(default_factory=list)
    related_nodes: List[Dict[str, Any]] = field(default_factory=list)

    def get_entity_type(self) -> str:
        """Return the primary entity type from labels."""
        if self.labels:
            return self.labels[0]
        return "Entity"

    def get(self, key: str, default=None):
        """Dict-like get for compatibility."""
        return getattr(self, key, default)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "uuid": self.uuid, "name": self.name, "labels": self.labels,
            "summary": self.summary, "attributes": self.attributes,
            "created_at": self.created_at, "edges": self.edges,
            "edge_count": self.edge_count,
        }


class ZepEntityReader:
    """Neo4j-based entity reader — replaces Zep Cloud entity reader."""

    def __init__(self, api_key: Optional[str] = None):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    def _node_to_entity(self, n) -> EntityNode:
        labels = n.get("labels", [])
        if isinstance(labels, str):
            labels = [labels]
        attrs = n.get("attributes", "{}")
        if isinstance(attrs, str):
            try:
                attrs = json.loads(attrs)
            except:
                attrs = {}
        return EntityNode(
            uuid=n.get("uuid", ""),
            name=n.get("name", ""),
            labels=labels,
            summary=n.get("summary", ""),
            attributes=attrs,
            created_at=str(n.get("created_at", "")),
        )

    def _node_to_dict(self, n) -> Dict[str, Any]:
        return self._node_to_entity(n).to_dict()

    def get_all_nodes(self, graph_id: str) -> List[EntityNode]:
        nodes = []
        with self.driver.session() as s:
            result = s.run("MATCH (n:Entity {graph_id: $gid}) RETURN n", gid=graph_id)
            for record in result:
                nodes.append(self._node_to_entity(record["n"]))
        logger.info(f"Neo4j: Retrieved {len(nodes)} nodes for graph {graph_id}")
        return nodes

    def get_node_edges(self, node_uuid: str) -> List[Dict[str, Any]]:
        edges = []
        with self.driver.session() as s:
            result = s.run("""
                MATCH (a:Entity {uuid: $uuid})-[r]-(b:Entity)
                RETURN a.name AS source_name, a.uuid AS source_uuid,
                       b.name AS target_name, b.uuid AS target_uuid,
                       type(r) AS rel_type, r.uuid AS uuid, r.fact AS fact,
                       r.name AS name
            """, uuid=node_uuid)
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
                })
        return edges

    def get_entity_count(self, graph_id: str) -> int:
        with self.driver.session() as s:
            result = s.run("MATCH (n:Entity {graph_id: $gid}) RETURN count(n) AS cnt", gid=graph_id)
            record = result.single()
            return record["cnt"] if record else 0

    def filter_defined_entities(
        self,
        graph_id: str,
        ontology: Optional[Dict[str, Any]] = None,
        max_agents: int = 100,
        max_environments: int = 50,
        defined_entity_types: Optional[List[str]] = None,
        **kwargs,
    ) -> FilteredEntities:
        """Filter entities into agents and environments based on ontology."""
        all_nodes = self.get_all_nodes(graph_id)
        
        # Cap agents to max_agents (default 8 for our 8-agent evaluation system)
        max_agents = min(max_agents, 8)
        max_environments = min(max_environments, 4)
        
        # Determine which types are agent-like vs environment-like
        # Only pick Person entities that match our 8 evaluation agents
        agent_types = {"Person"}
        env_types = {"Location", "Place", "Environment", "Setting", "Event",
                     "Organization", "Concept", "Document", "Database", "Section",
                     "Compañía", "Organización", "Proceso", "Política", "Policy",
                     "Correo electrónico", "Orden", "Comunicación Formal"}
        
        if ontology and "entity_types" in ontology:
            for et in ontology["entity_types"]:
                name = et.get("name", "") if isinstance(et, dict) else str(et)
                # Simple heuristic: if it looks like a person/role type, it's an agent
                name_lower = name.lower()
                if any(kw in name_lower for kw in ["person", "client", "customer", "agent", 
                                                     "representative", "specialist", "manager",
                                                     "persona", "cliente", "representante"]):
                    agent_types.add(name)
                else:
                    env_types.add(name)

        agents = []
        environments = []
        entity_types = {}

        for node in all_nodes:
            node_type = node.get_entity_type()
            labels = node.labels
            entity_types[node_type] = entity_types.get(node_type, 0) + 1

            # Get edges for context
            edges = self.get_node_edges(node.uuid)
            node.edges = edges
            node.edge_count = len(edges)
            node.related_edges = edges
            # Collect related node info from edges
            related = []
            for e in edges:
                related.append({
                    "uuid": e.get("target_node_uuid", ""),
                    "name": e.get("target_node_name", ""),
                    "relationship": e.get("name", ""),
                })
            node.related_nodes = related

            if node_type in agent_types or any(l in agent_types for l in labels):
                if len(agents) < max_agents:
                    agents.append(node)
            else:
                if len(environments) < max_environments:
                    environments.append(node)

        # If no agents found, treat all as agents
        if not agents:
            agents = all_nodes[:max_agents]
            environments = []

        result = FilteredEntities(
            agents=agents,
            environments=environments,
            total_count=len(all_nodes),
            agent_count=len(agents),
            environment_count=len(environments),
            entity_types=entity_types,
        )
        
        logger.info(f"Neo4j filter: {result.agent_count} agents, {result.environment_count} environments from {result.total_count} total")
        return result
