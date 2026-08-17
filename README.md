# MuaroTrack Backend Server

> **GEMASTIK XIX (2026) — Cabang Kompetisi VIII: Pengembangan Perangkat Lunak (Software Development)**
> Tim: **alamak dahpulkam pulak** · ID Tim: **260010321952850** · Universitas Negeri Padang

Server backend untuk proyek **MuaroTrack** berbasis **Python FastAPI** dan **PostgreSQL+PostGIS**. Menyediakan API terintegrasi untuk rekomendasi zona tangkap, prediksi bahan bakar (BBM), transkripsi laporan suara nelayan menggunakan AI (Whisper + DeepSeek), caching kondisi laut (Open-Meteo & TideCheck), penyimpanan titik favorit nelayan, dan sistem darurat SOS (Expo Push Notification).

- Aplikasi mobile (frontend): [muarotrack-app](https://github.com/muhammadrafifatihulihsan/muarotrack-app)
- APK Android: https://drive.google.com/drive/folders/1hroWpdvEJpyKpmBJho8lzwqTEA6m6NHC
- Video demo: https://youtu.be/_h3ZziaByIQ

## Struktur Proyek

```
server/
├── main.py                  # Entrypoint aplikasi FastAPI (lifespan, scheduler)
├── core/                    # config.py (settings), deps.py
├── db/                      # base.py, session.py, schema.sql
├── jobs/                    # refresh_zona_satelit.py, refresh_kondisi_laut.py
├── models/                  # nelayan, zona, laporan, kondisi_laut, trip_bbm, titik_favorit, sos
├── routers/                 # nelayan, zona, laporan, sync, kondisi_laut, trip_bbm, titik_favorit, sos
├── schemas/                 # Validasi data (Pydantic)
├── services/                # scoring, geo, moon, stt, deepseek_client, gee_client, marine_client, sos_dispatch, zona_grid, dll.
├── tests/                   # 24 kasus uji (pytest)
├── docker-compose.yml       # PostgreSQL/PostGIS lokal
├── docker-compose.prod.yml  # Orkestrasi produksi
├── Dockerfile               # Image multi-stage non-root
├── requirements.txt         # Dependensi runtime
└── requirements-dev.txt     # Dependensi pengujian
```

## Prasyarat
1. **Docker Desktop** (untuk menjalankan database PostgreSQL+PostGIS lokal).
2. **Python 3.10+** (Virtual environment `venv` sudah disediakan di dalam folder `server/`).

---

## Langkah Setup & Pengembangan

### 1. Konfigurasi Environment Variables (`.env`)
Salin berkas `.env.example` menjadi `.env` (sudah dibuat otomatis oleh script scaffold):
- Edit file `server/.env` sesuai kebutuhan.
- Secara bawaan, `MOCK_EXTERNAL=true` aktif agar Anda tidak memerlukan API Key eksternal di awal.

### 2. Menjalankan Database PostgreSQL + PostGIS (Lokal Docker)
Pastikan Docker Desktop aktif di komputer Anda, lalu jalankan perintah berikut di direktori `server/` menggunakan terminal:
```powershell
docker compose up -d
```
Perintah ini akan menyalakan container PostgreSQL+PostGIS pada port `5432` dengan nama database `muarotrack`.

### 3. Menggunakan Database Supabase (Alternatif)
Jika ingin menggunakan Supabase:
1. Pastikan Anda mengaktifkan ekstensi PostGIS di dashboard Supabase (SQL Editor):
   ```sql
   CREATE EXTENSION IF NOT EXISTS postgis;
   ```
2. Salin Connection String (URI format) dari Supabase.
3. Buka `.env` dan ganti nilai `DATABASE_URL` dengan string koneksi tersebut.

### 4. Menginstal Dependensi Python
Aktifkan Virtual Environment yang sudah Anda buat, lalu instal pustaka yang dibutuhkan:
```powershell
# Aktifkan venv di terminal Windows (PowerShell)
.\venv\Scripts\activate

# Instal dependensi runtime
pip install -r requirements.txt

# Instal dependensi pengujian (dev)
pip install -r requirements-dev.txt
```

### 5. Menjalankan Pengujian Otomatis
Untuk memverifikasi instalasi dan memastikan semua fungsi bisnis (scoring, geo, dsb) berjalan hijau:
```powershell
pytest -v
```

### 6. Menjalankan Server Backend
Untuk menjalankan server FastAPI dalam mode auto-reload (development):
```powershell
uvicorn main:app --reload
```
Buka dokumentasi interaktif API (Swagger UI) di browser Anda: [http://localhost:8000/docs](http://localhost:8000/docs).

---

## Panduan Database (PostgreSQL + PostGIS)

- **[`DATABASE.md`](DATABASE.md)** — panduan ramah pemula: di mana database, cara melihat isinya (DBeaver/pgAdmin/psql), daftar 9 tabel, dan kaitan dengan kode ORM.
- **[`db/schema.sql`](db/schema.sql)** — file SQL lengkap (CREATE TABLE + indeks PostGIS + seed stasiun) yang sinkron dengan `server/models/*.py`.

Cek cepat isi database:
```bash
docker exec -it muarotrack-db psql -U postgres -d muarotrack -c "\dt"
```

---

## Command Cheat Sheet (Development)

Semua perintah dijalankan di folder `server/` pada terminal **PowerShell** (Windows).

| # | Perintah | Fungsi |
|---|----------|--------|
| 1 | `docker compose up -d` | Nyalakan database PostgreSQL + PostGIS (container `muarotrack-db`). |
| 2 | `.\venv\Scripts\activate` | Aktifkan virtual environment Python. (Linux/Mac: `source venv/bin/activate`) |
| 3 | `pip install -r requirements.txt` | Install dependensi runtime. |
| 4 | `pip install -r requirements-dev.txt` | Install dependensi pengujian (pytest, dsb). |
| 5 | `pytest -v` | Jalankan seluruh test otomatis (harapannya **24 passed**). |
| 6 | `uvicorn main:app --reload` | Jalankan server FastAPI (auto-reload untuk development). |
| 7 | Buka `http://localhost:8000/docs` | Swagger UI — uji semua endpoint dari browser. |
| 8 | `curl http://localhost:8000/health` | Health check server. |
| 9 | `docker compose down` | Matikan database (data tetap aman di volume). |
| 10 | `docker compose logs -f muarotrack-db` | Lihat log database. |

> **Android emulator:** dari aplikasi mobile gunakan `http://10.0.2.2:8000` (bukan localhost) untuk menjangkau server di laptop/PC.

---

## Konfigurasi Grid Zona Dinamis & Scheduler

Grid zona rekomendasi kini **dibangun dinamis dari posisi GPS nelayan** (bukan dikunci ke 3 muara). Variabel environment berikut mengontrol perilakunya:

| Variabel               | Default | Keterangan                                                         |
| ---------------------- | ------- | ------------------------------------------------------------------ |
| `ZONA_RADIUS_MAKS_KM`  | `22.0`  | Radius maksimum rekomendasi (≈12 mil laut). Titik di luar ini dibuang (hemat BBM). |
| `ZONA_JUMLAH_TITIK`    | `5`     | Jumlah titik grid dinamis per request (dibatasi agar GEE cepat).   |
| `BEARING_LAUT_DEG`     | `270.0` | Arah laut dari posisi nelayan (default Barat — pesisir Padang).    |
| `RUN_SCHEDULER`        | `true`  | Set `false` bila menjalankan lebih dari 1 replika API (hindari job duplikat). |

## Panduan Pengisian Kredensial API Eksternal
Untuk beralih ke layanan asli (non-mock), ubah `MOCK_EXTERNAL=false` di `.env` dan isi variabel berikut:
1. **DeepSeek API Key (`DEEPSEEK_API_KEY`)**: Daftar di [Platform DeepSeek](https://platform.deepseek.com) dan buat API Key baru.
2. **TideCheck API Key (`TIDECHECK_API_KEY`)**: Daftar di [TideCheck](https://tidecheck.com/developers) untuk mendapatkan API Key ramalan pasang surut air laut.
3. **Google Earth Engine (`GEE_PROJECT_ID`)**: Daftar di [Google Earth Engine](https://earthengine.google.com/signup). Buat project di Google Cloud, aktifkan Earth Engine API, dan masukkan project ID tersebut.
4. **Expo Access Token (`EXPO_ACCESS_TOKEN`)**: Buat akun di [Expo](https://expo.dev) dan dapatkan token akses untuk pengiriman push notification darurat SOS ke perangkat nelayan sekitar.

## Lisensi

- Lisensi kode sumber aplikasi: **MIT License** — lihat berkas [`LICENSE`](LICENSE)
- Daftar lisensi komponen pihak ketiga: [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md)

---

*Dikembangkan untuk Pagelaran Mahasiswa Nasional Bidang TIK (GEMASTIK) XIX Tahun 2026 — Universitas Negeri Padang.*

---

## Deployment Production (Docker)

Panduan lengkap menjalankan backend dalam mode **production** (Dockerfile multi-stage, `docker-compose.prod.yml`, backup/restore DB, rollback, deploy ke PaaS) tersedia di **[DEPLOYMENT.md](DEPLOYMENT.md)**.

```bash
# Ringkasan:
cp .env.production.example .env.production   # isi password & API keys
docker compose -f docker-compose.prod.yml up -d --build
```
