import urllib.request
import urllib.parse
import json
import os

api_key = "usB9KjLcvNNqmLFZg8hm"
model_id = "license-plate-recognition-rxg4e/11"
api_url = "https://detect.roboflow.com"

def test():
    # just create a dummy black image to test the API response structure
    import numpy as np
    import cv2
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    _, buf = cv2.imencode(".jpg", img)
    img_bytes = buf.tobytes()

    import base64
    img_b64 = base64.b64encode(buf.tobytes()).decode("utf-8")

    query = urllib.parse.urlencode({"api_key": api_key})
    url = f"{api_url}/{model_id}?{query}"
    
    req = urllib.request.Request(
        url,
        data=img_b64.encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))
            print(json.dumps(data, indent=2))
    except urllib.error.HTTPError as e:
        print(f"Error: {e.code} - {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test()
