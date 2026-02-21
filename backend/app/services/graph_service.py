"""Graph service abstraction + SQLite adapter for Knowledge Graph."""

import json
from abc import ABC, abstractmethod

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tables import KGEdge, KGNode


def _safe_loads(raw: str, default=None):
    """Safely parse JSON string, return default on failure."""
    if default is None:
        default = {}
    try:
        return json.loads(raw) if raw else default
    except (json.JSONDecodeError, TypeError):
        return default


class GraphService(ABC):
    """Abstract interface for Knowledge Graph storage."""

    @abstractmethod
    async def upsert_node(
        self, project_id: int, label: str, name: str, properties: dict
    ) -> int:
        """Insert or update a node. Returns the node id."""
        ...

    @abstractmethod
    async def add_edge(
        self,
        project_id: int,
        source_id: int,
        target_id: int,
        relation: str,
        properties: dict,
    ) -> int:
        """Create an edge between two nodes. Returns the edge id."""
        ...

    @abstractmethod
    async def get_nodes(self, project_id: int, label: str | None = None) -> list:
        """Return all nodes for a project, optionally filtered by label."""
        ...

    @abstractmethod
    async def get_edges(self, project_id: int, node_id: int | None = None) -> list:
        """Return edges for a project, optionally filtered by node involvement."""
        ...

    @abstractmethod
    async def ensure_node(
        self, project_id: int, name: str, fallback_label: str
    ) -> int:
        """Get existing node by name, or create with fallback_label. Returns node id."""
        ...

    @abstractmethod
    async def upsert_edge(
        self,
        project_id: int,
        source_id: int,
        target_id: int,
        relation: str,
        properties: dict,
    ) -> int:
        """Insert or update an edge. Returns the edge id."""
        ...

    @abstractmethod
    async def delete_node(self, node_id: int) -> None:
        """Delete a node (cascades to its edges via FK)."""
        ...


class SQLiteGraphAdapter(GraphService):
    """SQLAlchemy / SQLite implementation of GraphService."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def upsert_node(
        self, project_id: int, label: str, name: str, properties: dict
    ) -> int:
        result = await self._db.execute(
            select(KGNode).where(
                KGNode.project_id == project_id,
                KGNode.label == label,
                KGNode.name == name,
            )
        )
        node = result.scalar_one_or_none()
        if node is None:
            node = KGNode(
                project_id=project_id,
                label=label,
                name=name,
                properties_json=json.dumps(properties, ensure_ascii=False),
            )
            self._db.add(node)
        else:
            node.properties_json = json.dumps(properties, ensure_ascii=False)
        await self._db.flush()
        await self._db.refresh(node)
        return node.id

    async def add_edge(
        self,
        project_id: int,
        source_id: int,
        target_id: int,
        relation: str,
        properties: dict,
    ) -> int:
        edge = KGEdge(
            project_id=project_id,
            source_node_id=source_id,
            target_node_id=target_id,
            relation=relation,
            properties_json=json.dumps(properties, ensure_ascii=False),
        )
        self._db.add(edge)
        await self._db.flush()
        await self._db.refresh(edge)
        return edge.id

    async def ensure_node(
        self, project_id: int, name: str, fallback_label: str
    ) -> int:
        """Return existing node id by name, or create with fallback_label."""
        result = await self._db.execute(
            select(KGNode).where(
                KGNode.project_id == project_id,
                KGNode.name == name,
            )
        )
        node = result.scalars().first()
        if node is not None:
            return node.id
        return await self.upsert_node(
            project_id, fallback_label, name, {}
        )

    async def upsert_edge(
        self,
        project_id: int,
        source_id: int,
        target_id: int,
        relation: str,
        properties: dict,
    ) -> int:
        """Insert edge or return existing. Dedup by (proj, src, tgt, rel)."""
        result = await self._db.execute(
            select(KGEdge).where(
                KGEdge.project_id == project_id,
                KGEdge.source_node_id == source_id,
                KGEdge.target_node_id == target_id,
                KGEdge.relation == relation,
            )
        )
        edge = result.scalar_one_or_none()
        if edge is not None:
            edge.properties_json = json.dumps(
                properties, ensure_ascii=False
            )
        else:
            edge = KGEdge(
                project_id=project_id,
                source_node_id=source_id,
                target_node_id=target_id,
                relation=relation,
                properties_json=json.dumps(
                    properties, ensure_ascii=False
                ),
            )
            self._db.add(edge)
        await self._db.flush()
        await self._db.refresh(edge)
        return edge.id

    async def get_nodes(self, project_id: int, label: str | None = None) -> list:
        stmt = select(KGNode).where(KGNode.project_id == project_id)
        if label:
            stmt = stmt.where(KGNode.label == label)
        result = await self._db.execute(stmt.order_by(KGNode.id))
        return result.scalars().all()

    async def get_edges(self, project_id: int, node_id: int | None = None) -> list:
        stmt = select(KGEdge).where(KGEdge.project_id == project_id)
        if node_id is not None:
            stmt = stmt.where(
                or_(
                    KGEdge.source_node_id == node_id,
                    KGEdge.target_node_id == node_id,
                )
            )
        result = await self._db.execute(stmt.order_by(KGEdge.id))
        return result.scalars().all()

    async def delete_node(self, node_id: int) -> None:
        node = await self._db.get(KGNode, node_id)
        if node:
            await self._db.delete(node)
            await self._db.flush()
