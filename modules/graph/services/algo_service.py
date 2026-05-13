from __future__ import annotations

from collections import defaultdict
from typing import Any
from uuid import uuid4

from shared.config.config import KINGBASE_APP_SCHEMA, logger
from shared.db.kingbase import execute_many, fetch_all, fetch_value, table_exists
from shared.db.neo4j_db import run_query


def _gang_result_table_ready() -> bool:
    return table_exists(KINGBASE_APP_SCHEMA, "hm_gang_result")


def _latest_run_id() -> str:
    if not _gang_result_table_ready():
        return ""
    return str(
        fetch_value(
            f"""
            SELECT COALESCE(run_id, '')
            FROM {KINGBASE_APP_SCHEMA}.hm_gang_result
            ORDER BY computed_at DESC, id DESC
            LIMIT 1
            """
        )
        or ""
    )


def _drop_projection(graph_name: str) -> None:
    exists_rows = run_query(
        "CALL gds.graph.exists($graph_name) YIELD exists RETURN exists",
        {"graph_name": graph_name},
    )
    if exists_rows and exists_rows[0].get("exists"):
        run_query(
            "CALL gds.graph.drop($graph_name, false) YIELD graphName RETURN graphName",
            {"graph_name": graph_name},
        )


def _run_gds_community_detection(
    graph_name: str,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], str]:
    projection: list[dict[str, Any]] | None = None
    try:
        _drop_projection(graph_name)
        projection = run_query(
            """
            CALL gds.graph.project(
                $graph_name,
                'Person',
                {
                    CO_SUSPECT: {
                        type: 'CO_SUSPECT',
                        orientation: 'UNDIRECTED',
                        properties: 'weight'
                    }
                }
            )
            YIELD graphName, nodeCount, relationshipCount
            RETURN graphName, nodeCount, relationshipCount
            """,
            {"graph_name": graph_name},
        )

        louvain_rows = run_query(
            """
            CALL gds.louvain.stream($graph_name, {relationshipWeightProperty: 'weight'})
            YIELD nodeId, communityId
            RETURN gds.util.asNode(nodeId).sfzh AS member_sfzh,
                   gds.util.asNode(nodeId).name AS member_name,
                   gds.util.asNode(nodeId).age AS member_age,
                   coalesce(gds.util.asNode(nodeId).is_wcnr, false) AS is_wcnr,
                   coalesce(gds.util.asNode(nodeId).area_code, '') AS area_code,
                   communityId
            ORDER BY communityId ASC, member_sfzh ASC
            """,
            {"graph_name": graph_name},
        )
        betweenness_rows = run_query(
            """
            CALL gds.betweenness.stream($graph_name)
            YIELD nodeId, score
            RETURN gds.util.asNode(nodeId).sfzh AS member_sfzh,
                   score
            """,
            {"graph_name": graph_name},
        )
        return projection[0] if projection else {}, louvain_rows, betweenness_rows, "louvain"
    finally:
        try:
            _drop_projection(graph_name)
        except Exception as exc:
            logger.warning("failed to drop GDS projection %s: %s", graph_name, exc)


def _run_networkx_community_detection() -> tuple[
    dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], str
]:
    import networkx as nx

    rows = run_query(
        """
        MATCH (a:Person)-[r:CO_SUSPECT]-(b:Person)
        WHERE a.sfzh < b.sfzh
        RETURN a {.sfzh, .name, .age, .is_wcnr, .area_code} AS source,
               b {.sfzh, .name, .age, .is_wcnr, .area_code} AS target,
               coalesce(r.weight, 1) AS weight
        """
    )
    graph = nx.Graph()
    for row in rows:
        source = row.get("source") or {}
        target = row.get("target") or {}
        source_sfzh = str(source.get("sfzh") or "").strip()
        target_sfzh = str(target.get("sfzh") or "").strip()
        if not source_sfzh or not target_sfzh:
            continue
        graph.add_node(source_sfzh, **source)
        graph.add_node(target_sfzh, **target)
        graph.add_edge(source_sfzh, target_sfzh, weight=float(row.get("weight") or 1.0))

    if graph.number_of_edges() <= 0:
        return (
            {
                "graphName": "hm-co-suspect-networkx",
                "nodeCount": graph.number_of_nodes(),
                "relationshipCount": 0,
            },
            [],
            [],
            "networkx_louvain",
        )

    algo_type = "networkx_louvain"
    try:
        communities = nx.community.louvain_communities(graph, weight="weight", seed=42)
    except Exception as exc:
        logger.warning("NetworkX Louvain failed; using connected components: %s", exc)
        communities = [set(component) for component in nx.connected_components(graph)]
        algo_type = "networkx_components"

    centrality = nx.betweenness_centrality(graph, normalized=True)
    louvain_rows: list[dict[str, Any]] = []
    for community_id, members in enumerate(communities):
        for sfzh in sorted(str(member) for member in members):
            attrs = graph.nodes[sfzh]
            louvain_rows.append(
                {
                    "member_sfzh": sfzh,
                    "member_name": attrs.get("name"),
                    "member_age": attrs.get("age"),
                    "is_wcnr": bool(attrs.get("is_wcnr")),
                    "area_code": attrs.get("area_code") or "",
                    "communityId": community_id,
                }
            )

    betweenness_rows = [
        {"member_sfzh": str(sfzh), "score": score}
        for sfzh, score in centrality.items()
    ]
    return (
        {
            "graphName": "hm-co-suspect-networkx",
            "nodeCount": graph.number_of_nodes(),
            "relationshipCount": graph.number_of_edges(),
        },
        louvain_rows,
        betweenness_rows,
        algo_type,
    )


