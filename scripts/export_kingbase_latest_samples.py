from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor


# ---------------------------------------------------------------------------
# Single-file configuration
# ---------------------------------------------------------------------------
# Copy this file to the intranet machine and edit these values directly.
# Environment variables with the same names still override these values, so the
# script also works inside the current project without changing this block.
KINGBASE_HOST = "127.0.0.1"
KINGBASE_PORT = 54321
KINGBASE_DBNAME = "yfywk"
KINGBASE_USER = "ywkuser"
KINGBASE_PASSWORD = "123"
KINGBASE_CONNECT_TIMEOUT = 5

DEFAULT_OUTPUT_DIR = "kingbase_latest_samples"


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from contextlib import contextmanager


@contextmanager
def get_connection():
    conn = psycopg2.connect(
        host=os.getenv("KINGBASE_HOST", KINGBASE_HOST),
        port=int(os.getenv("KINGBASE_PORT", str(KINGBASE_PORT))),
        dbname=os.getenv("KINGBASE_DBNAME", KINGBASE_DBNAME),
        user=os.getenv("KINGBASE_USER", KINGBASE_USER),
        password=os.getenv("KINGBASE_PASSWORD", KINGBASE_PASSWORD),
        connect_timeout=int(os.getenv("KINGBASE_CONNECT_TIMEOUT", str(KINGBASE_CONNECT_TIMEOUT))),
    )
    try:
        yield conn
    finally:
        conn.close()


DEFAULT_SCHEMAS = ("ywdata", "stdata", "jcgkzx_monitor")


DEFAULT_TABLES: tuple[tuple[str, str], ...] = (
    # Current code paths / P0 data sources.
    ("ywdata", "t_ap_czrk_jbxx"),
    ("stdata", "b_zdry_ryxx"),
    ("ywdata", "t_dsfb_rk_zpxx"),
    ("ywdata", "zq_zfba_xyrxx"),
    ("ywdata", "zq_zfba_ajxx"),
    ("ywdata", "zq_zfba_wcnr_xyr"),
    ("ywdata", "b_per_dqqkrygj"),
    ("ywdata", "t_spy_ryrlgj_xx"),
    # Business tables from business_database.md / P1 extensions.
    ("ywdata", "zq_kshddpt_dsjfx_jq"),
    ("ywdata", "zq_zfba_xzcfjds"),
    ("ywdata", "zq_zfba_jlz"),
    ("ywdata", "zq_zfba_dbz"),
    ("ywdata", "zq_zfba_qsryxx"),
    ("ywdata", "zq_zfba_saryxx"),
    # Data sources from the project declaration / data checklist.
    ("ywdata", "t_ly_checkin_gn_merge"),
    ("ywdata", "t_ly_checkin_gn"),
    ("ywdata", "t_ly_checkout_gn"),
    ("ywdata", "t_ly_info"),
    ("ywdata", "b_yfszxxxsxx"),
    ("ywdata", "sh_gd_zxxxsxj_xx"),
    ("ywdata", "b_per_qscxwcnr"),
    ("ywdata", "vehicle"),
    ("ywdata", "veh_flow"),
    ("ywdata", "veh_elecbicycle_info"),
    ("ywdata", "b_item_ddzxcdjxxb"),
    ("ywdata", "b_org_yfcsqd"),
    ("stdata", "b_org_yfsylfwcsjc"),
    # Existing / planned app tables in the Kingbase app schema.
    ("jcgkzx_monitor", "hm_graph_sync_log"),
    ("jcgkzx_monitor", "hm_gang_result"),
    ("jcgkzx_monitor", "hm_ai_behavior_label"),
    ("jcgkzx_monitor", "hm_ai_model_version"),
    ("jcgkzx_monitor", "hm_ai_media_asset"),
    ("jcgkzx_monitor", "hm_ai_yolo_run"),
    ("jcgkzx_monitor", "hm_ai_yolo_detection"),
    ("jcgkzx_monitor", "hm_ai_training_sample"),
    ("jcgkzx_monitor", "hm_statistics_metric_snapshot"),
    ("jcgkzx_monitor", "hm_statistics_report_cache"),
    ("jcgkzx_monitor", "hm_sys_user"),
    ("jcgkzx_monitor", "hm_sys_role"),
    ("jcgkzx_monitor", "hm_sys_user_role"),
    ("jcgkzx_monitor", "hm_audit_log"),
    ("jcgkzx_monitor", "hm_sensitive_access_log"),
    ("jcgkzx_monitor", "hm_ruizhi_call_log"),
    ("jcgkzx_monitor", "hm_ai_assistant_session"),
    ("jcgkzx_monitor", "hm_ai_assistant_message"),
    ("jcgkzx_monitor", "hm_ruizhi_kb_mapping"),
    ("jcgkzx_monitor", "hm_ruizhi_kb_file"),
)


