from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler

from core.config import get_settings
from db.session import init_db
from jobs import refresh_kondisi_laut, refresh_zona_satelit
from routers import (
    kondisi_laut,
    laporan,
    nelayan,
    sos,
    sync,
    titik_favorit,
    trip_bbm,
    zona,
)

settings = get_settings()

# Definisikan scheduler secara global agar bisa dipantau
scheduler = BackgroundScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Inisialisasi Database (Membuat tabel & seeding stasiun kondisi laut)
    init_db()
    
    # 2. Jalankan scheduler hanya jika RUN_SCHEDULER=true.
    #    Ini mencegah job duplikat saat production berjalan multi-instance/replica.
    if settings.RUN_SCHEDULER:
        # Perbarui data satelit setiap 12 jam
        scheduler.add_job(refresh_zona_satelit.run, "interval", hours=12, id="refresh_satelit")
        # Perbarui cuaca/gelombang/pasut stasiun setiap 3 jam
        scheduler.add_job(refresh_kondisi_laut.run, "interval", hours=3, id="refresh_kondisi_laut")

        scheduler.start()

        # Jalankan sinkronisasi pertama kali secara cepat saat startup
        try:
            refresh_zona_satelit.run()
            refresh_kondisi_laut.run()
        except Exception as e:
            print(f"Gagal menjalankan jobs awal pada startup: {e}")

    yield

    # 3. Hentikan Scheduler saat aplikasi dimatikan
    if settings.RUN_SCHEDULER:
        scheduler.shutdown()

app = FastAPI(
    title="MuaroTrack API Server",
    description="Backend API server untuk sistem penunjang nelayan tradisional pesisir Padang pascabencana.",
    version="1.0.0",
    lifespan=lifespan
)

# Konfigurasi Middleware CORS agar bisa diakses oleh Expo Mobile App
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Daftarkan Router API
app.include_router(nelayan.router)
app.include_router(zona.router)
app.include_router(laporan.router)
app.include_router(trip_bbm.router)
app.include_router(kondisi_laut.router)
app.include_router(titik_favorit.router)
app.include_router(sos.router)
app.include_router(sync.router)

@app.get("/health", tags=["Sistem"])
def health_check():
    """
    Endpoint sederhana untuk memantau status kesehatan server backend.
    """
    return {"status": "ok", "message": "MuaroTrack API Server is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
