"""
Face Recognition Pipeline - Kingbase DB + ONNX (No insightface required)
=========================================================================
This version replaces insightface with direct ONNX model inference,
completely avoiding the C++ / Cython build requirement.

Dependencies (all pure Python or pre-built wheels, no compiler needed):
  pip install psycopg2-binary onnxruntime opencv-python numpy tqdm --no-index --find-links=<your_pkg_dir>

Required ONNX model files (download once on an internet-connected machine):
  - Face detection:    scrfd_10g_bnkps.onnx
    https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip
    (extract buffalo_l/det_10g.onnx)
  - Face recognition:  w600k_r50.onnx
    https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip
    (extract buffalo_l/w600k_r50.onnx)

  Place both .onnx files in the same folder as this script, or update MODEL_DET / MODEL_REC below.
"""

import base64
import pickle
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
import psycopg2
import psycopg2.extras
import onnxruntime as ort
from tqdm import tqdm

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────
DB_CONFIG = {
    "host":     "68.252.130.51",
    "port":     54321,
    "dbname":   "yfywk",
    "user":     "ywkuser",
    "password": "YOUR_PASSWORD",       # <- change this
}

# Paths to ONNX model files (place them next to this script, or use absolute paths)
MODEL_DET = Path("./models/det_10g.onnx")       # face detection model
MODEL_REC = Path("./models/w600k_r50.onnx")     # face recognition/embedding model

# Local storage directories
BASE_DIR      = Path("./face_data")
PHOTO_DIR     = BASE_DIR / "photos"              # decoded photo JPEG files
FEATURE_DIR   = BASE_DIR / "features"            # face embedding vectors (.npy)
DB_CACHE_FILE = BASE_DIR / "person_db.pkl"       # serialized personnel records

# Face detection settings
DET_GALLERY_SIZE= 640           # max resolution for ID photos (gallery)
DET_PROBE_SIZE  = 1920          # max resolution for normal probe images
DET_PROBE_SIZE_HQ = 3840        # max resolution for high-res (>2000px) probe images
                                 # 4K images shrunk to 1920 lose fine detail on small faces;
                                 # using full-res costs more RAM/time but catches far-away faces.
DET_CONF_THRESH = 0.5           # minimum detection confidence for gallery (ID photos are clean/frontal)
DET_PROBE_CONF  = 0.4           # minimum detection confidence for probe images
                                 # Keep at 0.4: in-the-wild photos naturally score lower than
                                 # clean ID shots. Size filter (DET_MIN_FACE_PX) handles noise,
                                 # so we don't need to raise this threshold aggressively.
DET_NMS_THRESH  = 0.4           # NMS IoU threshold for removing duplicate boxes
DET_MIN_FACE_PX = 40            # minimum face bbox short-side (px, in original image coords)
                                 # Faces smaller than this are noise/false-positives —
                                 # ArcFace crops at 112×112 from a ≥40px face is already stretched;
                                 # anything smaller produces garbage embeddings.

# Face recognition settings
REC_INPUT_SIZE  = (112, 112)    # ArcFace standard crop size
SIMILARITY_THR  = 0.35          # cosine similarity threshold — w600k_r50 real-world sweet spot
                                 # Gallery: ID/证件照 vs Probe: 监控/现场照，阈值不宜超过 0.40

# Image quality settings
BLUR_THRESH     = 60.0          # Laplacian variance below this → face is blurry, skip
BBOX_PAD_RATIO  = 0.20          # bbox fallback padding ratio (avoids tight crop)

# SQL query
QUERY_SQL = """
SELECT
    bzr."zjlx",
    bzr."zjhm",
    bzr."xm",
    tdrz."xp"
FROM "stdata"."bzdry_ryxx" bzr
LEFT JOIN "tdsfbrk_zpxx" tdrz
    ON bzr."zjhm" = tdrz."gmsfhm"
WHERE bzr."sflg"  = 1
  AND bzr."deleteflag" = 0
"""

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ══════════════════════════════════════════════
# Data Structure
# ══════════════════════════════════════════════
@dataclass
class PersonRecord:
    zjlx:       str                              # ID type (resident ID, passport, etc.)
    zjhm:       str                              # ID number -- used as unique key
    xm:         str                              # full name
    photo_path: Optional[str]        = None      # local path to saved JPEG photo
    embedding:  Optional[np.ndarray] = None      # 512-dim face feature vector


