from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


def _import_loader():
    repo_root = str(Path(__file__).resolve().parents[1])
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    from scripts import load_mock_data

    return load_mock_data


def test_parse_csv_table_path_requires_schema_table_csv():
    loader = _import_loader()

    assert loader.parse_csv_table_path(Path("ywdata.t_ap_czrk_jbxx.csv")) == (
        "ywdata",
        "t_ap_czrk_jbxx",
    )

    with pytest.raises(ValueError):
        loader.parse_csv_table_path(Path("t_ap_czrk_jbxx.csv"))


def test_build_insert_plan_uses_real_table_columns_and_reports_drift():
    loader = _import_loader()

    real_columns = [
        {"column_name": "id", "data_type": "bigint"},
        {"column_name": "gmsfhm", "data_type": "character varying"},
        {"column_name": "xp", "data_type": "bytea"},
        {"column_name": "created_at", "data_type": "timestamp without time zone"},
    ]
    plan = loader.build_insert_plan(
        ["gmsfhm", "ignored_extra", "xp"],
        real_columns,
    )

    assert plan.insert_columns == ["gmsfhm", "xp"]
    assert plan.column_types == {"gmsfhm": "character varying", "xp": "bytea"}
    assert plan.skipped_csv_columns == ["ignored_extra"]
    assert plan.missing_real_columns == ["id", "created_at"]


def test_adapt_value_turns_empty_strings_null_and_decodes_bytea(tmp_path):
    loader = _import_loader()

    assert loader.adapt_value("", "character varying") is None
    assert loader.adapt_value("  ", "text") is None
    assert loader.adapt_value("2026-05-14T12:30:00", "timestamp without time zone") == (
        "2026-05-14T12:30:00"
    )

    assert loader.adapt_value(
        json.dumps({"__type": "bytes", "encoding": "base64", "data": "aGVsbG8="}),
        "bytea",
    ) == b"hello"

    binary_path = tmp_path / "photo.bin"
    binary_path.write_bytes(b"photo")
    assert loader.adapt_value(
        json.dumps({"__type": "bytes", "encoding": "file", "path": str(binary_path)}),
        "bytea",
    ) == b"photo"


def test_filter_compatible_columns_skips_misaligned_timestamp_values():
    loader = _import_loader()

    plan = loader.InsertPlan(
        insert_columns=["zjhm", "djsj", "score"],
        column_types={
            "zjhm": "character varying",
            "djsj": "timestamp without time zone",
            "score": "integer",
        },
        skipped_csv_columns=[],
        missing_real_columns=[],
    )
    filtered_plan, rejected_columns = loader.filter_compatible_columns(
        plan,
        [{"zjhm": "441702201202196991", "djsj": "02", "score": "7"}],
        {"zjhm": "zjhm", "djsj": "djsj", "score": "score"},
    )

    assert filtered_plan.insert_columns == ["zjhm", "score"]
    assert filtered_plan.column_types == {"zjhm": "character varying", "score": "integer"}
    assert rejected_columns == ["djsj"]


def test_filter_compatible_columns_skips_values_over_character_limit():
    loader = _import_loader()

    plan = loader.InsertPlan(
        insert_columns=["gmsfhm", "zt"],
        column_types={"gmsfhm": "character varying", "zt": "character varying"},
        skipped_csv_columns=[],
        missing_real_columns=[],
        column_max_lengths={"gmsfhm": 18, "zt": 2},
    )
    filtered_plan, rejected_columns = loader.filter_compatible_columns(
        plan,
        [{"gmsfhm": "441702201202196991", "zt": "2026-05-02T04:35:49"}],
        {"gmsfhm": "gmsfhm", "zt": "zt"},
    )

    assert filtered_plan.insert_columns == ["gmsfhm"]
    assert rejected_columns == ["zt"]


def test_filter_compatible_columns_skips_numeric_precision_overflow():
    loader = _import_loader()

    plan = loader.InsertPlan(
        insert_columns=["hphm", "xsjg"],
        column_types={"hphm": "character varying", "xsjg": "numeric"},
        skipped_csv_columns=[],
        missing_real_columns=[],
        column_numeric_limits={"xsjg": (8, 0)},
    )
    filtered_plan, rejected_columns = loader.filter_compatible_columns(
        plan,
        [{"hphm": "粤W52SBF", "xsjg": "26517939256867"}],
        {"hphm": "hphm", "xsjg": "xsjg"},
    )

    assert filtered_plan.insert_columns == ["hphm"]
    assert rejected_columns == ["xsjg"]


def test_coerce_value_supplies_type_safe_required_defaults():
    loader = _import_loader()

    assert loader.coerce_value("", "numeric", required=True) == 0
    assert loader.coerce_value("", "integer", required=True) == 0
    assert loader.coerce_value("", "boolean", required=True) is False
    assert loader.coerce_value("", "timestamp without time zone", required=True) == "1970-01-01T00:00:00"
    assert loader.coerce_value("", "date", required=True) == "1970-01-01"
    assert loader.coerce_value("", "character varying", required=True) == "0"
    assert loader.coerce_value("", "numeric", required=False) is None


def test_allowed_target_is_strictly_local_clone():
    loader = _import_loader()

    assert loader.is_allowed_local_target("127.0.0.1", "54321", "yfywk")
    assert not loader.is_allowed_local_target("localhost", "54321", "yfywk")
    assert not loader.is_allowed_local_target("127.0.0.1", "5432", "yfywk")
    assert not loader.is_allowed_local_target("127.0.0.1", "54321", "prod")
