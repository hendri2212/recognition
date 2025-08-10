import insightface
import cv2
import numpy as np

model = insightface.app.FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
model.prepare(ctx_id=0)

def get_face_embedding(img):
    faces = model.get(img)
    if not faces:
        return None
    # Crop manual pakai bbox
    x1, y1, x2, y2 = faces[0].bbox.astype(int)
    # Pastikan bbox tidak keluar batas gambar
    h, w = img.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    face_img = img[y1:y2, x1:x2]
    face_img = cv2.resize(face_img, (112, 112))
    # Bisa gunakan face_img untuk debug/cetak hasil crop
    cv2.imwrite("face_crop_debug.png", face_img)
    # Embedding dari deteksi
    emb = faces[0].embedding
    return emb

img1 = cv2.imread('register.png')
img2 = cv2.imread('recognize.png')
# img2 = cv2.imread('20392689.jpeg')
emb1 = get_face_embedding(img1)
emb2 = get_face_embedding(img2)
if emb1 is None or emb2 is None:
    print("Face not detected.")
else:
    print("Distance:", np.linalg.norm(emb1 - emb2))