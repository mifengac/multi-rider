import logging
import os


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _resolve_path(path_value: str) -> str:
    return path_value if os.path.isabs(path_value) else os.path.abspath(os.path.join(BASE_DIR, path_value))


def _load_env_file(*paths: str) -> None:
    for path in paths:
        if not path or not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as fh:
                for raw_line in fh:
                    line = raw_line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip("'").strip('"')
                    if key:
                        os.environ[key] = value
        except Exception:
            continue


_load_env_file(
    os.path.join(BASE_DIR, "app.env"),
    os.path.join(BASE_DIR, "deploy", "app.env"),
)

ORACLE_HOST = os.getenv("ORACLE_HOST", "10.45.100.147")
ORACLE_PORT = int(os.getenv("ORACLE_PORT", "1521"))
ORACLE_SERVICE = os.getenv("ORACLE_SERVICE", "yfgxpt")
ORACLE_USER = os.getenv("ORACLE_USER", "yfzagk")
ORACLE_PASSWORD = os.getenv("ORACLE_PASSWORD", "yfzagk")

INSTANT_CLIENT_DIR = _resolve_path(os.getenv("ORACLE_IC_DIR", os.path.join(BASE_DIR, "instantclient_11_2")))


def _resolve_model_path(default_filename: str, *env_names: str) -> str:
    project_model_path = os.path.join(BASE_DIR, "model", default_filename)
    for env_name in env_names:
        env_value = (os.getenv(env_name, "") or "").strip()
        if not env_value:
            continue
        candidate = _resolve_path(env_value)
        if os.path.isfile(candidate):
            return os.path.abspath(candidate)

    return os.path.abspath(project_model_path)


MODEL_REGISTRY = {
    "bczj": _resolve_model_path("biaochezhajiev2.pt", "MODEL_PATH_BCZJ", "MODEL_PATH"),
    "general": _resolve_model_path("yoloe-26n-seg.pt", "MODEL_PATH_GENERAL"),
}
MOBILECLIP_TS_PATH = _resolve_model_path("mobileclip_blt.ts", "MOBILECLIP_TS_PATH")
MOBILECLIP2_TS_PATH = _resolve_model_path("mobileclip2_b.ts", "MOBILECLIP2_TS_PATH")

MODEL_DEFAULT = (os.getenv("MODEL_DEFAULT", "general") or "general").strip()
if MODEL_DEFAULT not in MODEL_REGISTRY:
    MODEL_DEFAULT = "general"

MAX_WORKERS = int(os.getenv("MAX_WORKERS", "8"))
CONF_THRESH = float(os.getenv("CONF_THRESH", "0.8"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "8"))
IMGSZ = int(os.getenv("IMGSZ", "640"))

OUTPUT_DIR = _resolve_path(os.getenv("OUTPUT_DIR", os.path.join(BASE_DIR, "output")))
SQLITE_DB_PATH = _resolve_path(os.getenv("SQLITE_DB_PATH", os.path.join(BASE_DIR, "jobs.sqlite3")))

UPLOAD_TEMP_DIR = _resolve_path(os.getenv("UPLOAD_TEMP_DIR", os.path.join(BASE_DIR, "upload_tmp")))
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(500 * 1024 * 1024)))  # 500 MB
VIDEO_FRAME_INTERVAL = int(os.getenv("VIDEO_FRAME_INTERVAL", "5"))  # extract 1 frame every N frames

FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "5001"))

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(UPLOAD_TEMP_DIR, exist_ok=True)

# Disable ultralytics telemetry and PyPI version-check network calls.
# Without this, YOLO() startup will attempt outbound HTTP to PyPI and
# analytics.ultralytics.com, causing timeout delays on an intranet host.
os.environ.setdefault("YOLO_TELEMETRY", "false")

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger("multi_rider")
