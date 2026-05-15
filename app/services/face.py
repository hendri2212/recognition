from __future__ import annotations

import os
import time
import hashlib
import threading
from typing import List, Dict, Tuple, Optional, Union
from collections import OrderedDict

import numpy as np
import cv2
import onnxruntime as ort
from insightface.app import FaceAnalysis


# ---------- Provider selection ----------
def select_providers(prefer_gpu: bool = True) -> Tuple[List[str], int]:
    """
    Return (providers, ctx_id). ctx_id=0 jika GPU provider tersedia & dipakai, else -1 (CPU).
    Urutan prioritas: CUDA -> DirectML -> ROCm -> CoreML -> OpenVINO -> CPU
    """
    avail = set(ort.get_available_providers())

    preferred_order = [
        "CUDAExecutionProvider",
        "DmlExecutionProvider",         # DirectML (Windows)
        "ROCMExecutionProvider",
        "CoreMLExecutionProvider",
        "OpenVINOExecutionProvider",
    ]

    selected: List[str] = []
    ctx_id = -1

    if prefer_gpu:
        for p in preferred_order:
            if p in avail:
                selected.append(p)
                ctx_id = 0  # FaceAnalysis ctx_id=0 => GPU
                break

    # Tambahkan CPU sebagai fallback terakhir SELALU
    selected.append("CPUExecutionProvider")
    # Jika prefer_gpu=False atau tidak ada GPU: ctx_id tetap -1 (CPU)
    return selected, ctx_id


# ---------- Simple LRU cache untuk embeddings/outputs ----------
class LRUCache:
    def __init__(self, maxsize: int = 512):
        self.maxsize = maxsize
        self._store: OrderedDict[str, object] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str):
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
                return self._store[key]
            return None

    def set(self, key: str, value: object):
        with self._lock:
            self._store[key] = value
            self._store.move_to_end(key)
            if len(self._store) > self.maxsize:
                self._store.popitem(last=False)

    def clear(self):
        with self._lock:
            self._store.clear()


