# Newface Backend

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
