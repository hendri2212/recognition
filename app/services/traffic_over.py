import cv2
import json
import numpy as np
import os
from pathlib import Path
import tempfile
from typing import Dict, Any
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import base64
from ultralytics import YOLO

# =========================
# Model & Konstanta Umum
# =========================
# Gunakan model yang sedikit lebih akurat
# yolo = YOLO('yolov8s.pt')  # ganti sesuai kebutuhan
yolo = YOLO('yolov8l.pt')  # ganti sesuai kebutuhan
# yolo = YOLO('yolo11n.pt')  # ganti sesuai kebutuhan

HELMET_MODEL_PATH = Path("helmet_yolov8n.pt")
helmet_yolo = YOLO(str(HELMET_MODEL_PATH)) if HELMET_MODEL_PATH.exists() else None

OVERLOAD_MODEL_PATH = Path(os.getenv("OVERLOAD_MODEL_PATH", "truck_overload.pt"))
overload_yolo = YOLO(str(OVERLOAD_MODEL_PATH)) if OVERLOAD_MODEL_PATH.exists() else None
ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY", "usB9KjLcvNNqmLFZg8hm").strip()
ROBOFLOW_OVERLOAD_MODEL_ID = os.getenv(
    "ROBOFLOW_OVERLOAD_MODEL_ID",
    "truck-overload-6na0e-cbi6q/1",
).strip()
ROBOFLOW_OVERLOAD_API_URL = os.getenv(
    "ROBOFLOW_OVERLOAD_API_URL",
    "https://detect.roboflow.com",
).rstrip("/")
ROBOFLOW_LP_MODEL_ID = os.getenv(
    "ROBOFLOW_LP_MODEL_ID",
    "license-plate-recognition-rxg4e/11",
).strip()
ROBOFLOW_LP_API_URL = os.getenv(
    "ROBOFLOW_LP_API_URL",
    "https://detect.roboflow.com",
).rstrip("/")

# (opsional) percepat jika ada GPU
try:
    import torch
    if torch.cuda.is_available():
        yolo.to('cuda')
        yolo.fuse()
        if helmet_yolo is not None:
            helmet_yolo.to('cuda')
            helmet_yolo.fuse()
        if overload_yolo is not None:
            overload_yolo.to('cuda')
            overload_yolo.fuse()
except Exception:
    pass

# Daftar kelas untuk fungsi detect_traffic_violations.
# Class helmet/no_helmet/rider hanya akan muncul jika model YOLO yang dipakai
# memang dilatih dengan label tersebut. Model COCO bawaan hanya punya kendaraan.
TRAFFIC_CLASSES = {
    'person',
    'car',
    'truck',
    'bus',
    'motorcycle',
    'cell_phone',
    'helmet',
    'no_helmet',
    'rider',
}

TRAFFIC_CONF = 0.25
TRAFFIC_IMG_SIZE = 960
TRAFFIC_FALLBACK_CONF = 0.12
TRAFFIC_FALLBACK_IMG_SIZE = 1280
TRAFFIC_RUN_FALLBACK_ALWAYS = True
HELMET_CONF = 0.25
HELMET_IMG_SIZE = 640
VIDEO_SAMPLE_FPS = 1.0
VIDEO_MAX_FRAMES = 120

LABEL_ALIASES = {
    'cell phone': 'cell_phone',
    'mobile_phone': 'cell_phone',
    'mobile phone': 'cell_phone',
    'phone': 'cell_phone',
    'with_helmet': 'helmet',
    'with helmet': 'helmet',
    'without_helmet': 'no_helmet',
    'without helmet': 'no_helmet',
    'ride': 'rider',
    'motorbike': 'motorcycle',
    'motor': 'motorcycle',
    'no helmet': 'no_helmet',
    'no-helmet': 'no_helmet',
}


def _normalize_label(label: str) -> str:
    normalized = str(label).strip().lower().replace('-', '_').replace(' ', '_')
    return LABEL_ALIASES.get(normalized, normalized)


