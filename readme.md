# Newface Backend

## Truck overload model

Endpoint `POST /over` mendeteksi kandidat truk memakai YOLO COCO, lalu menentukan `overload`
dengan urutan berikut:

1. Model overload khusus lokal, jika file tersedia.
2. Roboflow hosted model, jika `ROBOFLOW_API_KEY` tersedia.
3. Heuristik visual lama sebagai fallback.

Konfigurasi opsional:

```powershell
$env:OVERLOAD_MODEL_PATH="D:\CODE\newface\truck_overload.pt"
$env:ROBOFLOW_API_KEY="<api-key-roboflow>"
$env:ROBOFLOW_OVERLOAD_MODEL_ID="truck-overload-6na0e-cbi6q/1"
```

Jika memakai model lokal, simpan bobot YOLO dengan kelas seperti `truck_overload`
di path `OVERLOAD_MODEL_PATH` atau `truck_overload.pt` pada root project.
