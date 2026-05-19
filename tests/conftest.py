from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
MODEL_DIR = REPO_ROOT / "model"
MODEL_YOLO_FOUNDATION_DIR = MODEL_DIR / "yolo" / "foundation"
MODEL_YOLO_PRODUCTION_DIR = MODEL_DIR / "yolo" / "production"
MODEL_INSIGHTFACE_DIR = MODEL_DIR / "insightface"
MODEL_ASSETS_DIR = MODEL_DIR / "assets"
TEST_ROOT = Path(tempfile.mkdtemp(prefix="multi_rider_pytest_"))


def _write_placeholder(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(b"placeholder")


def _prepare_environment() -> None:
    for directory in (
        TEST_ROOT / "output",
        TEST_ROOT / "output" / "_results",
        TEST_ROOT / "datasets",
        TEST_ROOT / "train_runs",
        TEST_ROOT / "upload_tmp",
        TEST_ROOT / "face_data",
        TEST_ROOT / "face_data" / "photos",
        TEST_ROOT / "face_data" / "features",
        TEST_ROOT / "instantclient_11_2",
        MODEL_YOLO_FOUNDATION_DIR,
        MODEL_YOLO_PRODUCTION_DIR,
        MODEL_INSIGHTFACE_DIR,
        MODEL_ASSETS_DIR,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    for path in (
        MODEL_YOLO_PRODUCTION_DIR / "biaochezhajiev2.pt",
        MODEL_YOLO_PRODUCTION_DIR / "yolov8s-worldv2.pt",
        MODEL_YOLO_FOUNDATION_DIR / "yolo26n.pt",
        MODEL_YOLO_FOUNDATION_DIR / "yolo26s.pt",
        MODEL_ASSETS_DIR / "mobileclip_blt.ts",
        MODEL_ASSETS_DIR / "mobileclip2_b.ts",
        MODEL_ASSETS_DIR / "ViT-B-32.pt",
        MODEL_INSIGHTFACE_DIR / "det_10g.onnx",
        MODEL_INSIGHTFACE_DIR / "w600k_r50.onnx",
    ):
        _write_placeholder(path)

    face_sql_query_path = TEST_ROOT / "face_library.sql"
    _write_placeholder(face_sql_query_path)

    os.environ.update(
        {
            "FLASK_SECRET_KEY": "test-secret-key",
            "YOLO_TELEMETRY": "false",
            "DISPATCH_MOCK_MODE": "true",
            "FACE_SQL_ENABLED": "false",
            "FACE_SQL_HOST": "",
            "FACE_SQL_DB": "",
            "FACE_SQL_USER": "",
            "FACE_SQL_PASSWORD": "",
            "OUTPUT_DIR": str(TEST_ROOT / "output"),
            "RESULTS_DIR": str(TEST_ROOT / "output" / "_results"),
            "DATASETS_DIR": str(TEST_ROOT / "datasets"),
            "TRAIN_RUNS_DIR": str(TEST_ROOT / "train_runs"),
            "UPLOAD_TEMP_DIR": str(TEST_ROOT / "upload_tmp"),
            "FACE_DATA_DIR": str(TEST_ROOT / "face_data"),
            "SQLITE_DB_PATH": str(TEST_ROOT / "jobs.sqlite3"),
            "ORACLE_IC_DIR": str(TEST_ROOT / "instantclient_11_2"),
            "FACE_SQL_QUERY_PATH": str(face_sql_query_path),
            "MODEL_PATH": str(MODEL_YOLO_PRODUCTION_DIR / "biaochezhajiev2.pt"),
            "MODEL_PATH_GENERAL": str(MODEL_YOLO_PRODUCTION_DIR / "yolov8s-worldv2.pt"),
            "MOBILECLIP_TS_PATH": str(MODEL_ASSETS_DIR / "mobileclip_blt.ts"),
            "MOBILECLIP2_TS_PATH": str(MODEL_ASSETS_DIR / "mobileclip2_b.ts"),
            "CLIP_VIT_B32_PATH": str(MODEL_ASSETS_DIR / "ViT-B-32.pt"),
            "FACE_MODEL_DET": str(MODEL_INSIGHTFACE_DIR / "det_10g.onnx"),
            "FACE_MODEL_REC": str(MODEL_INSIGHTFACE_DIR / "w600k_r50.onnx"),
            "APP_HOST": "127.0.0.1",
            "APP_PORT": "5001",
            "WCNR_SCHEDULER_ENABLED": "0",
        }
    )


def pytest_configure(config):
    _prepare_environment()


def pytest_unconfigure(config):
    shutil.rmtree(TEST_ROOT, ignore_errors=True)


@pytest.fixture(scope="session")
def app_module():
    import app as app_module

    return app_module


@pytest.fixture()
def client(app_module):
    return app_module.app.test_client()
