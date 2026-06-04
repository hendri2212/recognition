from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy import func
import urllib.request
import json
import logging
import cv2
import numpy as np

from app.core.db import SessionLocal
from app.models.vehicle import Vehicle
from app.models.person import Person
from app.models.user import User
from app.core.config import EMB_DIM
from app.services.face import extract_embedding
from app.services.traffic_over import (
    detect_traffic_violations,
    detect_traffic_violations_in_video,
    detect_overload,
)

router = APIRouter()

def process_violation_task(img_bytes: bytes | None, box: list | None, license_plate: str, violation_type: str):
    db = SessionLocal()
    try:
        clean_plate = license_plate.replace(" ", "").upper()
        vehicle = db.query(Vehicle).filter(
            func.replace(Vehicle.license_plate, " ", "") == clean_plate
        ).first()
        
        if not vehicle:
            return
            
        owner_name = vehicle.owner_name
        phone = vehicle.phone_number
        
        # 1. Kirim Notifikasi WhatsApp
        if phone:
            phone_str = phone.strip()
            if phone_str.startswith("0"):
                phone_str = "62" + phone_str[1:]
                
            message = f"Halo {owner_name}, kendaraan dengan plat nomor {license_plate} terdeteksi melakukan pelanggaran: {violation_type}."
            url = "https://wabot.tukarjual.com/send"
            payload = {"to": phone_str, "message": message}
            
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            try:
                with urllib.request.urlopen(req, timeout=10):
                    pass
            except Exception as e:
                logging.error(f"Failed to send WA message for {license_plate}: {e}")

        # 2. Registrasi Wajah
        if not owner_name or not img_bytes or not box:
            return
            
        img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            return
            
        x1, y1, x2, y2 = map(int, box)
        h, w = img.shape[:2]
        
        pad_x = int(0.1 * (x2 - x1))
        pad_y = int(0.1 * (y2 - y1))
        x1p = max(0, x1 - pad_x)
        y1p = max(0, y1 - pad_y)
        x2p = min(w, x2 + pad_x)
        y2p = min(h, y2 + pad_y)
        
        roi = img[y1p:y2p, x1p:x2p]
        if roi.size == 0:
            return
            
        ok, enc = cv2.imencode(".jpg", roi)
        if not ok:
            return
            
        outputs = extract_embedding(enc.tobytes(), return_all=True)
        if not outputs:
            return
            
        best = outputs[0]
        emb0 = best.get("embedding")
        if not isinstance(emb0, np.ndarray):
            return
            
        person = db.query(Person).filter(Person.name == owner_name).first()
        if not person:
            person = Person(name=owner_name)
            db.add(person)
            db.flush()
            
        emb0_norm = emb0.astype(np.float32, copy=False)
        n = float(np.linalg.norm(emb0_norm))
        if n > 0:
            emb0_norm = emb0_norm / n
            
        db.add(User(
            name=owner_name,
            embedding=emb0_norm.tobytes(),
            person_id=person.id
        ))
        db.commit()
        
        users = db.query(User).filter(User.person_id == person.id).all()
        all_embs = []
        for u in users:
            arr = np.frombuffer(u.embedding, dtype=np.float32)
            if arr.size == EMB_DIM:
                all_embs.append(arr)
                
        if all_embs:
            embs = np.stack(all_embs, axis=0)
            mean_emb = np.mean(embs, axis=0).astype(np.float32)
            n_mean = float(np.linalg.norm(mean_emb))
            if n_mean > 0:
                mean_emb = mean_emb / n_mean
            person.mean_embedding = mean_emb.tobytes()
            db.add(person)
            
        if vehicle.person_id != person.id:
            vehicle.person_id = person.id
            db.add(vehicle)
            
        db.commit()

    except Exception as e:
        logging.error(f"Failed to process violation task for {license_plate}: {e}")
    finally:
        db.close()


@router.post("/traffic")
async def traffic_violation(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    classes: str = Form(default=""),
):
    img_bytes = await file.read()
    try:
        selected_classes = [c.strip() for c in classes.split(",") if c.strip()]
        results = detect_traffic_violations(
            img_bytes,
            classes=selected_classes or None,
            return_debug=True,
        )
        
        detections = results.get("detections", []) if isinstance(results, dict) else results
        notified_plates = set()
        for d in detections:
            plate = d.get("license_plate")
            if d.get("helmet_violation") and plate and plate not in notified_plates:
                background_tasks.add_task(process_violation_task, img_bytes, d.get("box"), plate, "Tanpa Helm")
                notified_plates.add(plate)

        if isinstance(results, dict) and "detections" in results:
            return JSONResponse(content=results)
        return JSONResponse(content={"detections": results})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/traffic-video")
async def traffic_video_violation(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    classes: str = Form(default=""),
    sample_fps: float = Form(default=1.0),
    max_frames: int = Form(default=120),
):
    video_bytes = await file.read()
    try:
        selected_classes = [c.strip() for c in classes.split(",") if c.strip()]
        results = detect_traffic_violations_in_video(
            video_bytes,
            classes=selected_classes or None,
            sample_fps=sample_fps,
            max_frames=max_frames,
            return_debug=True,
        )
        
        frames = results.get("frames", []) if isinstance(results, dict) else []
        notified_plates = set()
        for frame in frames:
            for d in frame.get("detections", []):
                plate = d.get("license_plate")
                if d.get("helmet_violation") and plate and plate not in notified_plates:
                    background_tasks.add_task(process_violation_task, None, None, plate, "Tanpa Helm")
                    notified_plates.add(plate)

        return JSONResponse(content=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/over")
async def overload_detection(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    img_bytes = await file.read()
    try:
        results = detect_overload(img_bytes)
        
        trucks = results.get("trucks", []) if isinstance(results, dict) else results
        notified_plates = set()
        for t in trucks:
            plate = t.get("license_plate")
            if t.get("overload") and plate and plate not in notified_plates:
                background_tasks.add_task(process_violation_task, img_bytes, t.get("box"), plate, "Truk Overload")
                notified_plates.add(plate)

        if isinstance(results, dict) and "trucks" in results:
            return JSONResponse(content=results)
        return JSONResponse(content={"trucks": results})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
