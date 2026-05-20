#!/usr/bin/env uv run
"""Execute SQL migration scripts in version order."""
from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.db.kingbase import execute  # noqa: E402


def run_migrations(sql_dir: str = "scripts/sql") -> bool:
    path = Path(sql_dir)
    if not path.is_absolute():
        path = PROJECT_ROOT / path

    scripts = sorted(path.glob("v*.sql"))
    for script in scripts:
        print(f"Running {script.name}...")
        sql = script.read_text(encoding="utf-8")
        try:
            execute(sql)
            print(f"  OK {script.name} completed")
        except Exception as exc:
            print(f"  FAIL {script.name} failed: {exc}", file=sys.stderr)
            return False
    return True


def main() -> int:
    return 0 if run_migrations() else 1


if __name__ == "__main__":
    raise SystemExit(main())
