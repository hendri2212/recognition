from fastapi import APIRouter, UploadFile, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import cv2
import numpy as np

from app.services.face import model, process_face_align
from app.models.user import User
from app.models.person import Person
from app.core.config import EMB_DIM
from app.core.db import get_db

router = APIRouter()

def save_sample(db: Session, emb: np.ndarray, person_id: int, name: str):
    """
    Save a normalized embedding sample as raw Float32 bytes.
    """
    db.add(User(
        name=name,
        embedding=emb.astype(np.float32).tobytes(),
        person_id=person_id
    ))

@router.post("/register")
async def register(
    name: str = Form(...),
    file: UploadFile = Form(...),
    db: Session = Depends(get_db)
):
    # 1) Read & decode image bytes
    img_bytes = await file.read()
    img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Invalid image file")

    # 2) Detect face
    faces = model.get(img)
    if not faces:
        raise HTTPException(status_code=400, detail="Wajah tidak terdeteksi")
    face = faces[0]

    # 3) Align face for debug; embedding uses initial detection
    aligned = process_face_align(img, face)
    if aligned is None:
        print("[Info] Alignment unavailable, using original detection for embedding.")

    # 4) Ensure Person record exists
    person = db.query(Person).filter(Person.name == name).first()
    if not person:
        person = Person(name=name)
        db.add(person)
        db.flush()

    saved = 0
    # 5) Extract & normalize embedding from initial detection
    emb0 = face.embedding.astype(np.float32)
    emb0 /= np.linalg.norm(emb0)
    save_sample(db, emb0, person.id, name)
    saved += 1

    # 6) Apply augmentations if aligned image is available
    if aligned is not None:
        transforms = [
            lambda x: cv2.flip(x, 1),
            lambda x: cv2.warpAffine(
                x, cv2.getRotationMatrix2D((56,56), 15, 1.0), (112,112)
            ),
            lambda x: cv2.warpAffine(
                x, cv2.getRotationMatrix2D((56,56), -15, 1.0), (112,112)
            ),
            lambda x: cv2.convertScaleAbs(x, alpha=1.0, beta=30),
            lambda x: cv2.convertScaleAbs(x, alpha=1.0, beta=-30),
        ]
        for fn in transforms:
            try:
                aug = fn(aligned)
                det_aug = model.get(aug)
                if not det_aug:
                    continue
                emb_aug = det_aug[0].embedding.astype(np.float32)
                emb_aug /= np.linalg.norm(emb_aug)
                save_sample(db, emb_aug, person.id, name)
                saved += 1
            except Exception as e:
                print(f"[Error] Augmentation failed: {e}")

    # 7) Commit saved samples
    db.commit()

    # 8) Load embeddings, verify dimension, and compute mean
    users = db.query(User).filter(User.person_id == person.id).all()
    all_embs = []
    for u in users:
        arr = np.frombuffer(u.embedding, dtype=np.float32)
        if arr.size != EMB_DIM:
            raise HTTPException(
                status_code=500,
                detail=f"Embedding size invalid: {arr.size}, expected {EMB_DIM}"
            )
        all_embs.append(arr)
    embs = np.stack(all_embs, axis=0)

    mean_emb = np.mean(embs, axis=0).astype(np.float32)
    mean_emb /= np.linalg.norm(mean_emb)
    person.mean_embedding = mean_emb.tobytes()
    db.add(person)
    db.commit()

    # 9) Return summary
    return JSONResponse(content={
        "person_id": person.id,
        "name": name,
        "samples_saved": saved,
        "mean_computed": embs.shape[0]
    })