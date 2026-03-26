from __future__ import annotations

from config import (
    FACE_SQL_DB,
    FACE_SQL_ENABLED,
    FACE_SQL_HOST,
    FACE_SQL_PASSWORD,
    FACE_SQL_PORT,
    FACE_SQL_USER,
)


def _ensure_face_sql_ready() -> None:
    if not FACE_SQL_ENABLED:
        raise RuntimeError("face SQL sync is disabled by FACE_SQL_ENABLED")
    if not (FACE_SQL_HOST and FACE_SQL_DB and FACE_SQL_USER):
        raise RuntimeError("face SQL connection is not fully configured")


def fetch_dispatch_person_context(id_number: str) -> dict:
    safe_id_number = str(id_number or "").strip()
    if not safe_id_number:
        return {}

    _ensure_face_sql_ready()

    try:
        import psycopg2
        import psycopg2.extras
    except Exception as exc:
        raise RuntimeError(f"psycopg2-binary is not installed: {exc}") from exc

    sql = """
        SELECT
            xm,
            lxdh,
            ds,
            dsmc,
            ssxq,
            ssxqmc,
            pcs,
            pcsmc,
            dz
        FROM ywdata.t_ap_czrk_jbxx
        WHERE gmsfhm = %(id_number)s
        LIMIT 1
    """

    with psycopg2.connect(
        host=FACE_SQL_HOST,
        port=FACE_SQL_PORT,
        dbname=FACE_SQL_DB,
        user=FACE_SQL_USER,
        password=FACE_SQL_PASSWORD,
    ) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, {"id_number": safe_id_number})
            row = cur.fetchone()

    if not row:
        return {}

    keys = ["xm", "lxdh", "ds", "dsmc", "ssxq", "ssxqmc", "pcs", "pcsmc", "dz"]
    return {
        key: (str(row.get(key)).strip() if row.get(key) is not None else "")
        for key in keys
    }
