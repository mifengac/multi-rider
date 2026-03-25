import logging
import os


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "model")
UPLOAD_MODEL_EXTS = {".pt"}
PROMPT_MODEL_DEFAULT_CLASSES = "person,motorcycle,bicycle,car,bus,truck"
PROMPT_MODEL_DEFAULT_CONF = 0.10


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
    project_model_path = os.path.join(MODEL_DIR, default_filename)
    for env_name in env_names:
        env_value = (os.getenv(env_name, "") or "").strip()
        if not env_value:
            continue
        candidate = _resolve_path(env_value)
        if os.path.isfile(candidate):
            return os.path.abspath(candidate)

    return os.path.abspath(project_model_path)


def _resolve_model_path_candidates(default_filenames: tuple[str, ...], *env_names: str) -> str:
    for env_name in env_names:
        env_value = (os.getenv(env_name, "") or "").strip()
        if not env_value:
            continue
        candidate = _resolve_path(env_value)
        if os.path.isfile(candidate):
            return os.path.abspath(candidate)
        return os.path.abspath(candidate)

    for default_filename in default_filenames:
        candidate = os.path.join(MODEL_DIR, default_filename)
        if os.path.isfile(candidate):
            return os.path.abspath(candidate)

    return os.path.abspath(os.path.join(MODEL_DIR, default_filenames[0]))


MODEL_REGISTRY = {
    "bczj": _resolve_model_path("biaochezhajiev2.pt", "MODEL_PATH_BCZJ", "MODEL_PATH"),
    "general": _resolve_model_path_candidates(("yoloe-26s-seg.pt", "yoloe-26n-seg.pt"), "MODEL_PATH_GENERAL"),
}
MOBILECLIP_TS_PATH = _resolve_model_path("mobileclip_blt.ts", "MOBILECLIP_TS_PATH")
MOBILECLIP2_TS_PATH = _resolve_model_path("mobileclip2_b.ts", "MOBILECLIP2_TS_PATH")
CLIP_VIT_B32_PATH = _resolve_model_path("ViT-B-32.pt", "CLIP_VIT_B32_PATH")

MODEL_DEFAULT = (os.getenv("MODEL_DEFAULT", "general") or "general").strip()
if MODEL_DEFAULT not in MODEL_REGISTRY:
    MODEL_DEFAULT = "general"

MAX_WORKERS = int(os.getenv("MAX_WORKERS", "8"))
CONF_THRESH = float(os.getenv("CONF_THRESH", "0.8"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "8"))
IMGSZ = int(os.getenv("IMGSZ", "640"))

OUTPUT_DIR = _resolve_path(os.getenv("OUTPUT_DIR", os.path.join(BASE_DIR, "output")))
SQLITE_DB_PATH = _resolve_path(os.getenv("SQLITE_DB_PATH", os.path.join(BASE_DIR, "jobs.sqlite3")))
RESULTS_DIR = _resolve_path(os.getenv("RESULTS_DIR", os.path.join(OUTPUT_DIR, "_results")))

UPLOAD_TEMP_DIR = _resolve_path(os.getenv("UPLOAD_TEMP_DIR", os.path.join(BASE_DIR, "upload_tmp")))
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(1024 * 1024 * 1024)))  # 1 GB
VIDEO_FRAME_INTERVAL = int(os.getenv("VIDEO_FRAME_INTERVAL", "5"))  # extract 1 frame every N frames

FACE_MODEL_DET = _resolve_path(os.getenv("FACE_MODEL_DET", os.path.join(MODEL_DIR, "det_10g.onnx")))
FACE_MODEL_REC = _resolve_path(os.getenv("FACE_MODEL_REC", os.path.join(MODEL_DIR, "w600k_r50.onnx")))
FACE_DATA_DIR = _resolve_path(os.getenv("FACE_DATA_DIR", os.path.join(BASE_DIR, "face_data")))
FACE_SIMILARITY_THR = float(os.getenv("FACE_SIMILARITY_THR", "0.35"))
FACE_MATCH_TOP_K = max(1, int(os.getenv("FACE_MATCH_TOP_K", "5")))
FACE_BLUR_THRESH = float(os.getenv("FACE_BLUR_THRESH", "60.0"))
FACE_SQL_ENABLED = (os.getenv("FACE_SQL_ENABLED", "true") or "true").strip().lower() not in {"0", "false", "no"}
FACE_SQL_HOST = os.getenv("FACE_SQL_HOST", "")
FACE_SQL_PORT = int(os.getenv("FACE_SQL_PORT", "5432"))
FACE_SQL_DB = os.getenv("FACE_SQL_DB", "")
FACE_SQL_USER = os.getenv("FACE_SQL_USER", "")
FACE_SQL_PASSWORD = os.getenv("FACE_SQL_PASSWORD", "")
FACE_SQL_QUERY_PATH = _resolve_path(os.getenv("FACE_SQL_QUERY_PATH", os.path.join(BASE_DIR, "face_library.sql")))

FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "5001"))


def _is_prompt_model_name(model_name: str) -> bool:
    lower = os.path.basename(model_name).lower()
    return "yoloe" in lower or ("yolo" in lower and "world" in lower)


def model_supports_text_prompt(model_key: str) -> bool:
    key = (model_key or "").strip()
    if key == "general":
        return True
    if key == "bczj":
        return False
    return _is_prompt_model_name(key)


def list_upload_model_paths() -> dict[str, str]:
    registry: dict[str, str] = {}

    def _register(path: str | None) -> None:
        if not path or not os.path.isfile(path):
            return
        model_name = os.path.basename(path)
        if os.path.splitext(model_name)[1].lower() not in UPLOAD_MODEL_EXTS:
            return
        registry.setdefault(model_name, os.path.abspath(path))

    _register(MODEL_REGISTRY.get("general"))
    _register(MODEL_REGISTRY.get("bczj"))

    if os.path.isdir(MODEL_DIR):
        for entry in sorted(os.listdir(MODEL_DIR), key=str.lower):
            _register(os.path.join(MODEL_DIR, entry))

    return registry


def resolve_model_path(model_key: str) -> str:
    key = (model_key or "").strip()
    if key in MODEL_REGISTRY:
        return MODEL_REGISTRY[key]

    registry = list_upload_model_paths()
    if key in registry:
        return registry[key]

    normalized_key = os.path.basename(key).lower()
    for model_name, model_path in registry.items():
        if model_name.lower() == normalized_key:
            return model_path

    raise ValueError(f"unsupported model key: {model_key}")


def get_upload_model_default() -> str:
    registry = list_upload_model_paths()
    if not registry:
        return ""

    preferred_names = [
        os.path.basename(MODEL_REGISTRY.get("general", "")),
        "yoloe-26s-seg.pt",
        "yoloe-26n-seg.pt",
        "yolov8s-worldv2.pt",
        os.path.basename(MODEL_REGISTRY.get("bczj", "")),
    ]
    name_lookup = {name.lower(): name for name in registry}
    for preferred in preferred_names:
        if preferred and preferred.lower() in name_lookup:
            return name_lookup[preferred.lower()]

    prompt_models = [name for name in registry if model_supports_text_prompt(name)]
    if prompt_models:
        return sorted(prompt_models, key=str.lower)[0]
    return sorted(registry, key=str.lower)[0]


def _upload_model_description(model_name: str) -> str:
    lower = model_name.lower()
    if lower == "biaochezhajiev2.pt":
        return "飙车炸街专用模型，适合类别过滤。"
    if "yoloe" in lower:
        return "YOLOE 开放词表模型，支持英文提示词。"
    if "yolo" in lower and "world" in lower:
        return "YOLO-World 开放词表模型，支持英文提示词。"
    return "自定义检测模型。"


def get_upload_model_options() -> list[dict[str, object]]:
    registry = list_upload_model_paths()
    if not registry:
        return []

    preferred_rank = {
        os.path.basename(MODEL_REGISTRY.get("general", "")).lower(): 0,
        "yoloe-26s-seg.pt": 1,
        "yoloe-26n-seg.pt": 2,
        "yolov8s-worldv2.pt": 3,
        os.path.basename(MODEL_REGISTRY.get("bczj", "")).lower(): 10,
    }

    def _sort_key(model_name: str) -> tuple[int, str]:
        return preferred_rank.get(model_name.lower(), 50), model_name.lower()

    options: list[dict[str, object]] = []
    for model_name in sorted(registry, key=_sort_key):
        is_prompt = model_supports_text_prompt(model_name)
        options.append(
            {
                "value": model_name,
                "label": model_name,
                "short_label": model_name,
                "description": _upload_model_description(model_name),
                "ui_mode": "prompt" if is_prompt else "filter",
                "default_conf": PROMPT_MODEL_DEFAULT_CONF if is_prompt else CONF_THRESH,
                "default_classes": PROMPT_MODEL_DEFAULT_CLASSES if is_prompt else "",
            }
        )

    return options

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(UPLOAD_TEMP_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

# Disable ultralytics telemetry and PyPI version-check network calls.
# Without this, YOLO() startup will attempt outbound HTTP to PyPI and
# analytics.ultralytics.com, causing timeout delays on an intranet host.
os.environ.setdefault("YOLO_TELEMETRY", "false")

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger("multi_rider")

if os.path.basename(MODEL_REGISTRY["general"]).lower() != "yoloe-26s-seg.pt":
    logger.warning(
        "Preferred general model yoloe-26s-seg.pt is not active; currently using %s",
        MODEL_REGISTRY["general"],
    )