def detect_gangs(min_size: int = 2) -> dict[str, Any]:
    if not _gang_result_table_ready():
        raise RuntimeError(
            f"KingBase table {KINGBASE_APP_SCHEMA}.hm_gang_result not found; execute sql/01_create_hm_tables.sql first"
        )

    edge_count_rows = run_query(
        "MATCH ()-[r:CO_SUSPECT]-() RETURN count(r) AS edge_count"
    )
    edge_count = int(edge_count_rows[0].get("edge_count") or 0) if edge_count_rows else 0
    if edge_count <= 0:
        return {"ok": True, "run_id": "", "gang_count": 0, "member_count": 0, "message": "no CO_SUSPECT relationships found"}

    graph_name = "hm-co-suspect"
    try:
        projection_info, louvain_rows, betweenness_rows, algo_type = (
            _run_gds_community_detection(graph_name)
        )
    except Exception as exc:
        logger.warning("Neo4j GDS gang detection failed; falling back to NetworkX: %s", exc)
        projection_info, louvain_rows, betweenness_rows, algo_type = (
            _run_networkx_community_detection()
        )

    centrality_by_person = {
        str(row.get("member_sfzh") or ""): float(row.get("score") or 0.0)
        for row in betweenness_rows
    }
    members_by_community: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in louvain_rows:
        members_by_community[int(row.get("communityId") or 0)].append(row)

    run_id = uuid4().hex
    inserts: list[tuple[Any, ...]] = []
    gang_count = 0
    for community_id, members in sorted(members_by_community.items(), key=lambda item: len(item[1]), reverse=True):
        if len(members) < max(2, int(min_size or 2)):
            continue
        gang_count += 1
        gang_id = f"community_{community_id}"
        gang_size = len(members)
        area_code = next((str(member.get("area_code") or "") for member in members if member.get("area_code")), "")
        for member in members:
            sfzh = str(member.get("member_sfzh") or "").strip()
            if not sfzh:
                continue
            inserts.append(
                (
                    gang_id,
                    run_id,
                    sfzh,
                    member.get("member_name"),
                    member.get("member_age"),
                    bool(member.get("is_wcnr")),
                    gang_size,
                    centrality_by_person.get(sfzh, 0.0),
                    algo_type,
                    None,
                    area_code,
                )
            )

    if inserts:
        execute_many(
            f"""
            INSERT INTO {KINGBASE_APP_SCHEMA}.hm_gang_result (
                gang_id,
                run_id,
                member_sfzh,
                member_name,
                member_age,
                is_wcnr,
                gang_size,
                centrality_score,
                algo_type,
                case_types,
                area_code
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (run_id, member_sfzh) DO UPDATE
            SET gang_id = EXCLUDED.gang_id,
                member_name = EXCLUDED.member_name,
                member_age = EXCLUDED.member_age,
                is_wcnr = EXCLUDED.is_wcnr,
                gang_size = EXCLUDED.gang_size,
                centrality_score = EXCLUDED.centrality_score,
                algo_type = EXCLUDED.algo_type,
                case_types = EXCLUDED.case_types,
                area_code = EXCLUDED.area_code,
                computed_at = NOW()
            """,
            inserts,
        )

    return {
        "ok": True,
        "run_id": run_id,
        "graph_name": projection_info.get("graphName", graph_name),
        "node_count": int(projection_info.get("nodeCount") or 0),
        "relationship_count": int(projection_info.get("relationshipCount") or 0),
        "algo_type": algo_type,
        "gang_count": gang_count,
        "member_count": len(inserts),
    }


