import cv2
import json
import base64
import urllib.request
from urllib.parse import urlencode

api_key = "usB9KjLcvNNqmLFZg8hm"
model_id = "license-plate-recognition-rxg4e/11"
api_url = "https://detect.roboflow.com"

cap = cv2.VideoCapture("traffic_test.mp4")
ok, frame = cap.read()
cap.release()

if ok:
    ok2, buf = cv2.imencode(".jpg", frame)
    if ok2:
        img_bytes = buf.tobytes()
        img_b64 = base64.b64encode(img_bytes).decode("utf-8")
        query = urlencode({"api_key": api_key, "confidence": 10})
        url = f"{api_url}/{model_id}?{query}"
        req = urllib.request.Request(
            url,
            data=img_b64.encode("utf-8"),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req) as response:
                payload = json.loads(response.read().decode("utf-8"))
                print(json.dumps(payload, indent=2))
        except Exception as e:
            print("Error:", e)
