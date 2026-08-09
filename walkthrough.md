# Walkthrough Implementasi Backend Server MuaroTrack

Server backend **MuaroTrack** telah selesai dibangun secara lengkap dan terintegrasi (**v1 + v2**) menggunakan **Python FastAPI** dan **PostgreSQL+PostGIS**. Seluruh fungsionalitas dirancang kompatibel dengan **Python 3.13** dan menerapkan prinsip *Clean/Layered Architecture*.

---

## 1. Perubahan & Berkas yang Dibuat

### Konfigurasi & Scaffold Projek
- [docker-compose.yml](docker-compose.yml): Konfigurasi Postgres 16 dengan ekstensi PostGIS 3.4.
- [requirements.txt](requirements.txt) & [requirements-dev.txt](requirements-dev.txt): Mengatur dependensi runtime (FastAPI, SQLAlchemy, GeoAlchemy2, Pydantic, dsb) dan dev tools (pytest).
- [.env.example](.env.example) & [.env](.env): Konfigurasi flag mock `MOCK_EXTERNAL=true` dan API Key.
- [.gitignore](.gitignore): Mengabaikan file lingkungan dan cache Python.

### Core & Database Connection
- [core/config.py](core/config.py): Pembacaan konfigurasi terpusat menggunakan Pydantic Settings.
- [core/deps.py](core/deps.py): Dependency injection sesi database (`get_db`).
- [db/base.py](db/base.py): Base class deklaratif ORM.
- [db/session.py](db/session.py): Pengelolaan engine koneksi dan inisialisasi tabel otomatis + seeding koordinat kondisi laut awal.

### Data Models & Schemas (SQLAlchemy & Pydantic)
- Berkas model di `models/` (`nelayan`, `laporan`, `zona`, `trip_bbm`, `kondisi_laut`, `titik_favorit`, `sos`) mendefinisikan skema tabel spasial.
- Berkas skema di `schemas/` melakukan validasi parameter request dan memformat response JSON.

### Services Layer (Logika Bisnis & API Clients)
- [services/geo.py](services/geo.py): Rumus haversine, bearing navigasi, dan estimasi BBM.
- [services/moon.py](services/moon.py): Perhitungan fase bulan astronomis lokal offline.
- [services/scoring.py](services/scoring.py): Algoritma scoring zona tangkap rule-based v1.
- API Client terintegrasi dengan Google Earth Engine (`gee_client.py`), Open-Meteo (`marine_client.py`, `weather_client.py`), TideCheck (`tide_client.py`), faster-whisper STT (`stt.py`), DeepSeek API (`deepseek_client.py`), dan Expo SDK Push Notification (`sos_dispatch.py`). Semua memiliki dukungan mode tiruan (*mocking*) otomatis.

### Router Endpoints
- Mengaktifkan router `/nelayan`, `/zona-rekomendasi`, `/laporan` (teks & suara), `/trip-bbm`, `/kondisi-laut` (pencarian stasiun cuaca terdekat berdasarkan parameter `lat` & `lng`), `/titik-favorit`, `/sos`, dan `/sync/laporan-batch`.

### Background Scheduler & Main
- [jobs/refresh_zona_satelit.py](jobs/refresh_zona_satelit.py): Job terjadwal untuk memperbarui data GEE dan menghitung ulang skor zona.
- [jobs/refresh_kondisi_laut.py](jobs/refresh_kondisi_laut.py): Job terjadwal untuk memperbarui ramalan cuaca, gelombang, dan pasut.
- [main.py](main.py): Mengaitkan APScheduler pada lifespan event FastAPI.

### Dokumentasi API
- [api_documentation.md](api_documentation.md): Berisi spesifikasi API, format payload request/response, panduan penggunaan Python 3.13, setup database (Docker vs Supabase), dan cara pengujian.

---

## 2. Pengujian yang Dilakukan & Hasil Verifikasi

Seluruh pengujian otomatis tertulis di folder `tests/` menggunakan framework `pytest` dan `pytest-asyncio`.

### Jenis Pengujian
1. **Unit Test Geografis & Astronomis (`test_geo.py`, `test_moon.py`)**: Memastikan formula matematis dan mekanika astronomis berjalan akurat 100% secara offline.
2. **Unit Test Scoring (`test_scoring.py`)**: Memverifikasi ketepatan normalisasi rentang ideal, perhitungan bobot skor zona, serta pemberian bonus komunitas.
3. **Integration/API Test (`test_nelayan.py`, `test_laporan.py`, `test_zona.py`, `test_trip_bbm.py`, `test_kondisi_laut.py`, `test_titik_favorit.py`, `test_sos.py`)**: Menguji kelancaran response HTTP, kueri database PostGIS spasial (radius, jarak terdekat), dan integrasi mock client STT/DeepSeek.

