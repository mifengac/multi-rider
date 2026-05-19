from __future__ import annotations

import argparse
import base64
import csv
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor, execute_values


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR = PROJECT_ROOT / "mock_database_samples" / "kingbase"
ALLOWED_SCHEMAS = {"ywdata", "stdata"}
BLOCKED_TABLES = {("jcgkzx_monitor", "wcnr_10lv_manual_exclude")}

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.export_kingbase_latest_samples import (  # noqa: E402
    KINGBASE_DBNAME,
    KINGBASE_HOST,
    KINGBASE_PORT,
    get_connection,
)


@dataclass(frozen=True)
class InsertPlan:
    insert_columns: list[str]
    column_types: dict[str, str]
    skipped_csv_columns: list[str]
    missing_real_columns: list[str]
    column_max_lengths: dict[str, int | None] = field(default_factory=dict)
    column_numeric_limits: dict[str, tuple[int | None, int | None]] = field(default_factory=dict)
    column_required: dict[str, bool] = field(default_factory=dict)


@dataclass(frozen=True)
class LoadResult:
    schema: str
    table: str
    csv_rows: int
    real_columns: int
    insert_columns: int
    skipped_csv_columns: list[str]
    missing_real_columns: list[str]
    rejected_columns: list[str]
    inserted_rows: int
    status: str = "loaded"


def parse_csv_table_path(path: Path) -> tuple[str, str]:
    if path.suffix.lower() != ".csv":
        raise ValueError(f"Expected .csv file: {path}")
    stem = path.stem
    if "." not in stem:
        raise ValueError(f"Expected schema.table.csv file name: {path.name}")
    schema, table = stem.split(".", 1)
    if not schema or not table:
        raise ValueError(f"Expected schema.table.csv file name: {path.name}")
    return schema, table


def is_allowed_local_target(host: str, port: str | int, dbname: str) -> bool:
    return str(host).strip() == "127.0.0.1" and str(port).strip() == "54321" and dbname == "yfywk"


def ensure_safe_target() -> None:
    host = os.getenv("KINGBASE_HOST", KINGBASE_HOST)
    port = os.getenv("KINGBASE_PORT", str(KINGBASE_PORT))
    dbname = os.getenv("KINGBASE_DBNAME", KINGBASE_DBNAME)
    if not is_allowed_local_target(host, port, dbname):
        raise RuntimeError(
            "Refusing to load mock data outside the local clone "
            f"127.0.0.1:54321/yfywk; effective target is {host}:{port}/{dbname}"
        )