# ---------- Inti servis ----------
class FaceEmbedder:
    def __init__(
        self,
        prefer_gpu: bool = True,
        det_size: Tuple[int, int] = (640, 640),
        cache_size: int = 512,
        debug_io: bool = False,
    ):
        # (Opsional) thread/env tuning — aman untuk kebanyakan workload
        os.environ.setdefault("OMP_NUM_THREADS", "1")
        os.environ.setdefault("OMP_WAIT_POLICY", "PASSIVE")

        providers, ctx_id = select_providers(prefer_gpu=prefer_gpu)
        self.providers = providers
        self.ctx_id = ctx_id
        self.det_size = det_size
        self.debug_io = debug_io

        # Inisialisasi FaceAnalysis satu kali (hemat memori & cepat)
        # Upaya memaksa modul genderage ikut dimuat; fallback untuk versi lama.
        try:
            self.app = FaceAnalysis(
                name="buffalo_l",
                providers=self.providers,
                allowed_modules=["detection", "recognition", "genderage"],
            )
        except TypeError:
            # allowed_modules tidak tersedia di sebagian versi InsightFace
            self.app = FaceAnalysis(name="buffalo_l", providers=self.providers)

        # ctx_id: 0 jika GPU, -1 jika CPU
        self.app.prepare(ctx_id=self.ctx_id, det_size=self.det_size)

        # Lock untuk operasi get() agar aman di multi-thread server
        self._lock = threading.Lock()

        # Cache hasil untuk konten yang identik (berbasis bytes)
        self._cache = LRUCache(maxsize=cache_size)

        # Warmup ringan untuk load model & JIT graph
        self._warmup()

        if self.debug_io:
            os.makedirs("debug_align", exist_ok=True)
            os.makedirs("face_crops", exist_ok=True)

    def _warmup(self):
        img = np.zeros((224, 224, 3), dtype=np.uint8)
        with self._lock:
            _ = self.app.get(img)

    @staticmethod
    def _hash_bytes(b: bytes) -> str:
        return hashlib.md5(b).hexdigest()

    @staticmethod
    def _ensure_bgr_uint8(img: np.ndarray) -> np.ndarray:
        # Pastikan contiguous uint8 BGR (OpenCV)
        if img is None:
            raise ValueError("Gambar tidak valid (None).")
        if img.dtype != np.uint8:
            img = img.astype(np.uint8, copy=False)
        if not img.flags["C_CONTIGUOUS"]:
            img = np.ascontiguousarray(img)
        # Asumsikan input OpenCV sudah BGR; jika kamu kirim RGB, convert di luar.
        return img

    @staticmethod
    def _normalize_gender(gender_val: Union[int, float, str, None]) -> Optional[str]:
        """
        InsightFace umumnya mengembalikan 0/1 (0=female, 1=male) atau string 'male'/'female'.
        Kembalikan 'male' / 'female' / None.
        """
        if gender_val is None:
            return None
        # angka -> bulatkan ke 0/1
        if isinstance(gender_val, (int, float)) or hasattr(gender_val, "item"):
            try:
                return "male" if int(round(float(gender_val))) == 1 else "female"
            except Exception:
                return None
        # string
        if isinstance(gender_val, str):
            g = gender_val.strip().lower()
            if g in ("m", "male", "1"):
                return "male"
            if g in ("f", "female", "0"):
                return "female"
        return None

    @staticmethod
    def _safe_int(v: Union[int, float, str, None]) -> Optional[int]:
        try:
            return int(round(float(v)))
        except Exception:
            return None

    def _faces_to_outputs(self, faces, return_all: bool):
        """
        Konversi objek Face (insightface) -> list of dict:
        {
          'embedding': np.ndarray(float32, L2-normalized),
          'box': [x1,y1,x2,y2],
          'kps': [[x,y],...]*5?,
          'score': float?,
          'age': int? (perkiraan),
          'gender': 'male'/'female'/None,
          'gender_raw': raw value from model (0/1/str),
        }
        Jika return_all=False => kembalikan 1 embedding (np.ndarray) terbaik (kompatibel API lama).
        """
        if not faces:
            return [] if return_all else None

        # Pilih face terbaik berdasarkan det_score (fallback: area bbox)
        def face_key(f):
            sc = getattr(f, "det_score", None)
            if sc is not None:
                return sc
            x1, y1, x2, y2 = f.bbox.astype(int)
            return (x2 - x1) * (y2 - y1)

        faces_sorted = sorted(faces, key=face_key, reverse=True)
        outputs = []

        for i, f in enumerate(faces_sorted):
            # --- Embedding (normed) ---
            emb = getattr(f, "normed_embedding", None)
            if emb is None:
                emb = getattr(f, "embedding", None)
                if emb is not None:
                    emb = emb.astype(np.float32, copy=False)
                    n = np.linalg.norm(emb)
                    if n > 0:
                        emb = emb / n
                else:
                    # Tidak ada embedding (recognition belum aktif?) — tetap izinkan atribut lain
                    emb = None

            if emb is not None:
                emb = emb.astype(np.float32, copy=False)

            # --- Atribut dasar ---
            out = {
                "embedding": emb,
                "box": f.bbox.astype(int).tolist(),
            }
            if hasattr(f, "kps"):
                out["kps"] = f.kps.astype(float).tolist()
            if hasattr(f, "det_score"):
                out["score"] = float(f.det_score)

            # --- Estimasi umur & gender (jika tersedia) ---
            age_val = getattr(f, "age", None)
            sex_val = getattr(f, "gender", None)
            if sex_val is None:
                sex_val = getattr(f, "sex", None)  # sebagian versi pakai 'sex'

            out["age"] = self._safe_int(age_val) if age_val is not None else None
            out["gender"] = self._normalize_gender(sex_val)
            # simpan raw supaya bisa dianalisa kalau perlu
            if isinstance(sex_val, (int, float)) or hasattr(sex_val, "item"):
                try:
                    out["gender_raw"] = float(sex_val)
                except Exception:
                    out["gender_raw"] = sex_val
            else:
                out["gender_raw"] = sex_val

            # Simpan crop debug (optional)
            if self.debug_io:
                x1, y1, x2, y2 = f.bbox.astype(int)
                x1 = max(0, x1); y1 = max(0, y1)
                crop = self._last_img[y1:y2, x1:x2]
                if crop.size:
                    cv2.imwrite(f"face_crops/face_{i}.png", crop)

            outputs.append(out)

            # Kompatibilitas API lama: jika hanya minta satu, kembalikan embedding saja
            if not return_all:
                return emb  # np.ndarray atau None

        return outputs if return_all else None

    def _detect_internal(self, img: np.ndarray):
        """Panggil insightface untuk ambil daftar faces (objek)."""
        with self._lock:
            faces = self.app.get(img)
        return faces

    def embed_image(self, img: np.ndarray, return_all: bool = False):
        """
        Ambil embedding dari gambar (numpy BGR).
        return_all=False => satu embedding terbaik (np.ndarray) atau None.
        return_all=True  => list of dict (lihat _faces_to_outputs)
        """
        img = self._ensure_bgr_uint8(img)
        self._last_img = img  # untuk debug crop
        faces = self._detect_internal(img)
        return self._faces_to_outputs(faces, return_all=return_all)

    def embed_bytes(self, img_bytes: bytes, return_all: bool = False):
        """
        Ambil embedding dari bytes (JPEG/PNG).
        Cache berdasarkan hash bytes untuk menghindari komputasi berulang.
        """
        key = self._hash_bytes(img_bytes)
        cached = self._cache.get(key)
        if cached is not None:
            if return_all:
                return cached
            # cari embedding terbaik dari cache (urutan sudah disort)
            return cached[0]["embedding"] if (cached and cached[0].get("embedding") is not None) else None

        img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            return [] if return_all else None

        result = self.embed_image(img, return_all=True)  # list of dict
        # Simpan ke cache
        self._cache.set(key, result)

        return result if return_all else (result[0]["embedding"] if (result and result[0].get("embedding") is not None) else None)

    def detect_bytes(self, img_bytes: bytes) -> List[Dict]:
        """
        Deteksi wajah + atribut (box, score, kps, age, gender) dari bytes.
        Tidak fokus pada embedding — tetap ada jika model recognition aktif.
        Selalu mengembalikan list of dict (bisa kosong).
        """
        key = f"detect:{self._hash_bytes(img_bytes)}"
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            return []

        img = self._ensure_bgr_uint8(img)
        self._last_img = img
        faces = self._detect_internal(img)
        outputs = self._faces_to_outputs(faces, return_all=True)
        # Untuk deteksi: biasanya kita tidak perlu mengembalikan embedding (agar JSON-friendly)
        # Namun karena _faces_to_outputs sudah menyusupkan embedding jika ada, di sini kita "slim" kan.
        slim = []
        for f in outputs:
            slim.append({
                "box": f.get("box"),
                "score": f.get("score"),
                "kps": f.get("kps"),
                "age": f.get("age"),
                "gender": f.get("gender"),
                "gender_raw": f.get("gender_raw"),
            })
        self._cache.set(key, slim)
        return slim

    @staticmethod
    def compare(e1: np.ndarray, e2: np.ndarray, threshold: float = 0.4) -> bool:
        """
        Bandingkan dua embedding (cosine distance). True jika distance < threshold.
        """
        if e1 is None or e2 is None:
            return False
        e1 = e1.astype(np.float32, copy=False)
        e2 = e2.astype(np.float32, copy=False)
        # Asumsi sudah L2-normalized; jika belum, normalisasi ringan:
        n1 = np.linalg.norm(e1);  n2 = np.linalg.norm(e2)
        if n1 > 0: e1 = e1 / n1
        if n2 > 0: e2 = e2 / n2
        cos_sim = float(np.dot(e1, e2))
        dist = 1.0 - cos_sim
        return dist < threshold


