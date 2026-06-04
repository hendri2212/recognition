# Newface Backend

## Kebutuhan Sistem

Saat project dipindah ke komputer lokal lain, siapkan aplikasi berikut:

- Python 3.10 atau 3.11 direkomendasikan untuk kompatibilitas library ML.
- Node.js dan npm untuk frontend Vue/Vite.
- MySQL atau MariaDB untuk database.
- Git, opsional untuk clone/pull project.
- Microsoft Visual C++ Build Tools, kadang diperlukan saat install `insightface`.
- Driver NVIDIA/CUDA opsional jika ingin menjalankan inference dengan GPU. Tanpa GPU, aplikasi tetap bisa berjalan dengan CPU.

## File Penting Yang Harus Ikut Dicopy

Pastikan file model berikut tetap ada di root project:

- `yolov8l.pt`
- `helmet_yolov8n.pt`
- `yolov8n.pt`
- `yolov8s.pt`
- `yolo11n.pt`
- `truck_overload.pt`, jika memakai model overload lokal.

InsightFace akan mengunduh model `buffalo_l` saat pertama dijalankan. Jika komputer baru tidak punya internet, copy cache InsightFace dari komputer lama, biasanya dari:

```text
C:\Users\<user>\.insightface
```

## Setup Backend

Buat virtual environment dan install dependency Python:

```powershell
cd D:\CODE\newface
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install ultralytics onnxruntime torch
```

Jika PowerShell memblokir aktivasi virtual environment, jalankan pip lewat Python di `.venv`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install ultralytics onnxruntime torch
```

Dependency tambahan `ultralytics`, `onnxruntime`, dan `torch` diperlukan karena dipakai oleh service deteksi kendaraan dan wajah.

## Setup Database

Install MySQL/MariaDB, lalu buat database:

```sql
CREATE DATABASE newface;
```

Konfigurasi koneksi database ada di `app/core/config.py`:

```python
DATABASE_URL = "mysql+mysqlconnector://root:@localhost/newface"
```

Sesuaikan username, password, host, atau nama database jika konfigurasi MySQL di komputer baru berbeda.

Saat backend dijalankan, tabel utama akan dibuat otomatis dari model SQLAlchemy:

- `persons`
- `users`
- `vehicles`

Catatan: file `database/facerecog.sql` adalah dump lama untuk database `facerecog` dan tidak sama dengan schema aktif aplikasi saat ini. Jika ingin memindahkan data produksi/terbaru, lakukan dump dari database `newface` di komputer lama lalu import ke komputer baru.

Contoh dump dan import:

```powershell
mysqldump -u root -p newface > newface.sql
mysql -u root -p newface < newface.sql
```

## Setup Frontend

Install dependency frontend:

```powershell
cd D:\CODE\newface\frontend
npm.cmd install
```

Gunakan `npm.cmd` di PowerShell Windows jika `npm` biasa gagal karena execution policy.

## Environment Variable Opsional

Untuk fitur overload/Roboflow:

```powershell
$env:OVERLOAD_MODEL_PATH="D:\CODE\newface\truck_overload.pt"
$env:ROBOFLOW_API_KEY="<api-key-roboflow>"
$env:ROBOFLOW_OVERLOAD_MODEL_ID="truck-overload-6na0e-cbi6q/1"
$env:ROBOFLOW_LP_MODEL_ID="license-plate-recognition-rxg4e/11"
```

Jika memakai model overload lokal, simpan bobot YOLO dengan kelas seperti `truck_overload` di path `OVERLOAD_MODEL_PATH` atau `truck_overload.pt` pada root project.

## Menjalankan Project

Jalankan backend:

```powershell
cd D:\CODE\newface
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Atau menggunakan `Makefile`:

```powershell
make run
```

Jalankan frontend di terminal terpisah:

```powershell
cd D:\CODE\newface\frontend
npm.cmd run dev
```

Buka frontend:

```text
http://localhost:5173
```

Backend berjalan di:

```text
http://localhost:8000
```

Frontend saat ini memanggil backend melalui `http://localhost:8000`, jadi pastikan backend berjalan di port tersebut.

## Truck overload model

Endpoint `POST /over` mendeteksi kandidat kelas `truck` memakai YOLO COCO. Status `overload`
ditentukan dengan model overload khusus:

1. Model overload khusus lokal, jika file tersedia.
2. Roboflow hosted model, jika `ROBOFLOW_API_KEY` tersedia.

Jika model overload khusus tidak tersedia, endpoint tetap mengembalikan kandidat truk tetapi
`overload_supported` bernilai `false`. Hasil tersebut tidak boleh dibaca sebagai truk normal
atau overload.

Konfigurasi opsional:

```powershell
$env:OVERLOAD_MODEL_PATH="D:\CODE\newface\truck_overload.pt"
$env:ROBOFLOW_API_KEY="<api-key-roboflow>"
$env:ROBOFLOW_OVERLOAD_MODEL_ID="truck-overload-6na0e-cbi6q/1"
```

Jika memakai model lokal, simpan bobot YOLO dengan kelas seperti `truck_overload`
di path `OVERLOAD_MODEL_PATH` atau `truck_overload.pt` pada root project.

Heuristik visual lama masih ada untuk eksperimen melalui argumen service
`enable_heuristic_decision=True`, tetapi nonaktif pada route `/over` secara default karena
false positive tinggi pada kendaraan non-truk atau box vehicle.
