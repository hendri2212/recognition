import os
import numpy as np
import cv2
import insightface
from typing import Tuple

# Initialize InsightFace model
model = insightface.app.FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
model.prepare(ctx_id=0)

# Destination 5-point landmarks for 112×112 aligned output
DST = np.array([
    [38.2946, 51.6963],
    [73.5318, 51.5014],
    [56.0252, 71.7366],
    [41.5493, 92.3655],
    [70.7299, 92.2041],
], dtype=np.float32)

# Create debug directories
os.makedirs("face_crops", exist_ok=True)
os.makedirs("debug_align", exist_ok=True)


def crop_with_margin(
    img: np.ndarray,
    bbox: np.ndarray,
    margin: float = 0.4
) -> Tuple[np.ndarray, Tuple[int, int]]:
    """
    Crop the image around the face bbox with proportional margin.
    Returns the ROI and its top-left offset in the original image.
    """
    x1, y1, x2, y2 = bbox.astype(int)
    w, h = x2 - x1, y2 - y1
    dx, dy = int(w * margin), int(h * margin)
    x1m, y1m = max(0, x1 - dx), max(0, y1 - dy)
    x2m, y2m = min(img.shape[1], x2 + dx), min(img.shape[0], y2 + dy)
    roi = img[y1m:y2m, x1m:x2m]
    return roi, (x1m, y1m)


def process_face_align(
    img: np.ndarray,
    face,
    idx: int = 0
) -> np.ndarray:
    """
    Align a single face to a 112×112 crop using 5-point landmarks.
    Returns None if alignment fails.
    """
    # Crop with margin, get offset
    roi, (offx, offy) = crop_with_margin(img, face.bbox)

    # Compute source landmarks relative to the cropped ROI
    src = face.kps.astype(np.float32) - np.array([offx, offy], dtype=np.float32)
    # Estimate affine transform
    M, _ = cv2.estimateAffinePartial2D(src, DST, method=cv2.LMEDS)
    if M is None:
        return None

    # Warp with reflect border to preserve edges
    aligned = cv2.warpAffine(
        roi,
        M,
        (112, 112),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REFLECT
    )
    # Save aligned crops for inspection
    cv2.imwrite(f"face_crops/align_{idx}.png", aligned)
    cv2.imwrite(f"debug_align/debug_align_{idx}.png", aligned)
    return aligned


def extract_embedding(
    img_bytes: bytes,
    return_all: bool = False
):
    """
    Detect faces and extract their normalized embeddings.
    If return_all=False, returns first embedding or None.
    Else returns list of {{'embedding', 'box'}}.
    """
    img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
    dets = model.get(img)
    if not dets:
        return [] if return_all else None

    outputs = []
    for i, face in enumerate(dets):
        emb = None
        # Try aligned embedding
        aligned = process_face_align(img, face, idx=i)
        if aligned is not None:
            redets = model.get(aligned)
            if redets:
                emb = redets[0].embedding.astype(np.float32)
            else:
                print(f"[Warning] re-detection failed for face {i}, fallback to initial embedding.")
        # Fallback to initial embedding
        if emb is None:
            if hasattr(face, 'embedding'):
                emb = face.embedding.astype(np.float32)
                print(f"[Info] using initial embedding for face {i}.")
            else:
                continue
        # L2 normalization
        norm = np.linalg.norm(emb)
        if norm > 0:
            emb /= norm
        outputs.append({
            'embedding': emb,
            'box': face.bbox.astype(int).tolist()
        })
        if not return_all:
            return emb

    return outputs if return_all else None


def compare_embeddings(
    e1: np.ndarray,
    e2: np.ndarray,
    threshold: float = 0.4
) -> bool:
    """
    Compare two normalized embeddings using cosine distance.
    Returns True if distance < threshold.
    """
    cos_sim = np.dot(e1, e2)
    dist = 1.0 - cos_sim
    print(f"Cosine distance: {dist:.4f}")
    return dist < threshold