def list_gangs(limit: int = 20, run_id: str = "") -> dict[str, Any]:
    if not _gang_result_table_ready():
        return {"ok": True, "table_ready": False, "items": []}

    active_run_id = run_id.strip() or _latest_run_id()
    if not active_run_id:
        return {"ok": True, "table_ready": True, "items": [], "run_id": ""}

    rows = fetch_all(
        f"""
        SELECT gang_id,
               MAX(gang_size) AS gang_size,
               MAX(computed_at) AS computed_at,
               MAX(centrality_score) AS max_centrality,
               COUNT(*) AS member_count,
               SUM(CASE WHEN is_wcnr THEN 1 ELSE 0 END) AS wcnr_count,
               MAX(area_code) AS area_code
        FROM {KINGBASE_APP_SCHEMA}.hm_gang_result
        WHERE run_id = %s
        GROUP BY gang_id
        ORDER BY member_count DESC, max_centrality DESC, gang_id ASC
        LIMIT %s
        """,
        (active_run_id, max(1, min(int(limit or 20), 200))),
    )
    for row in rows:
        if row.get("computed_at") is not None:
            row["computed_at"] = row["computed_at"].isoformat(timespec="seconds")
    return {"ok": True, "table_ready": True, "run_id": active_run_id, "items": rows}


def get_gang_detail(gang_id: str, run_id: str = "") -> dict[str, Any] | None:
    if not _gang_result_table_ready():
        return None

    active_run_id = run_id.strip() or _latest_run_id()
    if not active_run_id:
        return None

    members = fetch_all(
        f"""
        SELECT gang_id, run_id, member_sfzh, member_name, member_age, is_wcnr,
               gang_size, centrality_score, computed_at, area_code
        FROM {KINGBASE_APP_SCHEMA}.hm_gang_result
        WHERE run_id = %s AND gang_id = %s
        ORDER BY centrality_score DESC NULLS LAST, member_sfzh ASC
        """,
        (active_run_id, gang_id),
    )
    if not members:
        return None

    sfzhs = [str(row.get("member_sfzh") or "") for row in members if row.get("member_sfzh")]
    graph_rows = run_query(
        """
        MATCH (a:Person)-[r:CO_SUSPECT]-(b:Person)
        WHERE a.sfzh IN $sfzhs AND b.sfzh IN $sfzhs AND a.sfzh < b.sfzh
        RETURN a {.sfzh, .name, .age, .is_wcnr, .area_code} AS source,
               b {.sfzh, .name, .age, .is_wcnr, .area_code} AS target,
               r {.weight, .case_count, .first_case_date, .last_case_date, .case_types} AS rel
        """,
        {"sfzhs": sfzhs},
    )
    case_rows = run_query(
        """
        MATCH (p:Person)-[r:SAME_CASE]->(c:Case)
        WHERE p.sfzh IN $sfzhs
        RETURN p.sfzh AS sfzh,
               c {.ajbh, .aymc, .ajlx, .fasj, .area_code} AS case_node,
               r {.case_date, .area_code, .aymc} AS rel
        """,
        {"sfzhs": sfzhs},
    )
    return {
        "ok": True,
        "run_id": active_run_id,
        "gang_id": gang_id,
        "members": members,
        "links": graph_rows,
        "cases": case_rows,
    }


def predict_links(limit: int = 50, min_common: int = 2) -> dict[str, Any]:
    """Find Person pairs that share common CO_SUSPECT neighbors but are not directly connected.

    Uses Common Neighbors heuristic: pairs with many mutual co-suspects
    are likely to also be co-offenders.
    """
    rows = run_query(
        """
        MATCH (a:Person)-[:CO_SUSPECT]-(common:Person)-[:CO_SUSPECT]-(b:Person)
        WHERE a.sfzh < b.sfzh
          AND NOT (a)-[:CO_SUSPECT]-(b)
        WITH a, b, count(DISTINCT common) AS common_neighbors
        WHERE common_neighbors >= $min_common
        RETURN a.sfzh AS source_sfzh,
               a.name AS source_name,
               a.age AS source_age,
               b.sfzh AS target_sfzh,
               b.name AS target_name,
               b.age AS target_age,
               common_neighbors
        ORDER BY common_neighbors DESC
        LIMIT $limit
        """,
        {"min_common": min_common, "limit": limit},
    )
    return {"ok": True, "links": rows, "count": len(rows)}
