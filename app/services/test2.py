import insightface
import cv2
import numpy as np

# Ganti path file di bawah dengan file hasil download dari register dan recognize
img1_path = "register.png"
img2_path = "recognize.png"
# img2_path = "20392689.jpeg"

# Inisialisasi model
model = insightface.app.FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
model.prepare(ctx_id=0)

# Load gambar
img1 = cv2.imread(img1_path)
img2 = cv2.imread(img2_path)

# Deteksi wajah pada kedua gambar
faces1 = model.get(img1)
faces2 = model.get(img2)

if not faces1 or not faces2:
    print("Wajah tidak terdeteksi di salah satu gambar.")
    exit()

# Ambil embedding wajah pertama dari masing-masing gambar
emb1 = faces1[0].embedding
emb2 = faces2[0].embedding

# Hitung distance
distance = np.linalg.norm(emb1 - emb2)
print('Distance:', distance)
print('Sample emb1:', emb1[:10])
print('Sample emb2:', emb2[:10])

# Untuk verifikasi shape dan dtype
print('emb1 shape:', emb1.shape, 'dtype:', emb1.dtype)
print('emb2 shape:', emb2.shape, 'dtype:', emb2.dtype)