# ══════════════════════════════════════════════
# ONNX Model Wrappers
# ══════════════════════════════════════════════
def _patch_onnx_dynamic_outputs(model_path: Path) -> str:
    """
    ONNX Runtime >= 1.16 strictly validates that each output tensor's shape matches
    what is declared in the model's type-info metadata.  The SCRFD detection model
    (det_10g.onnx) hard-codes static output shapes derived from a 640×640 input;
    any other padded resolution causes a shape-mismatch error at inference time.

    This function rewrites all output shape dimensions to symbolic ('dyn') so ORT
    skips the validation, then saves the patched model as  <stem>_dyn.onnx  next to
    the original.  Subsequent calls return the cached patched path immediately.
    The fix is one-time and does NOT affect inference speed or accuracy.
    """
    patched_path = model_path.with_name(model_path.stem + "_dyn.onnx")
    if patched_path.exists():
        return str(patched_path)

    try:
        import onnx  # available: onnx-1.20.1 is in pkgs/
    except ImportError:
        log.warning(
            "'onnx' package not found — cannot patch model output shapes. "
            "You may encounter 'Expected shape … does not match actual shape' errors. "
            "Install onnx to fix this automatically."
        )
        return str(model_path)

    model = onnx.load(str(model_path))
    patched = 0
    for output in model.graph.output:
        tensor_type = output.type.tensor_type
        if tensor_type.HasField("shape"):
            for dim in tensor_type.shape.dim:
                # Only override statically-fixed dimensions (dim_value > 0)
                # Leave existing symbolic params (dim_param) untouched
                if dim.dim_value > 0:
                    dim.ClearField("dim_value")
                    dim.dim_param = "dyn"
                    patched += 1

    onnx.save(model, str(patched_path))
    log.info(
        "Patched %d static output dims → dynamic; saved to %s",
        patched, patched_path,
    )
    return str(patched_path)