TABLE_ORDER_FIELDS: dict[tuple[str, str], tuple[str, ...]] = {
    ("ywdata", "zq_zfba_ajxx"): ("ajxx_lasj", "ajxx_fasj"),
    ("ywdata", "zq_kshddpt_dsjfx_jq"): ("calltime", "occurtime", "updated_at", "created_at"),
    ("ywdata", "zq_zfba_xyrxx"): ("xyrxx_xgsj", "xyrxx_lrsj", "ajxx_join_ajxx_lasj"),
    ("ywdata", "zq_zfba_wcnr_xyr"): ("xyrxx_xgsj", "xyrxx_lrsj", "ajxx_join_ajxx_lasj"),
    ("ywdata", "b_per_dqqkrygj"): ("rksj", "tlkssj"),
    ("ywdata", "t_spy_ryrlgj_xx"): ("shot_time",),
    ("ywdata", "t_ap_czrk_jbxx"): ("gxsj", "cjsj", "bzkrksj", "zakrksj"),
    ("stdata", "b_zdry_ryxx"): ("xgsj", "djsj", "cgsj", "lgsj"),
    ("ywdata", "t_dsfb_rk_zpxx"): ("gxsj", "cjsj"),
    ("ywdata", "zq_zfba_xzcfjds"): ("xzcfjds_xgsj", "xzcfjds_lrsj", "xzcfjds_spsj"),
    ("ywdata", "zq_zfba_jlz"): ("jlz_xgsj", "jlz_lrsj", "jlz_pzsj", "jlz_zxjlsj"),
    ("ywdata", "zq_zfba_dbz"): ("dbz_xgsj", "dbz_lrsj", "dbz_pzdbsj", "dbz_dasj"),
    ("ywdata", "zq_zfba_qsryxx"): ("qsryxx_xgsj", "qsryxx_lrsj", "qsryxx_tfsj"),
    ("ywdata", "zq_zfba_saryxx"): ("saryxx_xgsj", "saryxx_lrsj", "saryxx_wtsj"),
    ("jcgkzx_monitor", "hm_graph_sync_log"): ("sync_start_time", "sync_end_time"),
    ("jcgkzx_monitor", "hm_gang_result"): ("computed_at",),
}


COMMON_ORDER_CANDIDATES = (
    "updated_at",
    "created_at",
    "update_time",
    "create_time",
    "updatetime",
    "createtime",
    "xgsj",
    "lrsj",
    "gxsj",
    "cjsj",
    "rksj",
    "djsj",
    "shot_time",
    "calltime",
    "occurtime",
)


@dataclass
class ExportResult:
    schema: str
    table: str
    exists: bool
    row_count: int
    order_field: str
    csv_path: str
    error: str = ""


def parse_table_name(raw: str) -> tuple[str, str]:
    value = raw.strip().strip('"')
    if "." not in value:
        raise argparse.ArgumentTypeError(f"Table must be schema.table: {raw}")
    schema, table = value.split(".", 1)
    return schema.strip().strip('"'), table.strip().strip('"')