# ---------- Singleton + API kompatibel dgn kode lama ----------
_EMBEDDER = FaceEmbedder(
    prefer_gpu=True,          # set False jika mau paksa CPU
    det_size=(640, 640),      # naikkan jika banyak wajah kecil; turun = lebih cepat
    cache_size=512,           # atur sesuai pola workload
    debug_io=False,           # True hanya saat debugging
)


def extract_embedding(img_bytes: bytes, return_all: bool = False):
    """
    API kompatibel:
    - return_all=False => satu embedding terbaik (np.ndarray) atau None
    - return_all=True  => list[{'embedding','box','kps?','score?','age?','gender?','gender_raw?'}]
    """
    return _EMBEDDER.embed_bytes(img_bytes, return_all=return_all)


def compare_embeddings(e1: np.ndarray, e2: np.ndarray, threshold: float = 0.4) -> bool:
    return _EMBEDDER.compare(e1, e2, threshold=threshold)


# ---------- API baru untuk atribut umur & gender ----------
def estimate_age_gender(img_bytes: bytes, return_all: bool = True):
    """
    Ambil estimasi umur & gender dari gambar.
    return_all=True  => list per wajah (bisa kosong)
    return_all=False => wajah terbaik atau None
    Output: {'age': int|None, 'gender': 'male'|'female'|None, 'score': float?, 'box': [x1,y1,x2,y2]}
    """
    faces = _EMBEDDER.embed_bytes(img_bytes, return_all=True) or []
    slim = [
        {
            "age": f.get("age"),
            "gender": f.get("gender"),
            "score": f.get("score"),
            "box": f.get("box"),
        }
        for f in faces
    ]
    return slim if return_all else (slim[0] if slim else None)


def detect_faces(img_bytes: bytes) -> List[Dict]:
    """
    Deteksi wajah + atribut minimal (tanpa mengembalikan embedding):
    [{'box','score','kps','age','gender','gender_raw'}]
    """
    return _EMBEDDER.detect_bytes(img_bytes)
