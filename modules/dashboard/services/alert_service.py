from shared.db.kingbase import query_all, query_one, execute


def get_recent_alerts(limit: int = 20) -> list[dict]:
    sql = """
        SELECT id, zjhm, xm, alert_type, alert_level, alert_content,
               location, trigger_time, is_read, handle_status
        FROM "jcgkzx_monitoer"."wcnr_alert"
        ORDER BY trigger_time DESC
        LIMIT %(limit)s
    """
    return query_all(sql, {"limit": limit})


def get_alert_count_by_type() -> list[dict]:
    sql = """
        SELECT alert_type AS label, COUNT(*) AS value
        FROM "jcgkzx_monitoer"."wcnr_alert"
        WHERE trigger_time >= CURRENT_DATE - INTERVAL '30 days'
        GROUP BY alert_type
        ORDER BY value DESC
    """
    return query_all(sql)


def mark_alert_read(alert_id: int) -> bool:
    sql = """
        UPDATE "jcgkzx_monitoer"."wcnr_alert"
        SET is_read = TRUE
        WHERE id = %(id)s
    """
    affected = execute(sql, {"id": alert_id})
    return affected > 0


def handle_alert(alert_id: int, status: str) -> bool:
    sql = """
        UPDATE "jcgkzx_monitoer"."wcnr_alert"
        SET handle_status = %(status)s, is_read = TRUE
        WHERE id = %(id)s
    """
    affected = execute(sql, {"id": alert_id, "status": status})
    return affected > 0