def normalize_key(schema: str, table: str) -> tuple[str, str]:
    return (schema.lower(), table.lower())


def list_tables(conn, schemas: tuple[str, ...]) -> list[tuple[str, str]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_type = 'BASE TABLE'
              AND table_schema = ANY(%s)
            ORDER BY table_schema, table_name
            """,
            (list(schemas),),
        )
        return [(schema, table) for schema, table in cur.fetchall()]


def fetch_columns(conn, schema: str, table: str) -> list[dict[str, str]]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = %s
              AND table_name = %s
            ORDER BY ordinal_position
            """,
            (schema, table),
        )
        return [dict(row) for row in cur.fetchall()]


def choose_order_field(schema: str, table: str, columns: list[dict[str, str]]) -> str:
    if not columns:
        return ""
    column_names = {str(col["column_name"]).lower(): str(col["column_name"]) for col in columns}
    for candidate in TABLE_ORDER_FIELDS.get(normalize_key(schema, table), ()):
        actual = column_names.get(candidate.lower())
        if actual:
            return actual
    for candidate in COMMON_ORDER_CANDIDATES:
        actual = column_names.get(candidate.lower())
        if actual:
            return actual
    timestamp_columns = [
        str(col["column_name"])
        for col in columns
        if "timestamp" in str(col.get("data_type", "")).lower()
        or "date" == str(col.get("data_type", "")).lower()
    ]
    if timestamp_columns:
        return timestamp_columns[0]
    fuzzy = [
        str(col["column_name"])
        for col in columns
        if any(token in str(col["column_name"]).lower() for token in ("time", "date", "sj"))
    ]
    return fuzzy[0] if fuzzy else ""


def fetch_latest_row(conn, schema: str, table: str, order_field: str) -> dict[str, Any] | None:
    query = sql.SQL("SELECT * FROM {}.{}").format(sql.Identifier(schema), sql.Identifier(table))
    if order_field:
        query += sql.SQL(" ORDER BY {} DESC NULLS LAST").format(sql.Identifier(order_field))
    query += sql.SQL(" LIMIT 1")

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query)
        row = cur.fetchone()
        return dict(row) if row else None


def bytes_value(value: Any) -> bytes | None:
    if isinstance(value, bytes):
        return value
    if isinstance(value, bytearray):
        return bytes(value)
    if isinstance(value, memoryview):
        return value.tobytes()
    return None


def make_json_safe(value: Any, binary_dir: Path, field_key: str, inline_bytes: int) -> Any:
    raw_bytes = bytes_value(value)
    if raw_bytes is not None:
        digest = hashlib.sha256(raw_bytes).hexdigest()
        if len(raw_bytes) <= inline_bytes:
            return {
                "__type": "bytes",
                "encoding": "base64",
                "size": len(raw_bytes),
                "sha256": digest,
                "data": base64.b64encode(raw_bytes).decode("ascii"),
            }
        filename = f"{field_key}.{digest[:12]}.bin"
        binary_dir.mkdir(parents=True, exist_ok=True)
        (binary_dir / filename).write_bytes(raw_bytes)
        return {
            "__type": "bytes",
            "encoding": "file",
            "size": len(raw_bytes),
            "sha256": digest,
            "path": str((binary_dir / filename).resolve()),
        }
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def make_csv_safe(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    if value is None:
        return ""
    return str(value)


def export_one_table(
    conn,
    schema: str,
    table: str,
    out_dir: Path,
    inline_bytes: int,
) -> tuple[ExportResult, dict[str, Any] | None]:
    columns = fetch_columns(conn, schema, table)
    if not columns:
        return (
            ExportResult(schema, table, False, 0, "", "", "table not found or no columns visible"),
            None,
        )

    order_field = choose_order_field(schema, table, columns)
    try:
        row = fetch_latest_row(conn, schema, table, order_field)
    except Exception as exc:
        return (ExportResult(schema, table, True, 0, order_field, "", str(exc)), None)

    csv_path = out_dir / f"{schema}.{table}.csv"
    column_names = [str(col["column_name"]) for col in columns]
    binary_dir = out_dir / "binary"
    json_row: dict[str, Any] | None = None
    if row:
        json_row = {
            column: make_json_safe(
                row.get(column),
                binary_dir,
                f"{schema}.{table}.{column}",
                inline_bytes,
            )
            for column in column_names
        }

    with csv_path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=column_names)
        writer.writeheader()
        if json_row:
            writer.writerow({column: make_csv_safe(json_row.get(column)) for column in column_names})

    return (
        ExportResult(
            schema=schema,
            table=table,
            exists=True,
            row_count=1 if row else 0,
            order_field=order_field,
            csv_path=str(csv_path.resolve()),
        ),
        json_row,
    )


