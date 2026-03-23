from datetime import datetime
from typing import List, Tuple

from config import (
    INSTANT_CLIENT_DIR,
    ORACLE_HOST,
    ORACLE_PASSWORD,
    ORACLE_PORT,
    ORACLE_SERVICE,
    ORACLE_USER,
    logger,
)


try:
    import oracledb
except Exception:
    oracledb = None
    try:
        import cx_Oracle as cx_oracle
    except Exception:
        cx_oracle = None
else:
    cx_oracle = None


def init_oracle_client_if_needed() -> None:
    if oracledb is not None and hasattr(oracledb, "init_oracle_client"):
        try:
            oracledb.init_oracle_client(lib_dir=INSTANT_CLIENT_DIR)
        except Exception as exc:
            logger.warning("init_oracle_client failed: %s", exc)
    elif cx_oracle is not None:
        try:
            cx_oracle.init_oracle_client(lib_dir=INSTANT_CLIENT_DIR)
        except Exception as exc:
            logger.warning("cx_Oracle init failed: %s", exc)


def get_oracle_connection():
    dsn = f"{ORACLE_HOST}:{ORACLE_PORT}/{ORACLE_SERVICE}"
    if oracledb is not None:
        return oracledb.connect(user=ORACLE_USER, password=ORACLE_PASSWORD, dsn=dsn)
    if cx_oracle is not None:
        return cx_oracle.connect(user=ORACLE_USER, password=ORACLE_PASSWORD, dsn=dsn)
    raise RuntimeError("Oracle driver not available")


def build_query_and_binds(
    kssj: str,
    jssj: str,
    hours: List[str],
    model_key: str,
) -> tuple[str, dict]:
    sql = (
        "SELECT PIC_ABBREVIATE, TIME FROM yfgadb.T_SPY_ELCZP_XX "
        "WHERE TIME BETWEEN :kssj AND :jssj"
    )
    binds = {"kssj": kssj, "jssj": jssj}

    if hours:
        placeholders = []
        for index, hour in enumerate(hours):
            key = f"h{index}"
            placeholders.append(f":{key}")
            binds[key] = hour
        sql += f" AND HOUR IN ({','.join(placeholders)})"

    if model_key == "bczj":
        sql += " AND 1=1"

    return sql, binds


def fetch_image_urls(
    kssj: str,
    jssj: str,
    hours: List[str],
    model_key: str,
) -> List[Tuple[str, str]]:
    sql, binds = build_query_and_binds(kssj, jssj, hours, model_key)
    init_oracle_client_if_needed()
    with get_oracle_connection() as conn:
        with conn.cursor() as cursor:
            try:
                cursor.execute("ALTER SESSION SET NLS_DATE_FORMAT = 'YYYY-MM-DD HH24:MI:SS'")
            except Exception:
                pass
            cursor.execute(sql, binds)
            rows = cursor.fetchall()

    output: List[Tuple[str, str]] = []
    for row in rows:
        if not row or not row[0]:
            continue
        url = row[0]
        value = row[1] if len(row) > 1 else None
        if isinstance(value, datetime):
            time_str = value.strftime("%Y-%m-%d %H:%M:%S")
        else:
            time_str = str(value) if value else ""
        output.append((url, time_str))
    return output
