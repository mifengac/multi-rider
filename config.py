import logging
import json
import os


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "model")
DEPLOYMENT_SLOTS_PATH = os.path.join(MODEL_DIR, "deployment_slots.json")
UPLOAD_MODEL_EXTS = {".pt"}
PROMPT_MODEL_DEFAULT_CLASSES = "person,motorcycle,bicycle,car,bus,truck"
PROMPT_MODEL_DEFAULT_CONF = 0.10


def _resolve_path(path_value: str) -> str:
    if os.path.isabs(path_value):
        return path_value
    return os.path.abspath(os.path.join(BASE_DIR, path_value))


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
SMS_ORACLE_HOST = os.getenv("SMS_ORACLE_HOST", ORACLE_HOST)
SMS_ORACLE_PORT = int(os.getenv("SMS_ORACLE_PORT", str(ORACLE_PORT)))
SMS_ORACLE_SERVICE = os.getenv("SMS_ORACLE_SERVICE", ORACLE_SERVICE)
SMS_ORACLE_USER = os.getenv("SMS_ORACLE_USER", ORACLE_USER)
SMS_ORACLE_PASSWORD = os.getenv("SMS_ORACLE_PASSWORD", ORACLE_PASSWORD)


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
    "general": _resolve_model_path_candidates(("yolov8s-worldv2.pt", "yolo26s.pt", "yolo26n.pt"), "MODEL_PATH_GENERAL"),
}
MOBILECLIP_TS_PATH = _resolve_model_path("mobileclip_blt.ts", "MOBILECLIP_TS_PATH")
MOBILECLIP2_TS_PATH = _resolve_model_path("mobileclip2_b.ts", "MOBILECLIP2_TS_PATH")
CLIP_VIT_B32_PATH = _resolve_model_path("ViT-B-32.pt", "CLIP_VIT_B32_PATH")
MODEL_ASSET_FILENAMES = {
    os.path.basename(CLIP_VIT_B32_PATH).lower(),
}

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
DATASETS_DIR = _resolve_path(os.getenv("DATASETS_DIR", os.path.join(BASE_DIR, "datasets")))
TRAIN_RUNS_DIR = _resolve_path(os.getenv("TRAIN_RUNS_DIR", os.path.join(BASE_DIR, "train_runs")))

UPLOAD_TEMP_DIR = _resolve_path(os.getenv("UPLOAD_TEMP_DIR", os.path.join(BASE_DIR, "upload_tmp")))
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(1024 * 1024 * 1024)))
VIDEO_FRAME_INTERVAL = int(os.getenv("VIDEO_FRAME_INTERVAL", "5"))

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