def fetch_columns(conn, schema: str, table: str) -> list[dict[str, str]]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT column_name, data_type
                 , character_maximum_length
                 , numeric_precision
                 , numeric_scale
                 , is_nullable
                 , column_default
            FROM information_schema.columns
            WHERE table_schema = %s
              AND table_name = %s
            ORDER BY ordinal_position
            """,
            (schema, table),
        )
        return [dict(row) for row in cur.fetchall()]


def build_insert_plan(csv_columns: Iterable[str], real_columns: list[dict[str, str]]) -> InsertPlan:
    csv_column_list = list(csv_columns)
    csv_by_lower = {column.lower(): column for column in csv_column_list}
    real_names = [str(column["column_name"]) for column in real_columns]
    real_types = {
        str(column["column_name"]): str(column.get("data_type", ""))
        for column in real_columns
    }
    real_max_lengths = {
        str(column["column_name"]): column.get("character_maximum_length")
        for column in real_columns
    }
    real_numeric_limits = {
        str(column["column_name"]): (
            column.get("numeric_precision"),
            column.get("numeric_scale"),
        )
        for column in real_columns
    }
    real_required = {
        str(column["column_name"]): str(column.get("is_nullable", "")).upper() == "NO"
        for column in real_columns
    }
    real_lower = {column.lower(): column for column in real_names}

    insert_columns = [column for column in real_names if column.lower() in csv_by_lower]
    skipped_csv_columns = [column for column in csv_column_list if column.lower() not in real_lower]
    missing_real_columns = [column for column in real_names if column.lower() not in csv_by_lower]
    column_types = {column: real_types[column] for column in insert_columns}
    column_max_lengths = {column: real_max_lengths.get(column) for column in insert_columns}
    column_numeric_limits = {
        column: real_numeric_limits.get(column, (None, None))
        for column in insert_columns
    }
    column_required = {column: real_required.get(column, False) for column in insert_columns}
    return InsertPlan(
        insert_columns,
        column_types,
        skipped_csv_columns,
        missing_real_columns,
        column_max_lengths,
        column_numeric_limits,
        column_required,
    )


def _is_empty(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def _is_timestamp_value(value: str) -> bool:
    text = value.strip()
    if len(text) == 14 and text.isdigit():
        try:
            datetime.strptime(text, "%Y%m%d%H%M%S")
            return True
        except ValueError:
            return False
    try:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def _is_date_value(value: str) -> bool:
    text = value.strip()
    try:
        date.fromisoformat(text[:10])
        return True
    except ValueError:
        return _is_timestamp_value(text)


def _fits_numeric_limit(value: Decimal, precision: int | None, scale: int | None) -> bool:
    if precision is None or scale is None:
        return True
    normalized = value.copy_abs().normalize()
    integer_digits = max(normalized.adjusted() + 1, 0)
    return integer_digits <= int(precision) - int(scale)


def is_value_compatible(
    value: Any,
    data_type: str,
    max_length: int | None = None,
    numeric_limit: tuple[int | None, int | None] = (None, None),
) -> bool:
    if _is_empty(value):
        return True
    text = str(value).strip()
    normalized_type = data_type.lower()
    if max_length is not None and normalized_type in {
        "character varying",
        "character",
        "char",
        "varchar",
    }:
        return len(text) <= int(max_length)
    if "timestamp" in normalized_type:
        return _is_timestamp_value(text)
    if normalized_type == "date":
        return _is_date_value(text)
    if normalized_type in {"integer", "bigint", "smallint"}:
        try:
            int(text)
            return True
        except ValueError:
            return False
    if normalized_type in {"numeric", "decimal", "real", "double precision"}:
        try:
            decimal_value = Decimal(text)
            if normalized_type in {"numeric", "decimal"}:
                return _fits_numeric_limit(decimal_value, numeric_limit[0], numeric_limit[1])
            return True
        except (InvalidOperation, ValueError):
            return False
    if normalized_type == "boolean":
        return text.lower() in {"true", "false", "t", "f", "1", "0", "yes", "no", "y", "n"}
    return True


def filter_compatible_columns(
    plan: InsertPlan,
    raw_rows: list[dict[str, Any]],
    csv_lookup: dict[str, str],
) -> tuple[InsertPlan, list[str]]:
    rejected: list[str] = []
    for column in plan.insert_columns:
        csv_column = csv_lookup[column.lower()]
        data_type = plan.column_types[column]
        max_length = plan.column_max_lengths.get(column)
        numeric_limit = plan.column_numeric_limits.get(column, (None, None))
        if any(
            not is_value_compatible(row.get(csv_column), data_type, max_length, numeric_limit)
            for row in raw_rows
        ):
            rejected.append(column)

    if not rejected:
        return plan, []

    rejected_set = set(rejected)
    insert_columns = [column for column in plan.insert_columns if column not in rejected_set]
    return (
        InsertPlan(
            insert_columns=insert_columns,
            column_types={column: plan.column_types[column] for column in insert_columns},
            skipped_csv_columns=plan.skipped_csv_columns,
            missing_real_columns=plan.missing_real_columns,
            column_max_lengths={column: plan.column_max_lengths.get(column) for column in insert_columns},
            column_numeric_limits={
                column: plan.column_numeric_limits.get(column, (None, None))
                for column in insert_columns
            },
            column_required={column: plan.column_required.get(column, False) for column in insert_columns},
        ),
        rejected,
    )


def _decode_json_bytea(value: str) -> bytes | None:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict) or parsed.get("__type") != "bytes":
        return None

    encoding = str(parsed.get("encoding", "")).lower()
    if encoding == "base64" and parsed.get("data"):
        return base64.b64decode(str(parsed["data"]), validate=True)
    if encoding == "file" and parsed.get("path"):
        path = Path(str(parsed["path"]))
        if path.is_file():
            return path.read_bytes()
        return str(parsed["path"]).encode("utf-8")
    return json.dumps(parsed, ensure_ascii=False).encode("utf-8")


def _decode_plain_bytea(value: str) -> bytes:
    if value.startswith("\\x"):
        try:
            return bytes.fromhex(value[2:])
        except ValueError:
            pass
    try:
        return base64.b64decode(value, validate=True)
    except Exception:
        return value.encode("utf-8")


def adapt_value(value: Any, data_type: str) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "":
            return None
        value = stripped

    if data_type.lower() == "bytea":
        if isinstance(value, bytes):
            return value
        if isinstance(value, bytearray):
            return bytes(value)
        if isinstance(value, memoryview):
            return value.tobytes()
        text_value = str(value)
        decoded = _decode_json_bytea(text_value)
        return decoded if decoded is not None else _decode_plain_bytea(text_value)

    return value


def _required_default(data_type: str) -> Any:
    normalized_type = data_type.lower()
    if normalized_type == "bytea":
        return b""
    if "timestamp" in normalized_type:
        return "1970-01-01T00:00:00"
    if normalized_type == "date":
        return "1970-01-01"
    if normalized_type in {"integer", "bigint", "smallint", "numeric", "decimal", "real", "double precision"}:
        return 0
    if normalized_type == "boolean":
        return False
    return "0"


def coerce_value(value: Any, data_type: str, required: bool = False) -> Any:
    adapted = adapt_value(value, data_type)
    if adapted is None and required:
        return _required_default(data_type)
    return adapted


def _truncate_table(conn, schema: str, table: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            sql.SQL("TRUNCATE TABLE {}.{}").format(
                sql.Identifier(schema),
                sql.Identifier(table),
            )
        )


def _insert_rows(conn, schema: str, table: str, columns: list[str], rows: list[tuple[Any, ...]]) -> int:
    if not rows:
        return 0
    query = sql.SQL("INSERT INTO {}.{} ({}) VALUES %s").format(
        sql.Identifier(schema),
        sql.Identifier(table),
        sql.SQL(", ").join(sql.Identifier(column) for column in columns),
    )
    with conn.cursor() as cur:
        execute_values(cur, query, rows, page_size=1000)
        return len(rows)


def load_csv_file(conn, path: Path) -> LoadResult:
    schema, table = parse_csv_table_path(path)
    if (schema, table) in BLOCKED_TABLES:
        return LoadResult(schema, table, 0, 0, 0, [], [], [], 0, "blocked")
    if schema not in ALLOWED_SCHEMAS:
        return LoadResult(schema, table, 0, 0, 0, [], [], [], 0, "skipped_schema")

    columns = fetch_columns(conn, schema, table)
    if not columns:
        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            csv_rows = sum(1 for _ in csv.DictReader(fh))
        return LoadResult(schema, table, csv_rows, 0, 0, [], [], [], 0, "missing_table")

    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        csv_columns = reader.fieldnames or []
        plan = build_insert_plan(csv_columns, columns)
        csv_lookup = {column.lower(): column for column in csv_columns}
        raw_rows = list(reader)
        plan, rejected_columns = filter_compatible_columns(plan, raw_rows, csv_lookup)
        rows: list[tuple[Any, ...]] = []
        for row in raw_rows:
            rows.append(
                tuple(
                    coerce_value(
                        row.get(csv_lookup[column.lower()]),
                        plan.column_types[column],
                        plan.column_required.get(column, False),
                    )
                    for column in plan.insert_columns
                )
            )

    _truncate_table(conn, schema, table)
    inserted_rows = _insert_rows(conn, schema, table, plan.insert_columns, rows)
    return LoadResult(
        schema=schema,
        table=table,
        csv_rows=len(rows),
        real_columns=len(columns),
        insert_columns=len(plan.insert_columns),
        skipped_csv_columns=plan.skipped_csv_columns,
        missing_real_columns=plan.missing_real_columns,
        rejected_columns=rejected_columns,
        inserted_rows=inserted_rows,
    )


def _format_columns(columns: list[str], max_items: int = 8) -> str:
    if not columns:
        return "-"
    visible = columns[:max_items]
    suffix = "" if len(columns) <= max_items else f" ...(+{len(columns) - max_items})"
    return ",".join(visible) + suffix


def print_result(result: LoadResult) -> None:
    print(
        f"{result.schema}.{result.table}: status={result.status} "
        f"csv_rows={result.csv_rows} real_cols={result.real_columns} "
        f"insert_cols={result.insert_columns} inserted={result.inserted_rows} "
        f"skipped=[{_format_columns(result.skipped_csv_columns)}] "
        f"missing=[{_format_columns(result.missing_real_columns)}] "
        f"rejected=[{_format_columns(result.rejected_columns)}]",
        flush=True,
    )


def load_all(input_dir: Path) -> list[LoadResult]:
    ensure_safe_target()
    csv_files = sorted(input_dir.glob("*.csv"))
    results: list[LoadResult] = []
    with get_connection() as conn:
        try:
            for path in csv_files:
                result = load_csv_file(conn, path)
                print_result(result)
                results.append(result)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Load mock CSV data into the local KingBase clone.")
    parser.add_argument(
        "--input-dir",
        default=str(DEFAULT_INPUT_DIR),
        help=f"CSV directory. Default: {DEFAULT_INPUT_DIR}",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    if not input_dir.is_absolute():
        input_dir = PROJECT_ROOT / input_dir
    results = load_all(input_dir)
    loaded = sum(1 for result in results if result.status == "loaded")
    inserted = sum(result.inserted_rows for result in results)
    print(f"Done. loaded_tables={loaded}, inserted_rows={inserted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
