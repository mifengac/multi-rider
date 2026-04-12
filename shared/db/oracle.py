from datetime import datetime
import os
from typing import List, Tuple

from shared.config.config import (
    INSTANT_CLIENT_DIR,
    ORACLE_HOST,
    ORACLE_PASSWORD,
    ORACLE_PORT,
    ORACLE_SERVICE,
    ORACLE_USER,
    SMS_ORACLE_HOST,
    SMS_ORACLE_PASSWORD,
    SMS_ORACLE_PORT,
    SMS_ORACLE_SERVICE,
    SMS_ORACLE_USER,
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


_ORACLE_CLIENT_READY = False


def _prepare_windows_oracle_dll_path() -> None:
    if os.name != "nt":
        return
    if not os.path.isdir(INSTANT_CLIENT_DIR):
        logger.warning("Oracle Instant Client directory not found: %s", INSTANT_CLIENT_DIR)
        return
    try:
        os.add_dll_directory(INSTANT_CLIENT_DIR)
        logger.info("Added Oracle DLL directory: %s", INSTANT_CLIENT_DIR)
    except Exception as exc:
        logger.warning("Failed to add Oracle DLL directory %s: %s", INSTANT_CLIENT_DIR, exc)


def init_oracle_client_if_needed() -> None:
    global _ORACLE_CLIENT_READY
    if _ORACLE_CLIENT_READY:
        return

    _prepare_windows_oracle_dll_path()

    if oracledb is not None and hasattr(oracledb, "init_oracle_client"):
        try:
            oracledb.init_oracle_client(lib_dir=INSTANT_CLIENT_DIR)
            _ORACLE_CLIENT_READY = True
            logger.info("Oracle client initialized with lib_dir=%s", INSTANT_CLIENT_DIR)
        except Exception as exc:
            logger.warning("init_oracle_client failed: %s", exc)
    elif cx_oracle is not None:
        try:
            cx_oracle.init_oracle_client(lib_dir=INSTANT_CLIENT_DIR)
            _ORACLE_CLIENT_READY = True
            logger.info("cx_Oracle client initialized with lib_dir=%s", INSTANT_CLIENT_DIR)
        except Exception as exc:
            logger.warning("cx_Oracle init failed: %s", exc)


def _connect_oracle(host: str, port: int, service: str, user: str, password: str):
    dsn = f"{host}:{port}/{service}"
    if oracledb is not None:
        return oracledb.connect(user=user, password=password, dsn=dsn)
    if cx_oracle is not None:
        return cx_oracle.connect(user=user, password=password, dsn=dsn)
    raise RuntimeError("Oracle driver not available")


# ---------------------------------------------------------------------------
# Connection pools – reuse TCP connections instead of connect-per-query.
# Pools are created lazily on first use and kept for the process lifetime.
# ---------------------------------------------------------------------------
_oracle_pool = None
_sms_oracle_pool = None


def _create_pool(host: str, port: int, service: str, user: str, password: str):
    """Create an oracledb connection pool (falls back to single-connect if
    the driver does not support pooling)."""
    dsn = f"{host}:{port}/{service}"
    if oracledb is not None and hasattr(oracledb, "create_pool"):
        return oracledb.create_pool(
            user=user, password=password, dsn=dsn,
            min=2, max=8, increment=1,
        )
    # cx_Oracle pool (older driver)
    if cx_oracle is not None and hasattr(cx_oracle, "SessionPool"):
        return cx_oracle.SessionPool(
            user=user, password=password, dsn=dsn,
            min=2, max=8, increment=1,
        )
    return None


def _get_oracle_pool():
    global _oracle_pool
    if _oracle_pool is None:
        _oracle_pool = _create_pool(
            ORACLE_HOST, ORACLE_PORT, ORACLE_SERVICE, ORACLE_USER, ORACLE_PASSWORD,
        )
    return _oracle_pool


def _get_sms_oracle_pool():
    global _sms_oracle_pool
    if _sms_oracle_pool is None:
        _sms_oracle_pool = _create_pool(
            SMS_ORACLE_HOST, SMS_ORACLE_PORT, SMS_ORACLE_SERVICE,
            SMS_ORACLE_USER, SMS_ORACLE_PASSWORD,
        )
    return _sms_oracle_pool


def get_oracle_connection():
    pool = _get_oracle_pool()
    if pool is not None:
        return pool.acquire()
    return _connect_oracle(ORACLE_HOST, ORACLE_PORT, ORACLE_SERVICE, ORACLE_USER, ORACLE_PASSWORD)


def get_sms_oracle_connection():
    pool = _get_sms_oracle_pool()
    if pool is not None:
        return pool.acquire()
    return _connect_oracle(
        SMS_ORACLE_HOST,
        SMS_ORACLE_PORT,
        SMS_ORACLE_SERVICE,
        SMS_ORACLE_USER,
        SMS_ORACLE_PASSWORD,
    )


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


def fetch_dispatch_person_context(id_number: str) -> dict:
    safe_id_number = str(id_number or "").strip()
    if not safe_id_number:
        return {}

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
        WHERE gmsfhm = :id_number
          AND ROWNUM = 1
    """
    init_oracle_client_if_needed()
    with get_oracle_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, {"id_number": safe_id_number})
            row = cursor.fetchone()

    if not row:
        return {}

    keys = [
        "xm",
        "lxdh",
        "ds",
        "dsmc",
        "ssxq",
        "ssxqmc",
        "pcs",
        "pcsmc",
        "dz",
    ]
    return {
        key: (str(value).strip() if value is not None else "")
        for key, value in zip(keys, row)
    }


def insert_sms_queue_record(payload: dict) -> None:
    sql = """
        INSERT INTO yfgadb.dfsdl (
            id, mobile, content, deadtime, status, eid, userid, password, userport
        ) VALUES (
            yfgadb.seq_sendsms.nextval, :mobile, :content, SYSDATE, :status, :eid, :userid, :password, :userport
        )
    """
    binds = {
        "mobile": str(payload.get("mobile", "") or "").strip(),
        "content": str(payload.get("content", "") or "").strip(),
        "status": str(payload.get("status", "0") or "0").strip(),
        "eid": str(payload.get("eid", "") or "").strip(),
        "userid": str(payload.get("userid", "") or "").strip(),
        "password": str(payload.get("password", "") or "").strip(),
        "userport": str(payload.get("userport", "") or "").strip(),
    }
    init_oracle_client_if_needed()
    with get_sms_oracle_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, binds)
        conn.commit()
