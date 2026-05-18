from shared.db.kingbase import query_all


def find_shortest_path(from_zjhm: str, to_zjhm: str, max_hops: int = 4) -> dict:
    """BFS to find shortest path between two persons via co-suspect relationships."""
    if from_zjhm == to_zjhm:
        return {"found": True, "path": [from_zjhm], "hops": 0}

    visited = {from_zjhm}
    queue = [(from_zjhm, [from_zjhm])]

    for _ in range(max_hops):
        next_queue = []
        for current, path in queue:
            neighbors = _get_co_suspects(current)
            for neighbor_zjhm in neighbors:
                if neighbor_zjhm == to_zjhm:
                    return {"found": True, "path": path + [to_zjhm], "hops": len(path)}
                if neighbor_zjhm not in visited:
                    visited.add(neighbor_zjhm)
                    next_queue.append((neighbor_zjhm, path + [neighbor_zjhm]))
        queue = next_queue
        if not queue:
            break

    return {"found": False, "path": [], "hops": -1}


def _get_co_suspects(zjhm: str) -> list[str]:
    sql = """
        SELECT DISTINCT x2."xyrxx_sfzh"
        FROM "ywdata"."zq_zfba_xyrxx" x1
        JOIN "ywdata"."zq_zfba_xyrxx" x2
          ON x2."ajxx_join_ajxx_ajbh" = x1."ajxx_join_ajxx_ajbh"
          AND x2."xyrxx_sfzh" <> x1."xyrxx_sfzh"
        WHERE x1."xyrxx_sfzh" = %(zjhm)s
          AND NULLIF(BTRIM(COALESCE(x2."xyrxx_sfzh", '')), '') IS NOT NULL
    """
    rows = query_all(sql, {"zjhm": zjhm})
    return [r["xyrxx_sfzh"] for r in rows if r.get("xyrxx_sfzh")]
