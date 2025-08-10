from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
import numpy as np

from app.services.face import extract_embedding
from app.models.person import Person
from app.core.config import EMB_DIM
from app.core.db import get_db

router = APIRouter()

# Cosine distance threshold (0–2 range, typical threshold ~0.4)
THRESHOLD = 0.4

@router.post("/recognize")
async def recognize(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Recognize faces in an uploaded image.
    Returns a list of recognition results (bounding boxes, names, distances).
    """
    # Read image bytes
    img_bytes = await file.read()

    # Extract embeddings for all faces
    faces = extract_embedding(img_bytes, return_all=True)
    if not faces:
        raise HTTPException(status_code=400, detail="No faces detected")

    # Load registered persons
    persons = db.query(Person).filter(Person.mean_embedding != None).all()
    if not persons:
        raise HTTPException(status_code=404, detail="No registered persons found")

    results = []
    for face in faces:
        emb = face['embedding']
        box = face['box']
        best = {'name': 'unknown', 'dist': 1.0}
        for p in persons:
            blob = p.mean_embedding
            arr = np.frombuffer(blob, dtype=np.float32)
            if arr.size != EMB_DIM:
                continue
            mean_emb = arr / np.linalg.norm(arr)
            dist = 1 - float(np.dot(emb, mean_emb))
            # **DEBUG PRINT per person**  
            print(f"[DEBUG] Distance ke {p.name}: {dist:.4f}")
            if dist < best['dist']:
                best = {'name': p.name, 'dist': dist}
        
        # **DEBUG PRINT best match untuk tiap face**  
        print(f"[DEBUG] Face@{box} → best match: {best['name']} (distance {best['dist']:.4f})")
        
        label = best['name'] if best['dist'] < THRESHOLD else 'unknown'
        results.append({
            'box': [int(c) for c in box],
            'name': label,
            'distance': round(best['dist'], 4)
        })

    # Return list directly so frontend can use data.map
    return results