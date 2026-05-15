from typing import List, Optional, Literal

import numpy as np
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.services.face import extract_embedding
from app.models.person import Person
from app.core.config import EMB_DIM
from app.core.db import get_db

router = APIRouter()

# Cosine distance threshold (0–2 range, typical threshold ~0.4)
THRESHOLD = 0.4


class RecognizeItem(BaseModel):
    """Single face recognition result."""
    box: list[int] = Field(..., min_length=4, max_length=4)
    name: str
    distance: float
    age: Optional[int] = None
    gender: Optional[Literal["male", "female"]] = None


def _cosine_distance_normalized(a: np.ndarray, b: np.ndarray) -> float:
    """
    Compute cosine distance (1 - cosine similarity) assuming a and b are already L2-normalized.
    Clamps dot product to [-1, 1] to avoid tiny numerical drift.
    """
    sim = float(np.clip(np.dot(a, b), -1.0, 1.0))
    return 1.0 - sim


def _normalize(v: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(v))
    if norm <= 0.0 or not np.isfinite(norm):
        return v
    return v / norm


@router.post("/recognize", response_model=List[RecognizeItem])
async def recognize(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Recognize faces in an uploaded image and (optionally) return age & gender if provided by service layer.
    Returns a list of recognition results (bounding boxes, names, distances, age, gender).
    """
    # 1) Read image bytes
    img_bytes = await file.read()

    # 2) Extract embeddings for all faces (with attributes if supported by service)
    try:
        faces = extract_embedding(img_bytes, return_all=True, with_attr=True)
    except TypeError:
        # Backward compatibility if service doesn't accept with_attr yet
        faces = extract_embedding(img_bytes, return_all=True)

    if not faces:
        raise HTTPException(status_code=400, detail="No faces detected")

    # 3) Load registered persons that have mean embeddings
    persons: list[Person] = (
        db.query(Person).filter(Person.mean_embedding != None).all()  # noqa: E711
    )
    if not persons:
        raise HTTPException(status_code=404, detail="No registered persons found")

    # Pre-materialize normalized reference embeddings to speed up loop
    ref_vectors: list[tuple[str, np.ndarray]] = []
    for p in persons:
        arr = np.frombuffer(p.mean_embedding, dtype=np.float32)
        if arr.size != EMB_DIM:
            # Skip malformed vectors silently
            continue
        ref_vectors.append((p.name, _normalize(arr)))

    if not ref_vectors:
        raise HTTPException(status_code=500, detail="Registered embeddings are malformed")

    results: list[RecognizeItem] = []

    # 4) Match each face against reference vectors
    for face in faces:
        emb: np.ndarray = face["embedding"].astype(np.float32, copy=False)
        emb = _normalize(emb)

        best_name = "unknown"
        best_dist = 2.0  # max cosine distance in this setup

        for name, mean_emb in ref_vectors:
            dist = _cosine_distance_normalized(emb, mean_emb)
            if dist < best_dist:
                best_dist = dist
                best_name = name

        label = best_name if best_dist < THRESHOLD else "unknown"

        # Attributes from service (optional)
        age = face.get("age")
        gender = face.get("gender")
        box = [int(c) for c in face["box"]]

        results.append(
            RecognizeItem(
                box=box,
                name=label,
                distance=round(float(best_dist), 4),
                age=int(age) if isinstance(age, (int, np.integer)) else None,
                gender=gender if gender in ("male", "female") else None,
            )
        )

    # 5) Return list directly so frontend can use data.map
    return results