DISPATCH_AUTH_URL = os.getenv(
    "DISPATCH_AUTH_URL",
    "http://68.26.6.231:7204/rzzx_beta/oauth/token",
)
DISPATCH_TASK_URL = os.getenv(
    "DISPATCH_TASK_URL",
    "http://68.26.6.231:7204/xbrwzx_beta/api/WxtdjModule/receiveAndCreateRw",
)
DISPATCH_CLIENT_ID = os.getenv("DISPATCH_CLIENT_ID", "jcgkpt")
DISPATCH_CLIENT_SECRET = os.getenv("DISPATCH_CLIENT_SECRET", "123456")
DISPATCH_GRANT_TYPE = os.getenv("DISPATCH_GRANT_TYPE", "password")
DISPATCH_RWYID = os.getenv("DISPATCH_RWYID", "ecfffc32c9aa4aabb75541cb23a3270f")
DISPATCH_SJCSLY = os.getenv("DISPATCH_SJCSLY", "yfdjzldxwlxxwffzzx")
DISPATCH_QSSX = os.getenv("DISPATCH_QSSX", "06")
DISPATCH_FKSX = os.getenv("DISPATCH_FKSX", "08")
DISPATCH_GJDQ = os.getenv("DISPATCH_GJDQ", "CHN")
DISPATCH_ZJLX = os.getenv("DISPATCH_ZJLX", "111")
DISPATCH_XFDW = os.getenv("DISPATCH_XFDW", "")
DISPATCH_YWFZR = os.getenv("DISPATCH_YWFZR", "")
DISPATCH_YWFZRLXDH = os.getenv("DISPATCH_YWFZRLXDH", "")
DISPATCH_DEFAULT_TITLE = os.getenv("DISPATCH_DEFAULT_TITLE", "违法行为核查任务")
DISPATCH_DEFAULT_CONTENT = os.getenv(
    "DISPATCH_DEFAULT_CONTENT",
    "请核查该对象近期涉嫌违法行为并反馈处置情况。",
)
DISPATCH_DEFAULT_NOTE = os.getenv(
    "DISPATCH_DEFAULT_NOTE",
    "由 Multi-Rider 自动识别并流转生成，请结合实际情况核查。",
)
DISPATCH_MOCK_MODE = (os.getenv("DISPATCH_MOCK_MODE", "false") or "false").strip().lower() in {"1", "true", "yes", "on"}
DISPATCH_QUEUE_LIMIT = max(10, int(os.getenv("DISPATCH_QUEUE_LIMIT", "100")))
DISPATCH_SMS_DEFAULT_MOBILE = os.getenv("DISPATCH_SMS_DEFAULT_MOBILE", "")
DISPATCH_SMS_DEFAULT_TEMPLATE = os.getenv(
    "DISPATCH_SMS_DEFAULT_TEMPLATE",
    "【治安基础管控中心】{xm}，系统识别到您涉及“{illegal_type}”线索，请于{deadline}前主动配合核查。联系单位：{zbpcsmc}，联系电话：{ywfzrlxdh}。",
)
DISPATCH_SMS_USERID = os.getenv("DISPATCH_SMS_USERID", "admin")
DISPATCH_SMS_PASSWORD = os.getenv("DISPATCH_SMS_PASSWORD", "yfga8130018")
DISPATCH_SMS_USERPORT = os.getenv("DISPATCH_SMS_USERPORT", "0006")

FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "5001"))


def _is_prompt_model_name(model_name: str) -> bool:
    lower = os.path.basename(model_name).lower()
    return "yolo" in lower and "world" in lower


