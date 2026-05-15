from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from app.services.traffic_over import (
    detect_traffic_violations,
    detect_traffic_violations_in_video,
    detect_overload,
)

router = APIRouter()

@router.post("/traffic")
async def traffic_violation(
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
        if isinstance(results, dict) and "detections" in results:
            return JSONResponse(content=results)
        return JSONResponse(content={"detections": results})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/traffic-video")
async def traffic_video_violation(
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
        return JSONResponse(content=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/over")
async def overload_detection(file: UploadFile = File(...)):
    img_bytes = await file.read()
    try:
        results = detect_overload(img_bytes)
        if isinstance(results, dict) and "trucks" in results:
            return JSONResponse(content=results)
        return JSONResponse(content={"trucks": results})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
