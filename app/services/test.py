import insightface
import cv2
import numpy as np

model = insightface.app.FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
model.prepare(ctx_id=0)

img = cv2.imread("20392689.jpeg")
faces1 = model.get(img)
faces2 = model.get(img)
emb1 = faces1[0].embedding
emb2 = faces2[0].embedding
print('Distance:', np.linalg.norm(emb1 - emb2))
print('Sample emb1:', emb1[:10])
print('Sample emb2:', emb2[:10])