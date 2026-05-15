from fastapi import APIRouter, UploadFile, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import cv2
import numpy as np

from app.services.face import extract_embedding  # <- only this helper is needed

from app.models.user import User
from app.models.person import Person
from app.core.config import EMB_DIM
from app.core.db import get_db

router = APIRouter()


def save_sample(db: Session, emb: np.ndarray, person_id: int, name: str):
    """
    Save a normalized embedding sample as raw Float32 bytes.
    Assumes 'emb' is already L2-normalized float32 (helper ensures this,
    but we re-normalize defensively).
    """
    emb = emb.astype(np.float32, copy=False)
    n = float(np.linalg.norm(emb))
    if n > 0:
        emb = emb / n
    db.add(User(
        name=name,
        embedding=emb.tobytes(),
        person_id=person_id
    ))


@router.post("/register")
async def register(
    name: str = Form(...),
    file: UploadFile = Form(...),
    db: Session = Depends(get_db)
):
    # 1) Read raw bytes (dipakai langsung oleh extract_embedding)
    img_bytes = await file.read()
    if not img_bytes:
        raise HTTPException(status_code=400, detail="File gambar kosong")

    # 2) Ekstrak embedding & metadata wajah (pakai return_all=True untuk dapat bbox)
    outputs = extract_embedding(img_bytes, return_all=True)
    if not outputs:
        raise HTTPException(status_code=400, detail="Wajah tidak terdeteksi")

    # Ambil wajah terbaik (elemen pertama sudah terurut di helper)
    best = outputs[0]
    emb0 = best["embedding"]
    if not isinstance(emb0, np.ndarray):
        raise HTTPException(status_code=500, detail="Embedding tidak valid")

    # 3) Siapkan/temukan Person
    person = db.query(Person).filter(Person.name == name).first()
    if not person:
        person = Person(name=name)
        db.add(person)
        db.flush()  # dapatkan person.id

    saved = 0

    # 4) Simpan embedding utama
    save_sample(db, emb0, person.id, name)
    saved += 1

    # 5) (Opsional) Augmentasi berbasis ROI wajah untuk menambah variasi
    #    - pakai bbox dari helper; lalu crop -> resize 112x112
    #    - dari tiap augment, ambil embedding lagi via extract_embedding
    img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is not None and "box" in best and isinstance(best["box"], list):
        x1, y1, x2, y2 = map(int, best["box"])
        h, w = img.shape[:2]

        # padding 20% untuk amankan crop
        pad_x = int(0.2 * (x2 - x1))
        pad_y = int(0.2 * (y2 - y1))
        x1p = max(0, x1 - pad_x)
        y1p = max(0, y1 - pad_y)
        x2p = min(w, x2 + pad_x)
        y2p = min(h, y2 + pad_y)

        face_roi = img[y1p:y2p, x1p:x2p]
        if face_roi.size:
            face_roi = cv2.resize(face_roi, (112, 112), interpolation=cv2.INTER_LINEAR)

            # daftar augmentasi ringan
            transforms = [
                lambda x: x,  # identitas (crop murni)
                lambda x: cv2.flip(x, 1),
                lambda x: cv2.warpAffine(x, cv2.getRotationMatrix2D((56, 56), 15, 1.0), (112, 112)),
                lambda x: cv2.warpAffine(x, cv2.getRotationMatrix2D((56, 56), -15, 1.0), (112, 112)),
                lambda x: cv2.convertScaleAbs(x, alpha=1.0, beta=30),
                lambda x: cv2.convertScaleAbs(x, alpha=1.0, beta=-30),
            ]

            for fn in transforms:
                try:
                    aug = fn(face_roi)
                    ok, enc = cv2.imencode(".jpg", aug)
                    if not ok:
                        continue
                    aug_bytes = enc.tobytes()

                    # pakai helper lagi untuk dapat embedding dari hasil augment
                    emb_aug = extract_embedding(aug_bytes, return_all=False)
                    if isinstance(emb_aug, np.ndarray):
                        save_sample(db, emb_aug, person.id, name)
                        saved += 1
                except Exception as e:
                    # Jangan gagalkan pendaftaran hanya karena satu augment gagal
                    print(f"[Augment warn] {e}")

    # 6) Commit semua sample user
    db.commit()

    # 7) Ambil ulang semua embedding user, validasi dimensi, hitung rata-rata (mean)
    users = db.query(User).filter(User.person_id == person.id).all()
    if not users:
        raise HTTPException(status_code=500, detail="Tidak ada sampel tersimpan")

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
    n = float(np.linalg.norm(mean_emb))
    if n > 0:
        mean_emb = mean_emb / n

    person.mean_embedding = mean_emb.tobytes()
    db.add(person)
    db.commit()

    # 8) Response ringkas
    return JSONResponse(content={
        "person_id": person.id,
        "name": name,
        "samples_saved": saved,
        "mean_computed": int(embs.shape[0])
    })