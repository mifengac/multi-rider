from __future__ import annotations

import sys
from pathlib import Path


def test_run_etl_plan_uses_expected_sql_files_and_safe_tables():
    repo_root = str(Path(__file__).resolve().parents[1])
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    from scripts import run_etl

    assert [step.name for step in run_etl.SQL_PLAN] == [
        "ddl_create_tables.sql",
        "etl_init_target_pool.sql",
        "etl_fill_business_tables.sql",
    ]
    assert "jcgkzx_monitor.wcnr_10lv_manual_exclude" not in run_etl.COUNT_TABLES
    assert run_etl.BUSINESS_TABLES == (
        "jcgkzx_monitor.wcnr_czrk",
        "jcgkzx_monitor.wcnr_rk_zp",
        "jcgkzx_monitor.wcnr_ly_checkin",
        "jcgkzx_monitor.wcnr_ryrl_gj",
    )


def test_target_pool_id_validator_avoids_empty_string_comparison():
    sql_text = (Path(__file__).resolve().parents[1] / "scripts" / "etl_init_target_pool.sql").read_text(
        encoding="utf-8"
    )

    assert "id_no <> ''" not in sql_text
    assert "id_no IS NOT NULL" in sql_text


def test_face_trajectory_etl_outputs_non_null_mock_coordinates():
    sql_text = (
        Path(__file__).resolve().parents[1] / "scripts" / "etl_fill_business_tables.sql"
    ).read_text(encoding="utf-8")

    assert "NULL::NUMERIC AS jd" not in sql_text
    assert "NULL::NUMERIC AS wd" not in sql_text
    assert "112.0::NUMERIC AS jd" in sql_text
    assert "22.9::NUMERIC AS wd" in sql_text