def _box_iou(a, b) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)
    iw = max(0, ix2 - ix1)
    ih = max(0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
    area_b = max(0, bx2 - bx1) * max(0, by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def _merge_detections(primary, fallback, iou_threshold: float = 0.70):
    merged = list(primary)
    for candidate in fallback:
        duplicate = False
        for existing in merged:
            if candidate["label"] != existing["label"]:
                continue
            if _box_iou(candidate["box"], existing["box"]) >= iou_threshold:
                duplicate = True
                if candidate["confidence"] > existing["confidence"]:
                    existing.update(candidate)
                break
        if not duplicate:
            merged.append(candidate)
    return merged


def _traffic_result_to_detections(result, model, allowed_classes=None):
    detections = []
    raw_count = 0
    filtered_labels = {}
    allowed = set(allowed_classes) if allowed_classes else TRAFFIC_CLASSES

    if result.boxes is None or len(result.boxes) == 0:
        return detections, {
            "raw_count": raw_count,
            "kept_count": 0,
            "filtered_labels": filtered_labels,
        }

    for box, cls, conf in zip(result.boxes.xyxy, result.boxes.cls, result.boxes.conf):
        raw_count += 1
        raw_label = model.model.names[int(cls)]
        label = _normalize_label(raw_label)
        confidence = float(conf)

        if label not in allowed:
            filtered_labels[label] = filtered_labels.get(label, 0) + 1
            continue

        x1, y1, x2, y2 = box.tolist()
        detections.append({
            "label": label,
            "raw_label": raw_label,
            "confidence": round(confidence, 4),
            "box": [int(x1), int(y1), int(x2), int(y2)],
            "violation_type": "no_helmet" if label == "no_helmet" else None,
            "helmet_violation": label == "no_helmet",
        })

    return detections, {
        "raw_count": raw_count,
        "kept_count": len(detections),
        "filtered_labels": filtered_labels,
    }


# =========================
# FUNGSI TETAP (JANGAN DIUBAH)
# =========================
def detect_traffic_violations(img_bytes: bytes, *, classes=None, return_debug: bool = False):
    """
    Deteksi objek menggunakan YOLO dan kembalikan bounding boxes dan label.
    Mengembalikan kendaraan serta class helmet/no_helmet/rider jika tersedia
    pada model yang digunakan. no_helmet ditandai sebagai pelanggaran helm.
    """
    img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        out = {
            "detections": [],
            "debug": {"error": "failed_to_decode_image"},
        }
        return out if return_debug else out["detections"]

    selected_classes = None
    if classes:
        selected_classes = {
            label for label in (_normalize_label(c) for c in classes)
            if label in TRAFFIC_CLASSES
        }

    result = yolo(img, conf=TRAFFIC_CONF, imgsz=TRAFFIC_IMG_SIZE, verbose=False)[0]
    detections, first_debug = _traffic_result_to_detections(result, yolo, selected_classes)
    fallback_used = False
    fallback_debug = None
    helmet_debug = None

    if TRAFFIC_RUN_FALLBACK_ALWAYS or not detections:
        fallback_used = True
        result = yolo(
            img,
            conf=TRAFFIC_FALLBACK_CONF,
            imgsz=TRAFFIC_FALLBACK_IMG_SIZE,
            verbose=False,
        )[0]
        fallback_detections, fallback_debug = _traffic_result_to_detections(result, yolo, selected_classes)
        detections = _merge_detections(detections, fallback_detections)

    if helmet_yolo is not None:
        helmet_result = helmet_yolo(
            img,
            conf=HELMET_CONF,
            imgsz=HELMET_IMG_SIZE,
            verbose=False,
        )[0]
        helmet_detections, helmet_debug = _traffic_result_to_detections(
            helmet_result,
            helmet_yolo,
            selected_classes,
        )
        detections = _merge_detections(detections, helmet_detections)

    has_helmet_violation = any(d.get("helmet_violation") for d in detections)
    if has_helmet_violation:
        plates = _detect_license_plates_with_roboflow(img_bytes)
        for d in detections:
            if d.get("helmet_violation"):
                plate = _match_license_plate(d["box"], plates)
                if plate:
                    d["license_plate"] = plate

    if not return_debug:
        return detections

    return {
        "detections": detections,
        "debug": {
            "model": "yolov8l.pt",
            "helmet_model": str(HELMET_MODEL_PATH) if helmet_yolo is not None else None,
            "selected_classes": sorted(selected_classes) if selected_classes else sorted(TRAFFIC_CLASSES),
            "conf": TRAFFIC_CONF,
            "imgsz": TRAFFIC_IMG_SIZE,
            "fallback_used": fallback_used,
            "fallback_conf": TRAFFIC_FALLBACK_CONF if fallback_used else None,
            "fallback_imgsz": TRAFFIC_FALLBACK_IMG_SIZE if fallback_used else None,
            "first_pass": first_debug,
            "fallback_pass": fallback_debug,
            "helmet_pass": helmet_debug,
        },
    }


def detect_traffic_violations_in_video(
    video_bytes: bytes,
    *,
    classes=None,
    sample_fps: float = VIDEO_SAMPLE_FPS,
    max_frames: int = VIDEO_MAX_FRAMES,
    return_debug: bool = False,
):
    if not video_bytes:
        return {
            "frames": [],
            "summary": {"frames_analyzed": 0, "detections": 0, "helmet_violations": 0},
            "debug": {"error": "empty_video"},
        }

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            tmp.write(video_bytes)
            tmp_path = tmp.name

        cap = cv2.VideoCapture(tmp_path)
        if not cap.isOpened():
            return {
                "frames": [],
                "summary": {"frames_analyzed": 0, "detections": 0, "helmet_violations": 0},
                "debug": {"error": "failed_to_open_video"},
            }

        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if fps <= 0:
            fps = 25.0

        step = max(1, int(round(fps / max(sample_fps, 0.1))))
        frames = []
        frame_idx = 0
        analyzed = 0

        while analyzed < max_frames:
            ok, frame = cap.read()
            if not ok:
                break

            if frame_idx % step == 0:
                ok_img, encoded = cv2.imencode(".jpg", frame)
                if ok_img:
                    result = detect_traffic_violations(
                        encoded.tobytes(),
                        classes=classes,
                        return_debug=return_debug,
                    )
                    detections = result["detections"] if isinstance(result, dict) else result
                    frames.append({
                        "frame": frame_idx,
                        "time": round(frame_idx / fps, 3),
                        "detections": detections,
                    })
                    analyzed += 1

            frame_idx += 1

        cap.release()

        total_detections = sum(len(item["detections"]) for item in frames)
        helmet_violations = sum(
            1
            for item in frames
            for detection in item["detections"]
            if detection.get("helmet_violation")
        )
        output = {
            "frames": frames,
            "summary": {
                "frames_analyzed": analyzed,
                "detections": total_detections,
                "helmet_violations": helmet_violations,
                "source_fps": round(fps, 3),
                "total_frames": total_frames,
                "sample_fps": sample_fps,
                "frame_step": step,
            },
        }
        if return_debug:
            output["debug"] = {
                "max_frames": max_frames,
                "classes": classes,
            }
        return output
    finally:
        if tmp_path:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except Exception:
                pass


# =========================
# Utilitas untuk Overload
# =========================
# Parameter default (bisa di-tuning per kamera)
_CONF = 0.30
_IOU = 0.45
_MIN_TRUCK_W = 60
_MIN_TRUCK_H = 60
_EDGE_LO = 80
_EDGE_HI = 160
_MIN_EDGE_PCT = 0.02   # min % piksel edge per baris
_CABIN_RATIO = 0.35   # ~perkiraan tinggi kabin relatif tinggi bbox truk
_OVERLOAD_THR = 0.85  # rasio h_muatan_atas_bak / h_kabin
_SMOOTH_K = 5         # moving average untuk profil edge

def _preprocess_roi(roi: np.ndarray) -> np.ndarray:
    """Enhance kontras & kurangi noise agar Hough/Canny lebih stabil."""
    if roi.ndim == 3:
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    else:
        gray = roi
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    return gray

def _moving_avg(x: np.ndarray, k: int) -> np.ndarray:
    if k <= 1:
        return x
    k = min(k, max(1, len(x) // 2 * 2 + 1))  # ganjil & tak berlebihan
    return cv2.blur(x.astype(np.float32).reshape(-1, 1), (1, k)).ravel()

def _estimate_bed_line(truck_roi: np.ndarray):
    """
    Estimasi garis bak (bed top line).
    1) Canny → HoughLinesP → pilih garis horizontal dominan di 40–70% tinggi ROI.
    2) Fallback: puncak gradien vertikal (Sobel Y) pada rentang yang sama.
    """
    h, w = truck_roi.shape[:2]
    gray = _preprocess_roi(truck_roi)
    edges = cv2.Canny(gray, _EDGE_LO, _EDGE_HI)

    lines = cv2.HoughLinesP(
        edges, 1, np.pi / 180, threshold=80,
        minLineLength=max(20, w // 3), maxLineGap=10
    )
    ys = []
    if lines is not None:
        for x1, y1, x2, y2 in lines[:, 0, :]:
            if abs(y2 - y1) <= 3:  # ~horizontal
                ymid = (y1 + y2) // 2
                if int(0.4 * h) <= ymid <= int(0.7 * h):
                    length = max(1, abs(x2 - x1))
                    ys += [ymid] * int(length / 10 + 1)
    if ys:
        return int(np.median(ys))

    # Fallback: puncak gradien (energi tepi) di 40–70% tinggi ROI
    sobel_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    profile = np.mean(np.abs(sobel_y), axis=1)
    lo, hi = int(0.4 * h), int(0.7 * h)
    if hi - lo < 5:
        return None
    segment = profile[lo:hi]
    if segment.size == 0:
        return None
    y_local = int(np.argmax(_moving_avg(segment, 7)))
    return lo + y_local


# =========================
# DETECT OVERLOAD (Refactor)
# =========================
# --- helper untuk mapping nama kelas ---
def _get_names_map():
    names = getattr(yolo, "names", None)
    if names is None:
        names = getattr(getattr(yolo, "model", None), "names", None)
    if isinstance(names, dict):
        return {int(k): v for k, v in names.items()}
    elif isinstance(names, (list, tuple)):
        return {i: v for i, v in enumerate(names)}
    return {}

def _class_id_by_name(names_map, target: str):
    for k, v in names_map.items():
        if str(v).lower() == target.lower():
            return int(k)
    return None


def _specialist_prediction_to_box(pred: Dict[str, Any]):
    if all(k in pred for k in ("x", "y", "width", "height")):
        cx = float(pred["x"])
        cy = float(pred["y"])
        w = float(pred["width"])
        h = float(pred["height"])
        return [
            int(round(cx - w / 2)),
            int(round(cy - h / 2)),
            int(round(cx + w / 2)),
            int(round(cy + h / 2)),
        ]
    if all(k in pred for k in ("x1", "y1", "x2", "y2")):
        return [int(pred["x1"]), int(pred["y1"]), int(pred["x2"]), int(pred["y2"])]
    return None


def _detect_overload_with_local_model(img: np.ndarray, conf: float, iou: float, imgsz: int):
    if overload_yolo is None:
        return [], "none"

    result = overload_yolo(img, conf=conf, iou=iou, imgsz=imgsz, verbose=False)[0]
    if result.boxes is None or len(result.boxes) == 0:
        return [], "local"

    names = getattr(overload_yolo, "names", {}) or {}
    detections = []
    xyxy = result.boxes.xyxy.cpu().numpy()
    clss = result.boxes.cls.int().cpu().numpy()
    confs = result.boxes.conf.cpu().numpy()
    for box, cls_id, score in zip(xyxy, clss, confs):
        label = str(names.get(int(cls_id), int(cls_id))).lower()
        detections.append({
            "label": _normalize_label(label),
            "box": [int(box[0]), int(box[1]), int(box[2]), int(box[3])],
            "confidence": float(score),
            "overload": "overload" in label,
        })
    return detections, "local"


def _detect_overload_with_roboflow(img_bytes: bytes):
    if not ROBOFLOW_API_KEY or not ROBOFLOW_OVERLOAD_MODEL_ID:
        return [], "none"

    query = urlencode({"api_key": ROBOFLOW_API_KEY, "format": "json"})
    url = f"{ROBOFLOW_OVERLOAD_API_URL}/{ROBOFLOW_OVERLOAD_MODEL_ID}?{query}"
    request = Request(
        url,
        data=img_bytes,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError):
        return [], "error"

    detections = []
    for pred in payload.get("predictions", []):
        box = _specialist_prediction_to_box(pred)
        if box is None:
            continue
        label = _normalize_label(pred.get("class", "truck_overload"))
        detections.append({
            "label": label,
            "box": box,
            "confidence": float(pred.get("confidence", 0.0)),
            "overload": "overload" in label,
        })
    return detections, "roboflow"


import logging

def _detect_license_plates_with_roboflow(img_bytes: bytes):
    if not ROBOFLOW_API_KEY or not ROBOFLOW_LP_MODEL_ID:
        return []

    try:
        img_b64 = base64.b64encode(img_bytes).decode("utf-8")
        query = urlencode({"api_key": ROBOFLOW_API_KEY, "confidence": 10})
        url = f"{ROBOFLOW_LP_API_URL}/{ROBOFLOW_LP_MODEL_ID}?{query}"
        request = Request(
            url,
            data=img_b64.encode("utf-8"),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
            try:
                with open(r"d:\CODE\newface\roboflow_debug.json", "w") as f:
                    json.dump(payload, f, indent=2)
            except Exception as e:
                logging.error(f"Failed to dump debug: {e}")
    except HTTPError as e:
        err_msg = e.read().decode("utf-8")
        with open(r"d:\CODE\newface\roboflow_err.txt", "w") as f:
            f.write(f"HTTP Error {e.code}: {err_msg}")
        logging.error(f"Roboflow LP HTTPError: {err_msg}")
        return []
    except Exception as e:
        with open(r"d:\CODE\newface\roboflow_err.txt", "w") as f:
            f.write(f"Exception: {str(e)}")
        logging.error(f"Roboflow LP Exception: {e}")
        return []

    detections = []
    for pred in payload.get("predictions", []):
        box = _specialist_prediction_to_box(pred)
        if box is None:
            continue
            
        # Beberapa model OCR Roboflow menaruh teks di field 'ocr_text', 'text', 'name', atau 'class'
        plate_text = pred.get("ocr_text") or pred.get("text") or pred.get("name") or pred.get("class", "")
        plate_text = str(plate_text).strip()
        
        # Jika teksnya hanya "license_plate" atau "plate" (label objek, bukan teks plat), kosongkan
        if plate_text.lower() in ["license_plate", "license-plate", "plate", "vehicle", "car", "motorcycle"]:
            plate_text = ""
            
        if not plate_text:
            continue
                    
        detections.append({
            "text": plate_text,
            "box": box,
            "confidence": float(pred.get("confidence", 0.0)),
        })
    return detections


def _match_license_plate(target_box, plates):
    if not plates:
        return None
        
    best_plate = None
    best_dist = float('inf')
    
    tx1, ty1, tx2, ty2 = target_box
    tcx = (tx1 + tx2) / 2.0
    tcy = (ty1 + ty2) / 2.0
    
    for plate in plates:
        px1, py1, px2, py2 = plate["box"]
        pcx = (px1 + px2) / 2.0
        pcy = (py1 + py2) / 2.0
        
        # Cari plat nomor yang jarak titik tengahnya paling dekat dengan objek pelanggar
        dist = (tcx - pcx)**2 + (tcy - pcy)**2
        if dist < best_dist:
            best_dist = dist
            best_plate = plate["text"]
            
    return best_plate


def _detect_overload_with_specialist(img: np.ndarray, img_bytes: bytes, conf: float, iou: float, imgsz: int):
    detections, source = _detect_overload_with_local_model(img, conf, iou, imgsz)
    if source == "local":
        return detections, source
    return _detect_overload_with_roboflow(img_bytes)


def _overload_model_available(source: str) -> bool:
    return source in {"local", "roboflow"}


def detect_overload(
    img_bytes: bytes,
    *,
    conf: float = 0.30,
    iou: float = 0.45,
    imgsz: int = 1280,
    # fallback kandidat truk: tetap kelas truck, hanya lebih sensitif.
    enable_fallback: bool = True,
    fb_conf: float = 0.15,
    fb_imgsz: int = 1536,
    # heuristik hanya untuk eksperimen lama; jangan jadikan keputusan default.
    enable_heuristic_decision: bool = False,
    min_edge_pct: float = 0.02,
    cabin_ratio: float = 0.35,
    overload_ratio_thr: float = 0.85,
    specialist_conf: float = 0.25,
    specialist_iou_match: float = 0.30,
    smooth_k: int = 5,
    return_debug: bool = False
):
    """
    Step:
      1) PASS-1: deteksi khusus kelas 'truck' (pakai classes=[truck_id]).
      2) PASS-2 (fallback, opsional): deteksi ulang kelas 'truck' dengan conf lebih rendah.
      3) Nilai overload hanya dari model specialist lokal/hosted, kecuali heuristik lama
         dinyalakan eksplisit untuk eksperimen.

    Output: {"trucks": [...], "overload_supported": bool, "overload_model_source": str}
    """
    img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return {"trucks": [], "error": "failed_to_decode_image"}

    H, W = img.shape[:2]
    names_map = _get_names_map()
    truck_id = _class_id_by_name(names_map, "truck")

    # ---------- PASS-1: fokus 'truck' ----------
    if truck_id is not None:
        res1 = yolo(img, conf=conf, iou=iou, imgsz=imgsz, classes=[truck_id], verbose=False)[0]
    else:
        # kalau mapping kelas tidak ketemu, deteksi semua dulu
        res1 = yolo(img, conf=conf, iou=iou, imgsz=imgsz, verbose=False)[0]

    cand_boxes = []
    cand_sources = []

    if res1.boxes is not None and len(res1.boxes) > 0:
        xyxy = res1.boxes.xyxy.cpu().numpy()
        clss = res1.boxes.cls.int().cpu().numpy()
        for b, c in zip(xyxy, clss):
            label = names_map.get(int(c), str(int(c)))
            if str(label).lower() == "truck" or truck_id is None:
                cand_boxes.append([int(b[0]), int(b[1]), int(b[2]), int(b[3])])
                cand_sources.append("truck_pass")

    # ---------- PASS-2 (fallback) ----------
    fb_used = False
    if enable_fallback and len(cand_boxes) == 0:
        fb_used = True
        fb_kwargs = dict(conf=fb_conf, iou=iou, imgsz=fb_imgsz, verbose=False)
        if truck_id is not None:
            res2 = yolo(img, classes=[truck_id], **fb_kwargs)[0]
        else:
            res2 = yolo(img, **fb_kwargs)[0]

        if res2.boxes is not None and len(res2.boxes) > 0:
            xyxy = res2.boxes.xyxy.cpu().numpy()
            clss = res2.boxes.cls.int().cpu().numpy()
            for b, c in zip(xyxy, clss):
                x1, y1, x2, y2 = [int(v) for v in b]
                label = str(names_map.get(int(c), int(c))).lower()
                if label == "truck" or truck_id is None:
                    cand_boxes.append([x1, y1, x2, y2])
                    cand_sources.append("truck_fallback")

    specialist_detections, specialist_source = _detect_overload_with_specialist(
        img,
        img_bytes,
        conf=specialist_conf,
        iou=iou,
        imgsz=imgsz,
    )
    for det in specialist_detections:
        if not det.get("overload"):
            continue
        duplicate = any(_box_iou(det["box"], box) >= 0.50 for box in cand_boxes)
        if not duplicate:
            cand_boxes.append(det["box"])
            cand_sources.append(f"{specialist_source}_specialist")

    overload_supported = _overload_model_available(specialist_source)
    unavailable_note = (
        "specialist_overload_model_unavailable"
        if not overload_supported and not enable_heuristic_decision
        else None
    )

    # ---------- Jika tetap kosong, kembalikan kosong untuk transparansi ----------
    outputs = []
    if len(cand_boxes) == 0:
        out = {
            "trucks": outputs,
            "overload_supported": overload_supported,
            "overload_model_source": specialist_source,
        }
        if unavailable_note:
            out["note"] = unavailable_note
        if return_debug:
            out["debug"] = {
                "pass1_zero": True,
                "fallback_used": fb_used,
                "enable_heuristic_decision": enable_heuristic_decision,
                "specialist_source": specialist_source,
                "specialist_count": len(specialist_detections),
                "names_map": names_map,
                "note": "no_truck_found"
            }
        return out

    # ---------- Nilai overload per kandidat truk ----------
    for (x1, y1, x2, y2), candidate_source in zip(cand_boxes, cand_sources):
        # clamp bbox
        x1 = max(0, min(x1, W - 1)); x2 = max(0, min(x2, W - 1))
        y1 = max(0, min(y1, H - 1)); y2 = max(0, min(y2, H - 1))
        if x2 <= x1 or y2 <= y1:
            continue

        roi = img[y1:y2, x1:x2]
        h, w = roi.shape[:2]
        if h < 60 or w < 60:
            outputs.append({
                "label": "truck",
                "box": [x1, y1, x2, y2],
                "overload": False,
                "ratio": None,
                "overload_source": "unavailable" if unavailable_note else "specialist",
                "candidate_source": candidate_source,
                "bed_line_found": False,
                "note": "roi_too_small"
            })
            continue

        bed_y = _estimate_bed_line(roi) if enable_heuristic_decision else None
        overload_flag, ratio = False, None
        dbg = {}
        overload_source = "unavailable" if unavailable_note else "specialist"

        specialist_match = None
        for det in specialist_detections:
            if det.get("overload") and _box_iou([x1, y1, x2, y2], det["box"]) >= specialist_iou_match:
                if specialist_match is None or det.get("confidence", 0.0) > specialist_match.get("confidence", 0.0):
                    specialist_match = det

        if specialist_match is not None:
            overload_flag = True
            overload_source = specialist_source
            if return_debug:
                dbg.update({
                    "specialist_label": specialist_match.get("label"),
                    "specialist_confidence": float(specialist_match.get("confidence", 0.0)),
                    "specialist_box": specialist_match.get("box"),
                })
        elif enable_heuristic_decision and bed_y is not None and 5 < bed_y < h - 5:
            above = roi[:bed_y, :]
            gray_above = _preprocess_roi(above)
            edges = cv2.Canny(gray_above, 80, 160)

            row_counts = np.count_nonzero(edges, axis=1).astype(np.float32)
            # smoothing
            k = max(1, smooth_k)
            row_counts = cv2.blur(row_counts.reshape(-1, 1), (1, k)).ravel()

            thr_by_pct = max(1.0, min_edge_pct * edges.shape[1])
            thr_by_p70 = max(1.0, np.percentile(row_counts, 70))
            edge_thr = max(thr_by_pct, thr_by_p70)

            idx = np.where(row_counts >= edge_thr)[0]
            if idx.size > 0:
                top_load = int(idx[0])
                h_above = max(1, bed_y - top_load)
                h_cabin = max(1, int(cabin_ratio * h))
                ratio = float(h_above / h_cabin)
                overload_flag = ratio > float(overload_ratio_thr)

                if return_debug:
                    dbg.update({
                        "bed_y": int(bed_y),
                        "top_load": top_load,
                        "h_above": int(h_above),
                        "h_cabin_est": int(h_cabin),
                        "edge_thr": float(edge_thr),
                        "row_counts_p70": float(np.percentile(row_counts, 70)),
                        "row_counts_max": float(np.max(row_counts)),
                    })
            else:
                if return_debug:
                    dbg.update({"bed_y": int(bed_y), "edge_hits": 0})

        outputs.append({
            "label": "truck",
            "box": [x1, y1, x2, y2],
            "overload": bool(overload_flag),
            "ratio": float(ratio) if ratio is not None else None,
            "overload_source": overload_source,
            "candidate_source": candidate_source,
            "bed_line_found": bed_y is not None,
            **({"note": unavailable_note} if unavailable_note else {}),
            **({"debug": dbg} if return_debug else {})
        })

    has_overload = any(t.get("overload") for t in outputs)
    if has_overload:
        plates = _detect_license_plates_with_roboflow(img_bytes)
        for t in outputs:
            if t.get("overload"):
                plate = _match_license_plate(t["box"], plates)
                if plate:
                    t["license_plate"] = plate

    out = {
        "trucks": outputs,
        "overload_supported": overload_supported or enable_heuristic_decision,
        "overload_model_source": specialist_source,
        "decision_policy": "specialist_or_explicit_heuristic" if enable_heuristic_decision else "specialist_only",
    }
    if unavailable_note:
        out["note"] = unavailable_note
    if return_debug:
        out["debug"] = {
            "fallback_used": fb_used,
            "detected_candidates": len(cand_boxes),
            "enable_heuristic_decision": enable_heuristic_decision,
            "specialist_source": specialist_source,
            "specialist_count": len(specialist_detections),
            "names_map": names_map
        }
    return out