def _load_deployment_slots() -> dict:
    if not os.path.isfile(DEPLOYMENT_SLOTS_PATH):
        return {"slots": {}, "updated_ts": None}
    try:
        with open(DEPLOYMENT_SLOTS_PATH, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        if isinstance(payload, dict):
            slots = payload.get("slots")
            if not isinstance(slots, dict):
                payload["slots"] = {}
            payload.setdefault("updated_ts", None)
            return payload
    except Exception:
        pass
    return {"slots": {}, "updated_ts": None}


def get_deployment_slot_model_name(slot_key: str) -> str:
    payload = _load_deployment_slots()
    slot = (payload.get("slots") or {}).get(str(slot_key or "").strip(), {})
    if not isinstance(slot, dict):
        return ""
    model_name = os.path.basename(str(slot.get("model_name") or "").strip())
    if not model_name:
        return ""
    if os.path.splitext(model_name)[1].lower() not in UPLOAD_MODEL_EXTS:
        return ""
    candidate = os.path.join(MODEL_DIR, model_name)
    return model_name if os.path.isfile(candidate) else ""


def model_supports_text_prompt(model_key: str) -> bool:
    key = (model_key or "").strip()
    if key in MODEL_REGISTRY:
        return _is_prompt_model_name(os.path.basename(resolve_model_path(key)))
    return _is_prompt_model_name(key)


def list_upload_model_paths() -> dict[str, str]:
    registry: dict[str, str] = {}

    def _register(path: str | None) -> None:
        if not path or not os.path.isfile(path):
            return
        model_name = os.path.basename(path)
        if os.path.splitext(model_name)[1].lower() not in UPLOAD_MODEL_EXTS:
            return
        if model_name.lower() in MODEL_ASSET_FILENAMES:
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
        override_name = get_deployment_slot_model_name(key)
        if override_name:
            override_path = os.path.join(MODEL_DIR, override_name)
            if os.path.isfile(override_path):
                return os.path.abspath(override_path)
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

    override_name = get_deployment_slot_model_name("upload_default")
    if override_name and override_name in registry:
        return override_name

    preferred_names = [
        os.path.basename(MODEL_REGISTRY.get("general", "")),
        "yolov8s-worldv2.pt",
        "yolo26s.pt",
        "yolo26n.pt",
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
    meta = _friendly_model_meta(model_name)
    if meta and meta.get("description"):
        return str(meta["description"])
    lower = model_name.lower()
    if lower == "biaochezhajiev2.pt":
        return "Private wheelie detection model for closed-set filtering."
    if "yolo" in lower and "world" in lower:
        return "YOLO-World open-vocabulary model with English prompts."
    if lower == "yolo26n.pt":
        return "YOLO26n base model for low-compute training and deployment."
    if lower == "yolo26s.pt":
        return "YOLO26s base model for balanced accuracy and speed."
    return "Custom detection model."


def _friendly_model_meta(model_name: str) -> dict[str, str]:
    lower = (model_name or "").strip().lower()
    friendly_map: dict[str, dict[str, str]] = {
        "biaochezhajiev2.pt": {
            "label": "专项违法行为识别",
            "short_label": "专项违法行为识别",
            "description": "用于飙车炸街、翘头等专项违法行为快速筛查。",
        },
        "yolov8s-worldv2.pt": {
            "label": "通用人车要素识别",
            "short_label": "通用要素识别",
            "description": "适合按提示词检出人员、车辆、摩托车等通用目标。",
        },
        "yolo26n.pt": {
            "label": "快速版训练底模",
            "short_label": "快速版底模",
            "description": "适合低算力环境快速验证数据集和训练流程。",
        },
        "yolo26s.pt": {
            "label": "标准版训练底模",
            "short_label": "标准版底模",
            "description": "适合在速度和精度之间取得更均衡的训练效果。",
        },
    }
    if lower in friendly_map:
        return friendly_map[lower]
    return {
        "label": f"自定义识别模型（{model_name}）",
        "short_label": "自定义识别模型",
        "description": "本地自定义识别模型，可用于专项筛查或预标注。",
    }


def get_upload_model_options() -> list[dict[str, object]]:
    registry = list_upload_model_paths()
    if not registry:
        return []

    preferred_rank = {
        os.path.basename(MODEL_REGISTRY.get("general", "")).lower(): 0,
        "yolov8s-worldv2.pt": 1,
        "yolo26s.pt": 2,
        "yolo26n.pt": 3,
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
                "label": _friendly_model_meta(model_name)["label"],
                "short_label": _friendly_model_meta(model_name)["short_label"],
                "description": _upload_model_description(model_name),
                "ui_mode": "prompt" if is_prompt else "filter",
                "default_conf": PROMPT_MODEL_DEFAULT_CONF if is_prompt else CONF_THRESH,
                "default_classes": PROMPT_MODEL_DEFAULT_CLASSES if is_prompt else "",
            }
        )

    return options


def get_train_base_model_options() -> list[dict[str, str]]:
    registry = list_upload_model_paths()
    preferred = ["yolo26n.pt", "yolo26s.pt"]
    items: list[dict[str, str]] = []
    for model_name in preferred:
        model_path = registry.get(model_name)
        if not model_path:
            continue
        items.append(
            {
                "value": model_name,
                "label": _friendly_model_meta(model_name)["label"],
                "description": _upload_model_description(model_name),
            }
        )
    return items


os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(UPLOAD_TEMP_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(DATASETS_DIR, exist_ok=True)
os.makedirs(TRAIN_RUNS_DIR, exist_ok=True)

# Disable ultralytics telemetry and version checks for intranet hosts.
os.environ.setdefault("YOLO_TELEMETRY", "false")

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger("multi_rider")

if os.path.basename(MODEL_REGISTRY["general"]).lower() != "yolov8s-worldv2.pt":
    logger.warning(
        "Preferred general model yolov8s-worldv2.pt is not active; currently using %s",
        MODEL_REGISTRY["general"],
    )
