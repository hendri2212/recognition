# debug_routes.py
# Script untuk memeriksa routes yang terdaftar di FastAPI

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Buat app sederhana untuk testing
app = FastAPI()

# CORS configuration yang sama
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Import dan test router
try:
    from app.api.endpoints.traffic_over import router as traffic_over_router
    app.include_router(traffic_over_router, prefix="")
    print("✓ Router berhasil diimport dan ditambahkan")
except Exception as e:
    print(f"✗ Error import router: {e}")

# Fungsi untuk menampilkan semua routes
def print_routes():
    print("\n=== REGISTERED ROUTES ===")
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            methods = ', '.join(route.methods)
            print(f"{methods:<20} {route.path}")
        elif hasattr(route, 'path'):
            print(f"{'MOUNT':<20} {route.path}")

if __name__ == "__main__":
    print_routes()
    
    # Test import services
    try:
        from app.services.traffic_over import detect_traffic_violations, detect_overload
        print("\n✓ Services berhasil diimport")
    except Exception as e:
        print(f"\n✗ Error import services: {e}")