def write_manifest(out_dir: Path, results: list[ExportResult]) -> None:
    manifest_rows = [result.__dict__ for result in results]
    with (out_dir / "manifest.json").open("w", encoding="utf-8") as fh:
        json.dump(manifest_rows, fh, ensure_ascii=False, indent=2)
    with (out_dir / "manifest.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=("schema", "table", "exists", "row_count", "order_field", "csv_path", "error"),
        )
        writer.writeheader()
        writer.writerows(manifest_rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export the latest one-row sample from Kingbase tables."
    )
    parser.add_argument(
        "--out-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory. Default: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--schemas",
        nargs="+",
        default=list(DEFAULT_SCHEMAS),
        help="Schemas used with --all-tables. Default: ywdata stdata jcgkzx_monitor",
    )
    parser.add_argument(
        "--all-tables",
        action="store_true",
        help="Export one latest row from every table in --schemas instead of the built-in project table list.",
    )
    parser.add_argument(
        "--table",
        action="append",
        type=parse_table_name,
        help="Extra table to export, format schema.table. Can be repeated.",
    )
    parser.add_argument(
        "--inline-bytes",
        type=int,
        default=8192,
        help="Inline bytea fields as base64 up to this many bytes; larger values are written under binary/.",
    )
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = Path.cwd() / out_dir
    if out_dir.name == DEFAULT_OUTPUT_DIR:
        out_dir = out_dir / timestamp
    out_dir.mkdir(parents=True, exist_ok=True)

    with get_connection() as conn:
        if args.all_tables:
            tables = list_tables(conn, tuple(args.schemas))
        else:
            tables = list(DEFAULT_TABLES)
        if args.table:
            tables.extend(args.table)

        seen: set[tuple[str, str]] = set()
        unique_tables: list[tuple[str, str]] = []
        for schema, table in tables:
            key = normalize_key(schema, table)
            if key in seen:
                continue
            seen.add(key)
            unique_tables.append((schema, table))

        results: list[ExportResult] = []
        samples: dict[str, Any] = {}
        for index, (schema, table) in enumerate(unique_tables, 1):
            print(f"[{index}/{len(unique_tables)}] exporting {schema}.{table} ...", flush=True)
            result, row = export_one_table(conn, schema, table, out_dir, max(0, args.inline_bytes))
            results.append(result)
            samples[f"{schema}.{table}"] = {
                "schema": schema,
                "table": table,
                "exists": result.exists,
                "row_count": result.row_count,
                "order_field": result.order_field,
                "csv_path": result.csv_path,
                "error": result.error,
                "row": row,
            }

    with (out_dir / "all_samples.json").open("w", encoding="utf-8") as fh:
        json.dump(samples, fh, ensure_ascii=False, indent=2)
    write_manifest(out_dir, results)

    ok_count = sum(1 for result in results if result.exists and not result.error)
    row_count = sum(result.row_count for result in results)
    print(f"Done. tables_ok={ok_count}, rows_exported={row_count}, out_dir={out_dir.resolve()}")
    print(f"Manifest: {(out_dir / 'manifest.csv').resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