### Cara Menjalankan Pengujian di Mesin Anda
1. Nyalakan Docker Desktop.
2. Jalankan database PostGIS:
   ```powershell
   docker compose up -d
   ```
3. Aktifkan virtual environment dan jalankan pytest:
   ```powershell
   .\venv\Scripts\activate
   pytest -v
   ```
   Seluruh pengujian dirancang untuk berjalan sukses (Passed) menggunakan mode tiruan database pengujian.

### Status Terakhir
Setelah perbaikan stabilitas test (lihat log perubahan di bawah) dan penambahan fitur grid zona dinamis + estimasi BBM, seluruh suite dinyatakan hijau:

```text
========== 24 passed, 1 warning in 61.20s ==========
```

---

## 3. Catatan Perubahan Terakhir (Stabilitas Test)

Empat tes yang sebelumnya tidak stabil telah diperbaiki:

1. **`test_kondisi_laut` (UniqueViolation)** — koordinat stasiun kustom test diubah ke titik yang tidak bentrok dengan 3 stasiun default yang di-seed oleh `conftest.py`.
2. **`test_laporan_suara` (estimasi 2.0 vs 25.0)** — parser angka kata Indonesia di `services/deepseek_client.py` kini mencocokkan frasa terpanjang lebih dulu (`"dua puluh lima"` sebelum `"dua"`).
3. **`test_laporan_batch` (perlu_review False vs True)** — default `perlu_review` pada `LaporanBatchItem` diubah menjadi `None` sehingga router menghitungnya otomatis dari kelengkapan data.
4. **`test_zona` (skor 0.7876 vs 0.72)** — fixture `client` di `tests/conftest.py` kini membersihkan ulang database setelah `TestClient` dibuat, sehingga data 9 titik grid yang dimasukkan job startup tidak bocor ke test.

Bug tersembunyi `UnboundLocalError: local variable 'math' referenced before assignment` di `services/weather_client.py` juga diperbaiki dengan memindahkan `import math` ke atas file.

---

## 4. Upgrade: Grid Zona Dinamis dari Posisi Nelayan

- **`services/zona_grid.py` (baru)** — membangun titik grid bertingkat dari posisi GPS nelayan ke arah laut (3, 7, 12, 17, 22 km sesuai `BEARING_LAUT_DEG`), dibatasi radius maksimum (`ZONA_RADIUS_MAKS_KM`) sehingga tidak memberi rekomendasi boros BBM.
- **`services/scoring.py`** — menambahkan `skor_efektif` (keseimbangan potensi tangkapan vs jarak/BBM) untuk pengurutan, `faktor_hemat_bbm`, dan penanda sedimen pasca-banjir (`terdampak_sedimen` + catatan).
- **`routers/zona.py`** — grid dihitung dinamis dari `lat/lng` yang dikirim app (GPS saat menyiapkan sampan), hasil di-cache ke `zona_satelit`/`zona_rekomendasi`, diurutkan menurun dari `skor_efektif`, dan diberi peringkat 1..N + `jarak_km`/`estimasi_bbm_liter`.
- **`jobs/refresh_zona_satelit.py`** — tidak lagi memakai `GRID_LAT/GRID_LNG` global; hanya menyegarkan ulang titik zona yang sudah tersimpan di cache (offline-first).

## 5. Upgrade: Docker Production

- **`Dockerfile`** — image multi-stage `python:3.13-slim`, user non-root, healthcheck `/health`, entry uvicorn 1 worker.
- **`.dockerignore`** — mengecualikan env/cache/docs/tests.
- **`docker-compose.prod.yml`** — service `db` (PostGIS 16, healthcheck, volume, tidak diekspos publik) + `api` (build, `depends_on: service_healthy`, env lengkap).
- **`.env.production.example`** — template env production (`MOCK_EXTERNAL=false`, password DB, API keys, `ZONA_*`, `RUN_SCHEDULER`).
- **`DEPLOYMENT.md`** — panduan deploy, backup/restore, rollback, deploy ke PaaS, keamanan.
- **`core/config.py` + `main.py`** — tambah variabel `ZONA_*` & `RUN_SCHEDULER`; guard scheduler agar tidak duplikat saat multi-replica.

Cara menjalankan production:
```bash
cp .env.production.example .env.production
docker compose -f docker-compose.prod.yml up -d --build
```