class FaceDetector:
    """
    SCRFD face detector via ONNX.
    Returns a list of face bounding boxes and keypoints detected in an image.
    """

    def __init__(self, model_path: str | Path):
        model_path = Path(model_path)
        if not model_path.exists():
            raise FileNotFoundError(
                f"Detection model not found: {model_path}\n"
                "Download buffalo_l.zip from InsightFace releases and extract det_10g.onnx"
            )
        # Patch static output shapes → dynamic to avoid ORT >= 1.16 shape-mismatch errors
        load_path = _patch_onnx_dynamic_outputs(model_path)
        self.session = ort.InferenceSession(
            load_path,
            providers=["CUDAExecutionProvider", "CPUExecutionProvider"]
        )
        self.input_name = self.session.get_inputs()[0].name
        log.info("Face detector loaded: %s", load_path)

    def preprocess(self, img: np.ndarray, max_size: int = 640) -> tuple[np.ndarray, float, tuple]:
        """Resize image preserving aspect ratio mapped to max_size, and pad to multiple of 32."""
        h, w = img.shape[:2]
        scale = max_size / max(h, w)
        new_h, new_w = int(h * scale), int(w * scale)
        resized = cv2.resize(img, (new_w, new_h))

        # Pad to exactly nearest multiple of 32 for dynamic convolution
        pad_h = ((new_h + 31) // 32) * 32
        pad_w = ((new_w + 31) // 32) * 32
        canvas = np.zeros((pad_h, pad_w, 3), dtype=np.float32)
        canvas[:new_h, :new_w] = resized
        pad = (new_h, new_w)

        # Normalize: mean=[127.5, 127.5, 127.5], std=128.0
        canvas = (canvas - 127.5) / 128.0
        # Convert HWC -> CHW -> NCHW
        tensor = canvas.transpose(2, 0, 1)[np.newaxis].astype(np.float32)
        return tensor, scale, pad

    def detect(self, img: np.ndarray, max_size: int = 640) -> list[dict]:
        """
        Run detection on an image.
        Returns a list of detections: [{"bbox": [x1,y1,x2,y2], "score": float, "kps": array}]
        """
        tensor, scale, (new_h, new_w) = self.preprocess(img, max_size)
        outputs = self.session.run(None, {self.input_name: tensor})

        # SCRFD outputs vary by model; collect all score/bbox/kps output triplets
        results = []
        num_outputs = len(outputs)
        
        # Determine padded grid size for anchor generation
        tensor_h, tensor_w = tensor.shape[2], tensor.shape[3]

        # Typical SCRFD output order: scores_8, scores_16, scores_32,
        #                             bboxes_8, bboxes_16, bboxes_32,
        #                             kps_8, kps_16, kps_32
        strides = [8, 16, 32]
        num_levels = len(strides)
        has_kps = num_outputs == num_levels * 3

        for i, stride in enumerate(strides):
            scores = outputs[i].flatten()                  # (N,)
            bboxes = outputs[i + num_levels]               # (N, 4) — relative to input grid
            kps    = outputs[i + num_levels * 2] if has_kps else None

            # Build anchor grid dynamically for this stride
            fh = tensor_h // stride
            fw = tensor_w // stride
            anchor_centers = np.stack(
                np.mgrid[:fh, :fw][::-1], axis=-1
            ).reshape(-1, 2).astype(np.float32)
            anchor_centers = (anchor_centers * stride)
            # Each anchor center is repeated twice (2 anchors per cell in SCRFD)
            anchor_centers = np.repeat(anchor_centers, 2, axis=0)

            # Filter by confidence threshold
            mask = scores >= DET_CONF_THRESH
            if not mask.any():
                continue

            filtered_scores   = scores[mask]
            filtered_anchors  = anchor_centers[mask]
            filtered_bboxes   = bboxes[mask]

            # Decode bboxes: (cx - dx*stride, cy - dy*stride, cx + dw*stride, cy + dh*stride)
            x1 = (filtered_anchors[:, 0] - filtered_bboxes[:, 0] * stride) / scale
            y1 = (filtered_anchors[:, 1] - filtered_bboxes[:, 1] * stride) / scale
            x2 = (filtered_anchors[:, 0] + filtered_bboxes[:, 2] * stride) / scale
            y2 = (filtered_anchors[:, 1] + filtered_bboxes[:, 3] * stride) / scale

            for j in range(len(filtered_scores)):
                det = {
                    "bbox":  [float(x1[j]), float(y1[j]), float(x2[j]), float(y2[j])],
                    "score": float(filtered_scores[j]),
                    "kps":   None,
                }
                if kps is not None:
                    pts = kps[mask][j].reshape(5, 2)
                    anchor = filtered_anchors[j]
                    det["kps"] = (anchor + pts * stride) / scale
                results.append(det)

        if not results:
            return []

        # Apply Non-Maximum Suppression (NMS) to remove overlapping boxes
        boxes  = np.array([r["bbox"]  for r in results], dtype=np.float32)
        scores = np.array([r["score"] for r in results], dtype=np.float32)
        keep   = self._nms(boxes, scores, DET_NMS_THRESH)
        return [results[k] for k in keep]

    @staticmethod
    def _nms(boxes: np.ndarray, scores: np.ndarray, iou_thresh: float) -> list[int]:
        """Standard NMS: suppress lower-scoring boxes that heavily overlap a higher-scoring one."""
        x1, y1, x2, y2 = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
        areas  = (x2 - x1) * (y2 - y1)
        order  = scores.argsort()[::-1]
        keep   = []
        while order.size > 0:
            i = order[0]
            keep.append(i)
            # Compute IoU of the top box against all remaining boxes
            inter_x1 = np.maximum(x1[i], x1[order[1:]])
            inter_y1 = np.maximum(y1[i], y1[order[1:]])
            inter_x2 = np.minimum(x2[i], x2[order[1:]])
            inter_y2 = np.minimum(y2[i], y2[order[1:]])
            inter    = np.maximum(0, inter_x2 - inter_x1) * np.maximum(0, inter_y2 - inter_y1)
            iou      = inter / (areas[i] + areas[order[1:]] - inter)
            order    = order[1:][iou <= iou_thresh]
        return keep


class FaceRecognizer:
    """
    ArcFace face recognizer via ONNX.
    Extracts a normalized 512-dim embedding from a cropped face image.
    """

    # Standard 5-point landmark reference for ArcFace alignment
    ARCFACE_REF = np.array([
        [38.2946, 51.6963],
        [73.5318, 51.5014],
        [56.0252, 71.7366],
        [41.5493, 92.3655],
        [70.7299, 92.2041],
    ], dtype=np.float32)

    def __init__(self, model_path: str | Path):
        model_path = Path(model_path)
        if not model_path.exists():
            raise FileNotFoundError(
                f"Recognition model not found: {model_path}\n"
                "Download buffalo_l.zip from InsightFace releases and extract w600k_r50.onnx"
            )
        load_path = _patch_onnx_dynamic_outputs(model_path)
        self.session = ort.InferenceSession(
            load_path,
            providers=["CUDAExecutionProvider", "CPUExecutionProvider"]
        )
        self.input_name = self.session.get_inputs()[0].name
        log.info("Face recognizer loaded: %s", load_path)

    def align_and_crop(self, img: np.ndarray, kps: np.ndarray) -> np.ndarray:
        """
        Align the face using 5 facial keypoints (similarity transform)
        and crop to 112x112 as required by ArcFace.
        """
        M, _ = cv2.estimateAffinePartial2D(kps, self.ARCFACE_REF, method=cv2.LMEDS)
        aligned = cv2.warpAffine(img, M, REC_INPUT_SIZE, borderValue=0)
        return aligned

    def get_embedding(self, face_img: np.ndarray) -> np.ndarray:
        """
        Compute a normalized 512-dim face embedding from a 112x112 aligned face crop.
        """
        # Normalize pixel values from [0, 255] to [-1, 1]
        blob = (face_img.astype(np.float32) - 127.5) / 128.0
        # HWC -> CHW -> NCHW
        blob = blob.transpose(2, 0, 1)[np.newaxis]
        output = self.session.run(None, {self.input_name: blob})[0][0]
        # L2-normalize so cosine similarity = dot product
        norm   = np.linalg.norm(output)
        return output / norm if norm > 0 else output


# ══════════════════════════════════════════════
# Probe image preprocessing utilities
# ══════════════════════════════════════════════
def load_image(path: str) -> Optional[np.ndarray]:
    """Robustly load an image, supporting TIFF and JFIF formats correctly."""
    import os
    if not os.path.exists(path):
        return None

    # IMREAD_UNCHANGED helps to load 16-bit or unusual TIFFs properly via OpenCV
    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)

    # Fallback for formats whose extension is not recognized by OpenCV on Windows
    # (e.g. .jfif — a JPEG variant — is not in OpenCV's extension map).
    # imdecode inspects the actual file magic bytes and is extension-agnostic.
    if img is None:
        try:
            raw = Path(path).read_bytes()
            arr = np.frombuffer(raw, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_UNCHANGED)
        except Exception:
            return None

    if img is None:
        return None

    # Handle transparent/gray images gracefully
    if len(img.shape) == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    elif len(img.shape) == 3 and img.shape[2] == 4:
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    # Handle high bit depths (e.g. 16-bit TIFFs standard in some surveillance exports)
    if img.dtype == np.uint16:
        img = (img / 256).astype(np.uint8)

    return img


def enhance_image(img: np.ndarray) -> np.ndarray:
    """
    Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) per channel.
    Normalizes lighting differences between gallery (ID photos) and probe (field/surveillance) images.
    """
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    lab   = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def blur_score(face_img: np.ndarray) -> float:
    """Return Laplacian variance as sharpness score. Lower = blurrier."""
    gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def crop_face_bbox(img: np.ndarray, bbox: list, pad_ratio: float = BBOX_PAD_RATIO) -> np.ndarray:
    """
    Crop face from bounding box with proportional padding.
    Padding prevents tight crops that lose chin/forehead context.
    """
    h, w = img.shape[:2]
    x1, y1, x2, y2 = [float(v) for v in bbox]
    bw, bh   = x2 - x1, y2 - y1
    x1 = max(0, int(x1 - bw * pad_ratio))
    y1 = max(0, int(y1 - bh * pad_ratio))
    x2 = min(w, int(x2 + bw * pad_ratio))
    y2 = min(h, int(y2 + bh * pad_ratio))
    return cv2.resize(img[y1:y2, x1:x2], REC_INPUT_SIZE)


def extract_probe_embeddings(
    img: np.ndarray,
    detector: "FaceDetector",
    recognizer: "FaceRecognizer",
    use_enhance: bool = True,
    max_size: int = DET_PROBE_SIZE,
    conf_thresh: float = DET_PROBE_CONF,
    min_face_px: int = DET_MIN_FACE_PX,
) -> list[tuple[np.ndarray, dict]]:
    """
    Extract embeddings for ALL faces detected in the image.
    Returns a list of (embedding, info_dict) tuples.

    For high-resolution images (any dimension > 2000px), detection automatically
    runs at a higher resolution (DET_PROBE_SIZE_HQ) to avoid missing small faces
    that are lost when a 4K image is aggressively downscaled to 1920px.

    Filters applied (in order, before embedding extraction):
      1. conf_thresh  — drop low-confidence detections
      2. min_face_px  — drop faces whose shorter bbox side < min_face_px pixels
                        (tiny faces = noise / too far away to be useful)
    """
    if use_enhance:
        img = enhance_image(img)

    # Adaptive probe resolution: use high-res detection for 4K / large images
    h, w = img.shape[:2]
    if max_size == DET_PROBE_SIZE and max(h, w) > 2000:
        effective_max = DET_PROBE_SIZE_HQ
        log.info(
            "High-res image (%dx%d) detected — using DET_PROBE_SIZE_HQ=%d for detection",
            w, h, effective_max,
        )
    else:
        effective_max = max_size

    detections = detector.detect(img, effective_max)
    if not detections:
        return []

    # ── Size & confidence pre-filter ─────────────────────────────────────────
    valid_dets = []
    for det in detections:
        x1, y1, x2, y2 = det["bbox"]
        face_w = x2 - x1
        face_h = y2 - y1
        if det["score"] < conf_thresh:
            log.debug(
                "Skipped tiny/weak face — score=%.3f < %.2f  bbox=[%d,%d,%d,%d]",
                det["score"], conf_thresh, int(x1), int(y1), int(x2), int(y2),
            )
            continue
        if face_w < min_face_px or face_h < min_face_px:
            log.warning(
                "Skipped too-small face — %dx%dpx < %dpx min  "
                "(det_score=%.3f  bbox=[%d,%d,%d,%d])",
                int(face_w), int(face_h), min_face_px,
                det["score"], int(x1), int(y1), int(x2), int(y2),
            )
            continue
        valid_dets.append(det)

    if not valid_dets:
        skipped = len(detections)
        log.warning(
            "All %d raw detection(s) rejected by size/confidence filters "
            "(min_face_px=%d, conf_thresh=%.2f). "
            "Try a closer photo or lower DET_MIN_FACE_PX.",
            skipped, min_face_px, conf_thresh,
        )
        return []

    results = []
    total_faces = len(valid_dets)

    for idx, det in enumerate(valid_dets):
        x1, y1, x2, y2 = det["bbox"]
        info = {
            "face_idx": idx,
            "face_count": total_faces,
            "bbox": det["bbox"],
            "face_size": (round(x2 - x1), round(y2 - y1)),
            "det_score": round(det["score"], 4),
            "used_align": det["kps"] is not None,
            "error": None,
        }

        if det["kps"] is not None:
            face_crop = recognizer.align_and_crop(img, det["kps"])
        else:
            face_crop = crop_face_bbox(img, det["bbox"])

        bscore = blur_score(face_crop)
        info["blur_score"] = round(bscore, 2)
        if bscore < BLUR_THRESH:
            log.debug("Face %d is blurry (score=%.1f < %.1f), embedding may be unreliable",
                      idx, bscore, BLUR_THRESH)

        emb = recognizer.get_embedding(face_crop)
        results.append((emb, info))

    return results

def extract_probe_embedding(
    img: np.ndarray,
    detector: "FaceDetector",
    recognizer: "FaceRecognizer",
    use_enhance: bool = True,
    max_size: int = DET_GALLERY_SIZE,
) -> tuple[Optional[np.ndarray], dict]:
    """
    Legacy wrapper: extracts the LARGEST face's embedding for gallery building.
    """
    faces = extract_probe_embeddings(img, detector, recognizer, use_enhance, max_size)
    if not faces:
        return None, {"error": "no face detected", "face_count": 0}
        
    # Prefer the largest face by bounding box area
    def get_area(face_tuple):
        bbox = face_tuple[1]["bbox"]
        return (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
        
    best_face = max(faces, key=get_area)
    return best_face[0], best_face[1]


# ══════════════════════════════════════════════
# Step 1: Fetch data from database
# ══════════════════════════════════════════════
def fetch_persons_from_db() -> list[PersonRecord]:
    """Connect to Kingbase and query personnel records with photos."""
    log.info("Connecting to database %s:%s ...", DB_CONFIG["host"], DB_CONFIG["port"])
    conn = psycopg2.connect(**DB_CONFIG)
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    log.info("Executing query ...")
    cur.execute(QUERY_SQL)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    log.info("Fetched %d records from database", len(rows))

    log.info("Raw rows from DB (before dedup): %d", len(rows))

    # ── Deduplicate by zjhm ────────────────────────────────────────────────────
    # One person may have multiple rows (multiple photos in tdsfbrk_zpxx).
    # Keep exactly ONE record per zjhm, preferring the row that has a non-null photo.
    seen: dict[str, dict] = {}
    for row in rows:
        zjhm = row["zjhm"] or ""
        if not zjhm:
            continue
        if zjhm not in seen:
            seen[zjhm] = dict(row)
        elif seen[zjhm]["xp"] is None and row["xp"] is not None:
            # Upgrade to the row that actually has a photo
            seen[zjhm] = dict(row)

    log.info("Unique persons (by zjhm) after dedup: %d", len(seen))

    persons = []
    for row in seen.values():
        p = PersonRecord(
            zjlx = row["zjlx"] or "",
            zjhm = row["zjhm"] or "",
            xm   = row["xm"]   or "",
        )
        p._raw_photo = row["xp"]  # temporarily attached for save_photos()
        persons.append(p)
    return persons


# ══════════════════════════════════════════════
# Step 2: Decode and save photos
# ══════════════════════════════════════════════
def decode_photo(raw) -> Optional[np.ndarray]:
    """
    Decode a raw DB photo field (bytea or base64 string) into an OpenCV BGR image.
    Returns None if the field is empty or decoding fails.
    """
    if raw is None:
        return None
    if isinstance(raw, memoryview):
        raw = bytes(raw)
    if isinstance(raw, str):
        try:
            raw = base64.b64decode(raw)
        except Exception:
            return None
    arr = np.frombuffer(raw, dtype=np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def save_photos(persons: list[PersonRecord]) -> None:
    """Save decoded photos as JPEG files named by ID number."""
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    saved = 0
    for p in tqdm(persons, desc="Saving photos"):
        raw = getattr(p, "_raw_photo", None)
        if raw is None:
            continue
        img = decode_photo(raw)
        if img is None:
            log.warning("[%s] %s -- photo decode failed, skipping", p.zjhm, p.xm)
            continue
        path = PHOTO_DIR / f"{p.zjhm}.jpg"
        cv2.imwrite(str(path), img)
        p.photo_path = str(path)
        saved += 1
    log.info("Photos saved: %d / %d", saved, len(persons))


# ══════════════════════════════════════════════
# Step 3: Extract face embeddings
# ══════════════════════════════════════════════
def extract_embeddings(
    persons: list[PersonRecord],
    detector: FaceDetector,
    recognizer: FaceRecognizer,
    force: bool = False,
) -> None:
    """
    Detect face in each gallery photo and extract a 512-dim embedding.

    Gallery images are 证件照 (ID headshots):
      - Face occupies most of the image, already frontal and well-lit
      - BUT probe images (real-world) have varying lighting → CLAHE bridging is needed
      - We apply the SAME enhance_image + extract_probe_embedding pipeline used on probes
        to ensure gallery and probe embeddings are in the same feature space

    Args:
        force: if True, delete existing .npy files and re-extract (needed after
               preprocessing changes — e.g., adding CLAHE to an existing gallery)

    Resume support: existing .npy files are loaded and skipped UNLESS force=True.
    """
    FEATURE_DIR.mkdir(parents=True, exist_ok=True)
    success, skipped, failed = 0, 0, 0

    for p in tqdm(persons, desc="Extracting embeddings"):
        if p.photo_path is None:
            failed += 1
            continue

        feat_path = FEATURE_DIR / f"{p.zjhm}.npy"

        if feat_path.exists() and not force:
            # Resume: load existing embedding without reprocessing
            p.embedding = np.load(str(feat_path))
            success += 1
            skipped += 1
            continue

        img = load_image(p.photo_path)
        if img is None:
            log.warning("[%s] %s -- failed to read photo", p.zjhm, p.xm)
            failed += 1
            continue

        # Use the SAME pipeline as probe images for feature-space consistency:
        #   enhance_image (CLAHE) → detect → align/crop → get_embedding
        # For tight 证件照, CLAHE is nearly a no-op on the well-exposed face,
        # but applying it ensures gallery/probe embeddings are computed identically.
        emb, info = extract_probe_embedding(img, detector, recognizer, use_enhance=True)

        if emb is None:
            log.warning("[%s] %s -- %s", p.zjhm, p.xm, info.get("error", "extraction failed"))
            failed += 1
            continue

        if not info.get("used_align"):
            log.debug("[%s] %s -- keypoints missing, used bbox fallback", p.zjhm, p.xm)

        np.save(str(feat_path), emb)
        p.embedding = emb
        success += 1

    log.info(
        "Embedding extraction complete — success: %d (skipped existing: %d)  failed: %d",
        success, skipped, failed,
    )


# ══════════════════════════════════════════════
# Step 4: Persist / load the personnel database
# ══════════════════════════════════════════════
def save_person_db(persons: list[PersonRecord]) -> None:
    """Serialize PersonRecord list (without raw photo blobs) to disk."""
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    for p in persons:
        if hasattr(p, "_raw_photo"):
            del p._raw_photo
    with open(DB_CACHE_FILE, "wb") as f:
        pickle.dump(persons, f)
    log.info("Personnel database saved to %s", DB_CACHE_FILE)


def load_person_db() -> list[PersonRecord]:
    """Load the serialized personnel database from disk."""
    with open(DB_CACHE_FILE, "rb") as f:
        persons = pickle.load(f)
    log.info("Loaded %d personnel records", len(persons))
    return persons


# ══════════════════════════════════════════════
# Step 5: Face comparison interface
# ══════════════════════════════════════════════
def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Cosine similarity between two L2-normalized embedding vectors.
    Equivalent to dot product when vectors are already normalized.
    Range: [-1, 1] -- higher = more similar.
    """
    return float(np.dot(a, b))


def verify_face(
    probe_img_path: str,
    target_zjhm: str,
    persons: list[PersonRecord],
    detector: FaceDetector,
    recognizer: FaceRecognizer,
) -> dict:
    """
    1:1 Verification -- check if the person in a probe image matches
    the enrolled person with the given ID number.
    Checks ALL faces found in the probe image.

    Returns:
        {"match": bool, "score": float, "person": PersonRecord, "error": str (if any)}
    """
    target = next((p for p in persons if p.zjhm == target_zjhm), None)
    if target is None or target.embedding is None:
        return {"match": False, "score": 0.0, "person": None,
                "error": "Target person not found or has no embedding"}

    img = load_image(probe_img_path)
    if img is None:
        return {"match": False, "score": 0.0, "person": target,
                "error": f"Cannot read image: {probe_img_path}"}

    faces = extract_probe_embeddings(img, detector, recognizer)
    if not faces:
        return {"match": False, "score": 0.0, "person": target,
                "error": "no face detected", "face_count": 0}

    best_score = -1.0
    best_info = None

    for emb, info in faces:
        score = cosine_similarity(emb, target.embedding)
        if score > best_score:
            best_score = score
            best_info = info

    return {
        "match":  best_score >= SIMILARITY_THR,
        "score":  round(best_score, 4),
        "person": target,
        **best_info,
    }


def search_face(
    probe_img_path: str,
    persons: list[PersonRecord],
    detector: FaceDetector,
    recognizer: FaceRecognizer,
    top_k: int = 5,
) -> list[dict]:
    """
    1:N Search -- find the top-K most similar people in the personnel database 
    for EACH face detected in the probe image.

    Returns:
        [
            {
               "face_info": dict,
               "matches": [{"score": float, "person": PersonRecord}, ...]
            },
            ...
        ]
    """
    img = load_image(probe_img_path)
    if img is None:
        log.warning("Cannot read probe image: %s", probe_img_path)
        return []

    faces = extract_probe_embeddings(img, detector, recognizer)
    if not faces:
        log.warning("Probe extraction failed: no face detected")
        return []

    # Vectorized similarity: compute against all enrolled persons at once
    valid = [(p, p.embedding) for p in persons if p.embedding is not None]
    if not valid:
        return []

    db_persons, db_embs = zip(*valid)
    db_matrix = np.stack(db_embs)          # shape = (N, 512)

    results = []
    for emb, info in faces:
        fsize = info.get("face_size", ("?", "?"))
        log.info(
            "Face %d/%d — size:%dx%dpx  det_score:%.3f  blur:%.1f  aligned:%s  bbox:%s",
            info["face_idx"] + 1, info["face_count"],
            fsize[0], fsize[1],
            info["det_score"],
            info.get("blur_score", -1),
            info["used_align"],
            [int(v) for v in info["bbox"]],
        )
                 
        scores = db_matrix @ emb           # cosine similarity for all N persons

        top_idx = np.argsort(scores)[::-1][:top_k]
        matches = [
            {"score": round(float(scores[i]), 4), "person": db_persons[i]}
            for i in top_idx
            if scores[i] >= SIMILARITY_THR
        ]
        results.append({
            "face_info": info,
            "matches": matches
        })
        
    return results


def debug_probe(
    probe_img_path: str,
    persons: list[PersonRecord],
    detector: FaceDetector,
    recognizer: FaceRecognizer,
    top_k: int = 10,
) -> None:
    """
    Diagnostic tool: show top-K scores WITHOUT threshold filtering for ALL faces.
    Use this to determine if the similarity threshold needs adjustment.
    """
    img = load_image(probe_img_path)
    if img is None:
        print(f"[ERROR] Cannot read image: {probe_img_path}")
        return

    faces = extract_probe_embeddings(img, detector, recognizer)
    if not faces:
        print(f"\n── Probe Diagnostics ─────────────────────────────")
        print("  [FAIL] No face detected or extraction failed\n")
        return

    valid = [(p, p.embedding) for p in persons if p.embedding is not None]
    if not valid:
        print("  [FAIL] No enrolled persons with embeddings found.")
        return

    db_persons, db_embs = zip(*valid)
    db_matrix = np.stack(db_embs)

    print(f"\n── Probe Diagnostics ─────────────────────────────")
    print(f"  Faces detected : {len(faces)}")
    print(f"  Current SIMILARITY_THR = {SIMILARITY_THR}")
    
    for emb, info in faces:
        print(f"\n  ▶ Face {info['face_idx'] + 1} / {len(faces)}:")
        print(f"    Det confidence : {info.get('det_score', 'N/A')}")
        print(f"    Blur score     : {info.get('blur_score', 'N/A')}  (threshold={BLUR_THRESH})")
        print(f"    Alignment      : {'keypoint-aligned' if info.get('used_align') else 'bbox-crop (lower accuracy)'}")
        print(f"    BBox           : {[int(x) for x in info['bbox']]}")

        scores    = db_matrix @ emb
        top_idx   = np.argsort(scores)[::-1][:top_k]

        print(f"\n    ── Top-{top_k} Candidates (no threshold applied) ──────")
        print(f"      {'Rank':<5} {'Score':<8} {'Match?':<8} {'Name':<12} {'ID'}")
        print(f"      {'─'*5} {'─'*8} {'─'*8} {'─'*12} {'─'*20}")
        for rank, i in enumerate(top_idx, 1):
            s  = float(scores[i])
            p  = db_persons[i]
            ok = "✓ YES" if s >= SIMILARITY_THR else "✗ no"
            print(f"      {rank:<5} {s:<8.4f} {ok:<8} {p.xm:<12} {p.zjhm}")
    print()



# ══════════════════════════════════════════════
# Main workflows
# ══════════════════════════════════════════════
def load_models() -> tuple[FaceDetector, FaceRecognizer]:
    """Load both ONNX models. Call this once and reuse across operations."""
    return FaceDetector(MODEL_DET), FaceRecognizer(MODEL_REC)


def build_database():
    """
    Full pipeline: query DB -> save photos -> extract embeddings -> save cache.
    Run on first use or when personnel data needs to be refreshed.
    """
    persons = fetch_persons_from_db()
    save_photos(persons)
    detector, recognizer = load_models()
    extract_embeddings(persons, detector, recognizer, force=False)
    save_person_db(persons)
    log.info(
        "Database built successfully. Records with valid embeddings: %d",
        sum(1 for p in persons if p.embedding is not None)
    )


def rebuild_features():
    """
    Re-extract ALL gallery embeddings using the current preprocessing pipeline
    (CLAHE + aligned crop), WITHOUT re-querying the database or re-saving photos.

    ⚠ MUST RUN THIS if:
      - You previously built the database WITHOUT CLAHE preprocessing
      - The gallery photos are already saved in face_data/photos/
      - You want probe and gallery to use the same feature extractor

    This deletes all existing .npy files and recomputes from saved JPEGs.
    Typical runtime: ~3-8 min for 2300 persons on CPU (ONNX).
    """
    if not DB_CACHE_FILE.exists():
        log.error("person_db.pkl not found. Run build_database() first.")
        return

    persons = load_person_db()

    # Reload photo_path for each person (may be None if pkl was saved without it)
    missing = 0
    for p in persons:
        expected = PHOTO_DIR / f"{p.zjhm}.jpg"
        if expected.exists():
            p.photo_path = str(expected)
        else:
            p.photo_path = None
            missing += 1

    if missing > 0:
        log.warning("%d persons have no saved photo — they will be skipped. "
                    "Run build_database() to re-fetch photos from DB.", missing)

    # Delete old .npy files so extract_embeddings re-processes everything
    old_files = list(FEATURE_DIR.glob("*.npy"))
    log.info("Deleting %d old embedding files ...", len(old_files))
    for f in old_files:
        f.unlink()

    detector, recognizer = load_models()
    extract_embeddings(persons, detector, recognizer, force=False)
    save_person_db(persons)
    log.info(
        "Feature rebuild complete. Valid embeddings: %d / %d",
        sum(1 for p in persons if p.embedding is not None), len(persons)
    )


def demo_search(probe_path: str):
    """Demo: 1:N search using a probe image."""
    persons = load_person_db()
    detector, recognizer = load_models()
    results = search_face(probe_path, persons, detector, recognizer, top_k=3)
    if not results:
        print("No matching person found or no faces detected.")
        return
        
    for res in results:
        info = res["face_info"]
        print(f"\n▶ Face at bbox {[int(x) for x in info['bbox']]} (det_score: {info['det_score']}):")
        if not res["matches"]:
            print("  No matches above similarity threshold.")
            continue
            
        for r in res["matches"]:
            p = r["person"]
            print(f"  Match -> Name: {p.xm}  |  ID: {p.zjhm}  |  Score: {r['score']:.4f}")


def demo_verify(probe_path: str, zjhm: str):
    """Demo: 1:1 verification against a specific enrolled person."""
    persons = load_person_db()
    detector, recognizer = load_models()
    result = verify_face(probe_path, zjhm, persons, detector, recognizer)
    p = result.get("person")
    print(f"Name: {p.xm if p else 'N/A'}  |  Score: {result['score']}  |  Match: {result['match']}")


# ─────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) == 1:
        # Default: build the personnel feature database
        build_database()

    elif sys.argv[1] == "rebuild":
        # Re-extract gallery embeddings with current preprocessing (no DB query needed)
        # ⚠ Run this after any change to preprocessing pipeline
        rebuild_features()

    elif sys.argv[1] == "search" and len(sys.argv) >= 3:
        # Usage: python face_recognition_pipeline.py search <probe_image_path>
        demo_search(sys.argv[2])

    elif sys.argv[1] == "verify" and len(sys.argv) >= 4:
        # Usage: python face_recognition_pipeline.py verify <probe_image_path> <id_number>
        demo_verify(sys.argv[2], sys.argv[3])

    elif sys.argv[1] == "debug" and len(sys.argv) >= 3:
        # Usage: python face_recognition_pipeline.py debug <probe_image_path>
        # Shows top-10 candidates WITHOUT threshold — use to diagnose poor results
        _persons = load_person_db()
        _det, _rec = load_models()
        debug_probe(sys.argv[2], _persons, _det, _rec)

    else:
        print("Usage:")
        print("  python face_recognition_pipeline.py                              # Build personnel database (first run)")
        print("  python face_recognition_pipeline.py rebuild                      # ⚠ Re-extract gallery features with new preprocessing")
        print("  python face_recognition_pipeline.py search <image_path>          # 1:N face search")
        print("  python face_recognition_pipeline.py verify <image_path> <id_no>  # 1:1 face verify")
        print("  python face_recognition_pipeline.py debug  <image_path>          # Diagnose: show top-10 scores without threshold")
