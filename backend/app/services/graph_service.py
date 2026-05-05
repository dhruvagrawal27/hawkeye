"""Neo4j graph service."""

from __future__ import annotations

from typing import Any
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.schemas import GraphData, GraphNode, GraphLink

log = structlog.get_logger()


class GraphService:
    def __init__(self) -> None:
        self._driver = None
        self.connected = False

    async def connect(self) -> None:
        from app.deps import get_neo4j
        try:
            self._driver = await get_neo4j()
            # Verify connection
            async with self._driver.session() as session:
                await session.run("RETURN 1")
            self.connected = True
            log.info("neo4j_connected")
            await self._create_indexes()
        except Exception as exc:
            log.warning("neo4j_connect_failed", error=str(exc))
            self.connected = False

    async def _create_indexes(self) -> None:
        queries = [
            "CREATE INDEX employee_id IF NOT EXISTS FOR (e:Employee) ON (e.id)",
            "CREATE INDEX system_id IF NOT EXISTS FOR (s:SystemResource) ON (s.id)",
        ]
        try:
            async with self._driver.session() as session:
                for q in queries:
                    await session.run(q)
        except Exception as exc:
            log.warning("index_creation_failed", error=str(exc))

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
    async def merge_access(self, employee_id: str, resource_id: str, event: dict[str, Any]) -> None:
        if not self._driver:
            return
        cypher = """
        MERGE (e:Employee {id: $emp_id})
        MERGE (s:SystemResource {id: $res_id})
        MERGE (e)-[r:ACCESSED]->(s)
        ON CREATE SET r.count = 1, r.first_seen = $ts
        ON MATCH  SET r.count = r.count + 1
        SET r.last_seen = $ts,
            r.amount = $amount,
            e.risk_score = coalesce(e.risk_score, 0.0)
        """
        async with self._driver.session() as session:
            await session.run(cypher, {
                "emp_id": employee_id,
                "res_id": resource_id,
                "ts": event.get("timestamp", ""),
                "amount": float(event.get("amount", 0) or 0),
            })

    async def update_risk_score(self, employee_id: str, score: float) -> None:
        if not self._driver:
            return
        async with self._driver.session() as session:
            await session.run(
                "MERGE (e:Employee {id: $id}) SET e.risk_score = $score, e.flagged = ($score >= 0.5)",
                {"id": employee_id, "score": score},
            )

    async def get_neighborhood(self, employee_id: str, depth: int = 2, limit: int = 200) -> GraphData:
        if not self._driver:
            return GraphData(nodes=[], links=[])
        cypher = """
        MATCH path = (e:Employee {id: $emp_id})-[:ACCESSED*1..2]-(neighbor)
        WITH nodes(path) AS ns, relationships(path) AS rels
        UNWIND ns AS n
        WITH COLLECT(DISTINCT n) AS all_nodes, rels
        UNWIND rels AS r
        RETURN all_nodes, COLLECT(DISTINCT r) AS all_rels
        LIMIT $limit
        """
        try:
            async with self._driver.session() as session:
                result = await session.run(cypher, {"emp_id": employee_id, "limit": limit})
                record = await result.single()
                if not record:
                    return GraphData(nodes=[], links=[])
                return self._build_graph_data(record["all_nodes"], record["all_rels"])
        except Exception as exc:
            log.warning("graph_query_failed", error=str(exc))
            return GraphData(nodes=[], links=[])

    async def get_top_risk_graph(self, limit: int = 50) -> GraphData:
        if not self._driver:
            return GraphData(nodes=[], links=[])
        cypher = """
        MATCH (e:Employee)-[r:ACCESSED]->(s:SystemResource)
        WITH e ORDER BY e.risk_score DESC LIMIT $limit
        MATCH (e)-[r:ACCESSED]->(s:SystemResource)
        RETURN COLLECT(DISTINCT e) AS emps, COLLECT(DISTINCT s) AS systems, COLLECT(DISTINCT r) AS rels
        """
        try:
            async with self._driver.session() as session:
                result = await session.run(cypher, {"limit": limit})
                record = await result.single()
                if not record:
                    return GraphData(nodes=[], links=[])
                all_nodes = list(record["emps"]) + list(record["systems"])
                return self._build_graph_data(all_nodes, record["rels"])
        except Exception as exc:
            log.warning("top_risk_graph_failed", error=str(exc))
            return GraphData(nodes=[], links=[])

    def _build_graph_data(self, nodes: list, rels: list) -> GraphData:
        graph_nodes = []
        graph_links = []
        seen_nodes: set[str] = set()

        for n in nodes:
            props = dict(n)
            nid = props.get("id", str(n.id))
            if nid in seen_nodes:
                continue
            seen_nodes.add(nid)
            labels = list(n.labels)
            ntype = "employee" if "Employee" in labels else "system"
            graph_nodes.append(GraphNode(
                id=nid,
                label=nid,
                type=ntype,
                risk_score=props.get("risk_score"),
                flagged=props.get("flagged", False),
            ))

        for r in rels:
            props = dict(r)
            src = dict(r.start_node).get("id", str(r.start_node.id))
            tgt = dict(r.end_node).get("id", str(r.end_node.id))
            graph_links.append(GraphLink(
                source=src,
                target=tgt,
                weight=float(props.get("count", 1)),
                access_type=props.get("access_type"),
            ))

        return GraphData(nodes=graph_nodes, links=graph_links)

    async def seed_from_synthetic(self, accounts_path: str, transactions_path: str) -> None:
        """Seed Neo4j from synthetic parquet files if the graph is empty."""
        if not self._driver:
            return
        try:
            async with self._driver.session() as session:
                result = await session.run("MATCH (n) RETURN count(n) AS cnt")
                record = await result.single()
                if record and record["cnt"] > 0:
                    log.info("neo4j_already_seeded", count=record["cnt"])
                    return
        except Exception:
            pass

        try:
            import pandas as pd
            txns = pd.read_parquet(transactions_path)
            log.info("seeding_neo4j", rows=len(txns))
            batch_size = 500
            for i in range(0, min(len(txns), 10000), batch_size):
                batch = txns.iloc[i:i + batch_size]
                cypher = """
                UNWIND $rows AS row
                MERGE (e:Employee {id: row.employee_id})
                MERGE (s:SystemResource {id: row.system_resource})
                MERGE (e)-[r:ACCESSED]->(s)
                ON CREATE SET r.count = 1
                ON MATCH  SET r.count = r.count + 1
                SET r.last_seen = row.timestamp
                """
                rows = []
                for _, row in batch.iterrows():
                    rows.append({
                        "employee_id": str(row.get("employee_id", row.get("account_id", ""))),
                        "system_resource": str(row.get("system_resource", row.get("counterparty_id", ""))),
                        "timestamp": str(row.get("timestamp", "")),
                    })
                async with self._driver.session() as session:
                    await session.run(cypher, {"rows": rows})
            log.info("neo4j_seeded")
        except Exception as exc:
            log.warning("neo4j_seed_failed", error=str(exc))
