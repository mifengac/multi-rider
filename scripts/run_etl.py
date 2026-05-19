from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Iterable

from psycopg2 import sql


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.export_kingbase_latest_samples import get_connection


@dataclass(frozen=True)
class SqlStep:
    name: str
    path: Path
    count_tables: tuple[str, ...]


BUSINESS_TABLES = (
    "jcgkzx_monitor.wcnr_czrk",
    "jcgkzx_monitor.wcnr_rk_zp",
    "jcgkzx_monitor.wcnr_ly_checkin",
    "jcgkzx_monitor.wcnr_ryrl_gj",
)

COUNT_TABLES = (
    "jcgkzx_monitor.wcnr_target_pool",
    *BUSINESS_TABLES,
    "jcgkzx_monitor.wcnr_score",
    "jcgkzx_monitor.wcnr_score_history",
)

SQL_PLAN = (
    SqlStep("ddl_create_tables.sql", SCRIPTS_DIR / "ddl_create_tables.sql", COUNT_TABLES),
    SqlStep("etl_init_target_pool.sql", SCRIPTS_DIR / "etl_init_target_pool.sql", ("jcgkzx_monitor.wcnr_target_pool",)),
    SqlStep("etl_fill_business_tables.sql", SCRIPTS_DIR / "etl_fill_business_tables.sql", BUSINESS_TABLES),
)


def _split_table_name(table_name: str) -> tuple[str, str]:
    parts = table_name.split(".", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(f"Expected schema-qualified table name, got: {table_name}")
    return parts[0], parts[1]


def _table_exists(conn, table_name: str) -> bool:
    schema, table = _split_table_name(table_name)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = %s
                  AND table_name = %s
            )
            """,
            (schema, table),
        )
        return bool(cur.fetchone()[0])


def count_table(conn, table_name: str) -> int | None:
    if not _table_exists(conn, table_name):
        return None
    schema, table = _split_table_name(table_name)
    query = sql.SQL("SELECT COUNT(*) FROM {}.{}").format(
        sql.Identifier(schema),
        sql.Identifier(table),
    )
    with conn.cursor() as cur:
        cur.execute(query)
        return int(cur.fetchone()[0])


def collect_counts(conn, table_names: Iterable[str]) -> dict[str, int | None]:
    return {table_name: count_table(conn, table_name) for table_name in table_names}


def _format_delta(before: int | None, after: int | None) -> str:
    if after is None:
        return "missing"
    if before is None:
        return f"{after} (created)"
    return f"{after} (delta {after - before:+d})"


def execute_sql_file(conn, step: SqlStep) -> int:
    sql_text = step.path.read_text(encoding="utf-8")
    with conn.cursor() as cur:
        cur.execute(sql_text)
        return cur.rowcount


def run_plan() -> dict[str, int | None]:
    with get_connection() as conn:
        try:
            for step in SQL_PLAN:
                print(f"\n== {step.name} ==")
                before = collect_counts(conn, step.count_tables)
                rowcount = execute_sql_file(conn, step)
                after = collect_counts(conn, step.count_tables)
                print(f"cursor_rowcount={rowcount}")
                for table_name in step.count_tables:
                    print(f"{table_name}: {_format_delta(before.get(table_name), after.get(table_name))}")

            final_counts = collect_counts(conn, COUNT_TABLES)
            conn.commit()
            print("\n== final_counts ==")
            for table_name in COUNT_TABLES:
                print(f"{table_name}: {final_counts[table_name]}")
            return final_counts
        except Exception:
            conn.rollback()
            raise


def main() -> int:
    run_plan()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
