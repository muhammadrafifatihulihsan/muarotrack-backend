# Implementation Plan

[Overview]

Membangun backend MuaroTrack (Python/FastAPI, PostgreSQL+PostGIS) versi gabungan v1+v2 sebagai fondasi data oseanografi, scoring zona tangkap rule-based, prediksi BBM, laporan tangkapan (teks & suara), cache kondisi laut, titik favorit, dan SOS untuk aplikasi mobile offline-first.

Proyek saat ini masih kosong: `docs/` berisi tiga spesifikasi (detail-umum.md = narasi proposal, spesifikasi-v1.md = brief teknis fondasi, spesifikasi-v2.md = perluasan halaman utama/backend). `server/` dan `app/` kosong, belum ada repo git. Rencana ini mencakup seluruh sisi server sesuai struktur clean architecture di spesifikasi-v2 Bagian 3.2, menggabungkan endpoint v1 (nelayan, laporan, zona, sync, trip-bbm) dan v2 (kondisi-laut, titik-favorit, sos, push-token) sekaligus karena saling melengkapi. Semua integrasi layanan eksternal (Google Earth Engine, DeepSeek, Open-Meteo, TideCheck, Expo Push) dibungkus di `services/*_client.py` dengan mode mock/fallback agar backend bisa dijalankan dan dites end-to-end secara lokal sebelum kredensial tersedia. Database dev memakai PostgreSQL+PostGIS via Docker (bukan SQLite) karena model menggunakan tipe spasial PostGIS, dan produksi (Supabase) juga PostgreSQL sehingga migrasi nanti cukup ganti `DATABASE_URL`.

[Types]

Mendefinisikan model data (SQLAlchemy ORM), schema request/response (Pydantic), dan tipe data time-series untuk seluruh domain backend v1+v2.

**Konvensi koordinat:** semua titik lokasi disimpan sebagai `GEOGRAPHY(Point, 4326)` via GeoAlchemy2, nilai longitude = x, latitude = y. Seluruh API menerima koordinat sebagai dua field `lat` (number) dan `lng` (number).

### Tabel database (PostgreSQL + PostGIS)

| Tabel               | Kolom wajib                                                                                                                                                                                                          | Kolom opsional                                                                                                            | Keterangan                                                                                           |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| `nelayan`           | `id UUID PK DEFAULT gen_random_uuid()`, `nama TEXT NOT NULL`, `konsumsi_bbm_per_km NUMERIC NOT NULL`, `created_at TIMESTAMPTZ DEFAULT now()`                                                                         | —                                                                                                                         | Profil kapal; `konsumsi_bbm_per_km` dihitung backend dari input onboarding                           |
| `muara`             | `id UUID PK`, `nama TEXT NOT NULL`, `lokasi GEOGRAPHY(Point,4326) NOT NULL`                                                                                                                                          | —                                                                                                                         | Seed 3 titik: Batang Kuranji, Koto Tangah, Ulak Karang                                               |
| `laporan_tangkapan` | `id UUID PK`, `nelayan_id FK→nelayan`, `lokasi GEOGRAPHY(Point,4326) NOT NULL`, `waktu TIMESTAMPTZ DEFAULT now()`, `synced BOOLEAN DEFAULT true`                                                                     | `jenis_ikan TEXT`, `estimasi_kg NUMERIC`, `catatan TEXT`, `perlu_review BOOLEAN DEFAULT false`                            | `perlu_review=true` jika parsing DeepSeek gagal                                                      |
| `zona_satelit`      | `id UUID PK`, `lokasi GEOGRAPHY(Point,4326) NOT NULL`, `diperbarui_pada TIMESTAMPTZ DEFAULT now()`                                                                                                                   | `sst NUMERIC`, `klorofil NUMERIC`, `turbiditas_ndti NUMERIC`                                                              | Nilai mentah dari GEE per titik grid                                                                 |
| `zona_rekomendasi`  | `id UUID PK`, `lokasi GEOGRAPHY(Point,4326) NOT NULL`, `skor NUMERIC NOT NULL`, `dihitung_pada TIMESTAMPTZ DEFAULT now()`                                                                                            | `detail_skor JSONB`                                                                                                       | `detail_skor` = breakdown per faktor (sst, klorofil, turbiditas, batimetri, fase_bulan, jarak_muara) |
| `trip_bbm`          | `id UUID PK`, `nelayan_id FK`, `jarak_km NUMERIC NOT NULL`, `prediksi_liter NUMERIC NOT NULL`, `waktu TIMESTAMPTZ DEFAULT now()`                                                                                     | `liter_aktual NUMERIC`                                                                                                    | Bahan validasi uji lapangan                                                                          |
| `kondisi_laut`      | `id UUID PK`, `muara_id FK→muara`, `lokasi GEOGRAPHY(Point,4326) NOT NULL`, `sumber_gelombang_cuaca TEXT DEFAULT 'open-meteo'`, `sumber_pasut TEXT DEFAULT 'tidecheck'`, `diperbarui_pada TIMESTAMPTZ DEFAULT now()` | `gelombang_gabungan JSONB`, `gelombang_angin JSONB`, `gelombang_swell JSONB`, `cuaca_per_jam JSONB`, `pasang_surut JSONB` | Satu baris per muara, di-refresh job terjadwal                                                       |
| `titik_favorit`     | `id UUID PK`, `nelayan_id FK`, `nama_label TEXT NOT NULL`, `lokasi GEOGRAPHY(Point,4326) NOT NULL`, `dibuat_pada TIMESTAMPTZ DEFAULT now()`, `synced BOOLEAN DEFAULT true`                                           | `catatan TEXT`, `laporan_tangkapan_id FK→laporan_tangkapan NULL`                                                          | Lokasi simpan manual nelayan                                                                         |
| `sos_signal`        | `id UUID PK`, `nelayan_id FK`, `lokasi GEOGRAPHY(Point,4326) NOT NULL`, `waktu_kejadian TIMESTAMPTZ NOT NULL`, `status TEXT DEFAULT 'tertunda'`, `dibuat_pada TIMESTAMPTZ DEFAULT now()`                             | `pesan TEXT`, `waktu_terkirim TIMESTAMPTZ NULL`                                                                           | `status` ∈ `tertunda\|terkirim\|dibatalkan\|selesai`                                                 |
| `push_token`        | `id UUID PK`, `nelayan_id FK`, `expo_push_token TEXT NOT NULL`, `diperbarui_pada TIMESTAMPTZ DEFAULT now()`                                                                                                          | —                                                                                                                         | Fan-out SOS; satu device satu baris (upsert per token)                                               |

### Tipe data time-series (JSONB)

Semua item memiliki field `waktu` (ISO-8601 string):

```jsonc
// gelombang_gabungan / gelombang_angin / gelombang_swell
[{ "waktu": "2026-08-08T07:00", "tinggi_m": 1.2, "arah_derajat": 210, "periode_detik": 7.5 }]

// cuaca_per_jam
[{ "waktu": "2026-08-08T07:00", "suhu_c": 27.3, "kelembapan_persen": 84, "tekanan_hpa": 1010.2,
   "uv_index": 3.1, "presipitasi_mm": 0.0, "probabilitas_presipitasi_persen": 10,
   "kecepatan_angin_kmh": 14.2, "arah_angin_derajat": 250, "hembusan_angin_kmh": 22.5 }]

// pasang_surut
[{ "waktu": "2026-08-08T05:12", "tinggi_m": 0.3, "tipe": "surut" }]  // tipe ∈ pasang|surut|sampel
```

### Skor zona (rule-based v1, semua dinormalisasi 0–1)

```
skor_zona = 0.20*skor_SST + 0.15*skor_klorofil + 0.25*skor_turbiditas
          + 0.15*skor_batimetri + 0.10*skor_fase_bulan + 0.15*skor_jarak_muara
          + bonus_komunitas   // +0.10 maks, aktif jika ≥3 laporan dalam 500 m
```

Normalisasi (dapat dikalibrasi, didokumentasikan sebagai placeholder):

- `skor_SST` = clamp((sst − 24) / 7, 0, 1) — rentang ideal tropis ~24–31 °C.
- `skor_klorofil` = clamp(log10(klorofil / 0.1) / 2, 0, 1) — 0.1–10 mg/m³.
- `skor_turbiditas` = 1 − clamp((ndti + 1) / 2, 0, 1) — NDTI lebih rendah = air jernih = lebih baik.
- `skor_batimetri` = dari lookup statis kedalaman per titik (lihat Files: `data/batimetri.json`); skor tertinggi pada kedalaman 10–40 m.
- `skor_fase_bulan` = fraksi iluminasi bulan (0–1) dari rumus astronomi lokal (tanpa API).
- `skor_jarak_muara` = clamp(distance_km / 5, 0, 1) — semakin jauh dari muara terdampak semakin baik, jenuh di ≥5 km.

### Formula prediksi BBM

```
haversine_km(lat1,lng1,lat2,lng2)   # radius bumi 6371 km
prediksi_liter = jarak_km * konsumsi_bbm_per_km * 2   # pulang-pergi
```

[Files]

Seluruh backend baru dibuat di bawah `server/`; tidak ada file yang dimodifikasi/dihapus karena folder masih kosong. Struktur mengikuti spesifikasi-v2 Bagian 3.2 (layered/clean architecture).

> **Catatan implementasi final:** Dokumen ini adalah rencana awal. Pada implementasi aktual, beberapa item berikut **tidak dibuat** karena desain disederhanakan: tabel/model/router `muara` (koordinat muara di-hardcode sebagai konstanta pada `services/scoring.py`), folder `alembic/` (pembuatan tabel memakai `Base.metadata.create_all`), dan folder `data/` (seed stasiun dilakukan langsung di `db/session.py` & `tests/conftest.py`). Endpoint `GET /kondisi-laut` juga memakai parameter `lat` & `lng` (bukan `muara_id`) — sesuai dokumentasi API aktual.
>
> **Upgrade berikutnya (sudah diterapkan):** grid zona rekomendasi kini **dinamis dari posisi GPS nelayan** (bukan grid global `GRID_LAT/GRID_LNG`); `services/zona_grid.py` membangun grid bertingkat ke arah laut sesuai `BEARING_LAUT_DEG` dan dibatasi `ZONA_RADIUS_MAKS_KM`. Response `/zona-rekomendasi` menambah `jarak_km`, `estimasi_bbm_liter`, `peringkat`, `skor_efektif`, dan penanda sedimen. Tersedia juga setup **Docker production**: `Dockerfile`, `docker-compose.prod.yml`, `.env.production.example`, dan `DEPLOYMENT.md`. Seluruh suite **24 test** lulus.

**File baru:**

```
server/
├── docker-compose.yml                # Postgres 16 + PostGIS 3, port 5432, db muarotrack
├── .env.example                      # Semua variabel env + komentar cara mengisinya
├── .gitignore                        # .env, __pycache__, .venv, dll
├── requirements.txt                  # Dependensi runtime (lihat Dependencies)
├── requirements-dev.txt              # pytest, httpx test client, dll
├── README.md                         # Setup lokal + panduan kredensial (langkah demi langkah)
├── alembic.ini                       # Konfigurasi migrasi
├── alembic/
│   ├── env.py                        # Kaitkan metadata Base, baca DATABASE_URL
│   ├── script.py.mako
│   └── versions/
│       └── 0001_initial.py           # Migrasi awal: semua tabel + indeks spasial
├── main.py                           # Entrypoint FastAPI: lifespan (init/seed + scheduler), daftar router, /health
├── core/
│   ├── __init__.py
│   ├── config.py                     # pydantic-settings; Settings dengan semua env (DATABASE_URL, GEE_PROJECT_ID, DEEPSEEK_API_KEY, TIDECHECK_API_KEY, WORLDTIDES_API_KEY, EXPO_ACCESS_TOKEN, WHISPER_MODEL_SIZE, SOS_RADIUS_KM, MOCK_EXTERNAL=true)
│   └── deps.py                       # get_db (session factory), get_settings
├── db/
│   ├── __init__.py
│   ├── base.py                       # DeclarativeBase + GeoAlchemy2 setup
│   └── session.py                    # engine, SessionLocal, get_session; helper init_db() create_all + seed
├── models/
│   ├── __init__.py                   # Import semua model (agar terdaftar di metadata)
│   ├── nelayan.py                    # class Nelayan
│   ├── muara.py                      # class Muara
│   ├── laporan.py                    # class LaporanTangkapan
│   ├── zona.py                       # class ZonaSatelit, class ZonaRekomendasi
│   ├── trip_bbm.py                   # class TripBbm
│   ├── kondisi_laut.py               # class KondisiLaut
│   ├── titik_favorit.py              # class TitikFavorit
│   └── sos.py                        # class SosSignal, class PushToken
├── schemas/
│   ├── __init__.py
│   ├── nelayan.py                    # NelayanCreate{name, total_liter_biasa, jarak_km_biasa}, NelayanOut
│   ├── muara.py                      # MuaraOut{id, nama, lat, lng}
│   ├── laporan.py                    # LaporanTeksCreate, LaporanSuaraOut, LaporanOut, LaporanBatchRequest, LaporanBatchItem
│   ├── zona.py                       # ZonaRekomendasiOut{id, lat, lng, skor, detail_skor, dihitung_pada}, ZonaRekomendasiListResponse{zonas}
│   ├── trip_bbm.py                   # TripBbmCreate, TripBbmOut
│   ├── kondisi_laut.py               # KondisiLautOut{muara_id, diperbarui_pada, gelombang_*, cuaca_per_jam, pasang_surut}
│   ├── titik_favorit.py              # TitikFavoritCreate{nelayan_id, nama_label, lat, lng, catatan?, laporan_tangkapan_id?}, TitikFavoritOut
│   └── sos.py                        # SosCreate{nelayan_id, lat, lng, pesan?, waktu_kejadian}, SosOut, PushTokenCreate{nelayan_id, expo_push_token}
├── routers/
│   ├── __init__.py
│   ├── nelayan.py                    # POST /nelayan → hitung konsumsi_bbm_per_km = total_liter/jarak_km
│   ├── muara.py                      # GET /muara → daftar 3 muara (dipakai app utk sinkronisasi awal)
│   ├── laporan.py                    # POST /laporan/teks, POST /laporan/suara, POST /sync/laporan-batch
│   ├── zona.py                       # GET /zona-rekomendasi?lat=&lng=&radius_km=
│   ├── trip_bbm.py                   # POST /trip-bbm
│   ├── kondisi_laut.py               # GET /kondisi-laut?muara_id=
│   ├── titik_favorit.py              # POST /titik-favorit, GET /titik-favorit?nelayan_id=
│   ├── sos.py                        # POST /sos, GET /sos/aktif?radius_km=&lat=&lng=, POST /push-token
│   └── sync.py                       # /sync/laporan-batch delegasi ke router laporan (alias konsisten dgn kontrak API)
├── services/
│   ├── __init__.py
│   ├── geo.py                        # haversine_km(), bearing(), prediksi_bbm(), total_jarak_jalur()
│   ├── moon.py                       # skor_fase_bulan(date)→0..1, fraksi_iluminasi() (rumus astronomi murni, tanpa API)
│   ├── scoring.py                    # hitung_skor_zona(raw: dict) → (skor, detail_skor); fungsi murni, tanpa ML
│   ├── gee_client.py                 # class GeeClient: fetch_satellite(lat,lng) → {sst, klorofil, turbiditas_ndti}; MOCK fallback bila env kosong/import gagal
│   ├── marine_client.py              # class MarineClient: fetch_gelombang(lat,lng) → gelombang_* time series via Open-Meteo Marine
│   ├── weather_client.py             # class WeatherClient: fetch_cuaca(lat,lng) → cuaca_per_jam via Open-Meteo Forecast
│   ├── tide_client.py                # class TideClient: fetch_pasut(lat,lng) → pasang_surut via TideCheck; fallback WorldTides
│   ├── stt.py                        # class SttService: transkrip(audio_bytes) → teks via faster-whisper; MOCK fallback
│   ├── deepseek_client.py            # class DeepSeekClient: parse_laporan(teks) → {jenis_ikan, estimasi_kg} JSON terstruktur; MOCK fallback + validasi
│   └── sos_dispatch.py               # class SosDispatch: notify_nearby(sos, session) → query ST_DWithin push_token, kirim via expo-server-sdk
├── jobs/
│   ├── __init__.py
│   ├── refresh_zona_satelit.py       # async run(): grid titik sekitar 3 muara → GEE → upsert zona_satelit → recompute zona_rekomendasi via scoring
│   └── refresh_kondisi_laut.py       # async run(): utk tiap muara → marine+weather+tide → upsert kondisi_laut
├── data/
│   ├── muara_seed.json               # [{nama, lat, lng}] 3 titik studi kasus (koordinat perkiraan, perlu verifikasi lapangan)
│   └── batimetri.json                # Grid kedalaman statis placeholder per titik muara (BATNAS penuh = pengembangan lanjutan)
└── tests/
    ├── __init__.py
    ├── conftest.py                   # Fixture: test DB (postgres+postgis lokal), TestClient, override get_db
    ├── test_scoring.py               # Unit: normalisasi tiap faktor, bobot, bonus komunitas, edge case clamp
    ├── test_geo.py                   # Unit: haversine (jarak dikenal), bearing, prediksi_bbm pulang-pergi
    ├── test_moon.py                  # Unit: fase bulan dalam rentang 0..1, siklus bulan baru/purnama
    ├── test_nelayan.py               # API: POST /nelayan menghitung konsumsi_bbm_per_km
    ├── test_laporan.py               # API: teks, suara (mock STT+DeepSeek), batch sync
    ├── test_zona.py                  # API: GET /zona-rekomendasi (isi data dummy zona_satelit)
    ├── test_trip_bbm.py              # API: POST /trip-bbm
    ├── test_kondisi_laut.py          # API: GET /kondisi-laut (mock client eksternal)
    ├── test_titik_favorit.py         # API: CRUD titik favorit
    └── test_sos.py                   # API: POST /sos (mock dispatch), GET /sos/aktif
```

**File yang dimodifikasi:** tidak ada (proyek baru).
**File yang dihapus/dipindah:** tidak ada.
**Update konfigurasi:** `.env` dibuat dari `.env.example` oleh developer saat setup lokal (tidak di-commit).

[Functions]

Menambahkan fungsi-fungsi inti (pure function & service method) untuk logika bisnis, scoring, klien eksternal, dan job terjadwal.

**New functions (services/geo.py):**

- `haversine_km(lat1, lng1, lat2, lng2) -> float` — great-circle distance, radius 6371 km.
- `bearing(lat1, lng1, lat2, lng2) -> float` — initial bearing 0–360° (fallback: `atan2` formula dari spec 7.2).
- `prediksi_bbm(jarak_km, konsumsi_per_km) -> float` — `jarak * konsumsi * 2`.
- `total_jarak_jalur(titik: list[dict]) -> float` — jumlah haversine per segmen.

**New functions (services/moon.py):**

- `skor_fase_bulan(tanggal: date) -> float` — fraksi iluminasi (0–1) dijadikan skor; rumus astronomi murni (tanpa API, tanpa dependensi), berjalan offline.

**New functions (services/scoring.py):**

- `normalisasi_sst(sst) -> float`, `normalisasi_klorofil(klorofil) -> float`, `normalisasi_turbiditas(ndti) -> float`, `normalisasi_batimetri(depth_m) -> float`, `normalisasi_fase_bulan(illum) -> float`, `normalisasi_jarak_muara(distance_km) -> float` — masing-masing clamp ke 0–1.
- `hitung_skor_zona(sst, klorofil, turbiditas_ndti, kedalaman_m, fase_bulan_illum, jarak_muara_km, laporan_dalam_500m: int = 0) -> tuple[float, dict]` — pure function, tidak menyentuh DB/HTTP, menerapkan bobot 0.20/0.15/0.25/0.15/0.10/0.15 dan bonus komunitas (+0.10 maks bila `laporan_dalam_500m >= 3`). Kembalikan `(skor, detail_skor)`.

**New service methods (services/\*\_client.py):**

- `GeeClient.fetch_satellite(lat, lng) -> dict` — SST, klorofil, turbiditas (NDTI) via GEE Python API (`ee`); bila `MOCK_EXTERNAL=true` atau import gagal, kembalikan data dummy bertanda `{"source": "mock"}`.
- `MarineClient.fetch_gelombang(lat, lng) -> dict` — Open-Meteo Marine hourly `wave_*`, `wind_wave_*`, `swell_wave_*` (timezone `Asia/Jakarta`, `forecast_days=7`); response dinormalisasi ke format time-series JSON.
- `WeatherClient.fetch_cuaca(lat, lng) -> list[dict]` — Open-Meteo Forecast hourly (9 parameter sesuai spec 7.6).
- `TideClient.fetch_pasut(lat, lng) -> list[dict]` — TideCheck; fallback WorldTides bila TideCheck tidak menjangkau titik.
- `SttService.transkrip(audio_bytes) -> str` — faster-whisper model `small`; mock fallback mengembalikan teks contoh.
- `DeepSeekClient.parse_laporan(teks) -> dict` — call DeepSeek `deepseek-v4-flash` (OpenAI-compatible endpoint) meminta JSON `{jenis_ikan, estimasi_kg, catatan}`; **tidak** untuk prediksi lokasi ikan; fallback menyimpan teks mentah + `perlu_review=true`.
- `SosDispatch.notify_nearby(sos, db) -> int` — query `push_token` dalam `SOS_RADIUS_KM` (default 10, env) via `ST_DWithin`, kirim push via `expo-server-sdk`; no-op saat `EXPO_ACCESS_TOKEN` kosong.

**New functions (jobs/):**

- `refresh_zona_satelit.run() -> dict` — bangun grid ±radius nearshore (mis. 1–12 mil laut) di sekitar tiap muara, panggil GEE per titik, upsert `zona_satelit`, lalu jalankan scoring → upsert `zona_rekomendasi`. Idempotent.
- `refresh_kondisi_laut.run() -> dict` — untuk tiap muara: panggil MarineClient + WeatherClient + TideClient, upsert satu baris `kondisi_laut` (3 jam untuk gelombang/cuaca, 1×/hari untuk pasut — guard dengan `diperbarui_pada`).

**New router handlers (routers/\*.py):** handler tipis per kontrak API di bawah:

| Method | Endpoint                                 | Handler                | Catatan                                                                         |
| ------ | ---------------------------------------- | ---------------------- | ------------------------------------------------------------------------------- |
| POST   | `/nelayan`                               | `daftar_nelayan`       | Body `{nama, total_liter_biasa, jarak_km_biasa}` → simpan `konsumsi_bbm_per_km` |
| GET    | `/muara`                                 | `list_muara`           | Daftar 3 muara untuk sinkronisasi awal app                                      |
| GET    | `/zona-rekomendasi?lat=&lng=&radius_km=` | `zona_rekomendasi`     | Query `ST_DWithin` dari posisi; default `radius_km=22` (≈12 mil laut)           |
| POST   | `/laporan/teks`                          | `laporan_teks`         | Simpan laporan terstruktur                                                      |
| POST   | `/laporan/suara`                         | `laporan_suara`        | Multipart audio → STT → DeepSeek → simpan; fallback `perlu_review=true`         |
| POST   | `/sync/laporan-batch`                    | `laporan_batch`        | Terima array laporan offline, simpan semua                                      |
| POST   | `/trip-bbm`                              | `trip_bbm`             | Simpan prediksi vs realisasi                                                    |
| GET    | `/kondisi-laut?muara_id=`                | `kondisi_laut`         | Hanya baca cache, **tidak** panggil API eksternal live                          |
| POST   | `/titik-favorit`                         | `titik_favorit_create` | Simpan lokasi favorit                                                           |
| GET    | `/titik-favorit?nelayan_id=`             | `titik_favorit_list`   | Semua titik favorit satu nelayan                                                |
| POST   | `/sos`                                   | `sos_create`           | Simpan sinyal + panggil `SosDispatch.notify_nearby`                             |
| GET    | `/sos/aktif?radius_km=&lat=&lng=`        | `sos_aktif`            | Sinyal `tertunda`/`terkirim` dalam radius                                       |
| POST   | `/push-token`                            | `push_token_upsert`    | Daftar/perbarui Expo push token                                                 |

**New functions (core/config.py):** `class Settings` (pydantic-settings) + `get_settings()`. **core/deps.py:** `get_db()` generator. **db/session.py:** `init_db()` create_all + seed muara dari `data/muara_seed.json`.

[Classes]

Menambahkan kelas ORM (SQLAlchemy) dan kelas service untuk seluruh domain backend.

**New classes (models/) — SQLAlchemy 2.0 declarative, Base dari `db/base.py`:**

- `Nelayan` — kolom sesuai tabel `nelayan`.
- `Muara` — kolom sesuai tabel `muara`; `lokasi` bertipe `Geography(geometry_type="POINT", srid=4326)`.
- `LaporanTangkapan` — kolom sesuai tabel `laporan_tangkapan`; relasi `nelayan_id`.
- `ZonaSatelit`, `ZonaRekomendasi` — kolom sesuai tabel; `detail_skor` bertipe `JSONB`.
- `TripBbm` — kolom sesuai tabel `trip_bbm`.
- `KondisiLaut` — kolom JSONB time-series sesuai spec.
- `TitikFavorit` — kolom sesuai tabel; relasi `nelayan_id` dan opsional `laporan_tangkapan_id`.
- `SosSignal` — kolom sesuai tabel; konstanta status `TERTUNDA/TERKIRIM/DIBATALKAN/SELESAI`.
- `PushToken` — kolom sesuai tabel; unique constraint pada `expo_push_token`.

Semua kelas menggunakan UUID primary key (server-generated `gen_random_uuid()`), `__tablename__` plural (bentuk jamak, contoh `laporan_tangkapan`).

**New classes (schemas/) — Pydantic v2:**

- `NelayanCreate`, `NelayanOut` — `NelayanCreate` memvalidasi `jarak_km_biasa > 0` (hindari ZeroDivision).
- `LaporanTeksCreate`, `LaporanBatchItem`, `LaporanBatchRequest` (list), `LaporanOut`, `LaporanSuaraOut` (`perlu_review`).
- `ZonaRekomendasiOut`, `ZonaRekomendasiListResponse` — format persis contoh kontrak API.
- `KondisiLautOut` — format persis contoh spec v2 Bagian 6.
- `TitikFavoritCreate`, `TitikFavoritOut`.
- `SosCreate`, `SosOut`, `PushTokenCreate`.

**New classes (services/):** `GeeClient`, `MarineClient`, `WeatherClient`, `TideClient`, `SttService`, `DeepSeekClient`, `SosDispatch` — detail method di bagian [Functions]. Semua mengikuti aturan: **router tidak pernah memanggil HTTP eksternal langsung**, hanya lewat kelas service.

[Dependencies]

Menambahkan dependensi Python (requirements.txt) dan layanan infrakstruktur (Docker PostGIS) untuk backend.

- `fastapi`, `uvicorn[standard]` — framework web & ASGI server.
- `sqlalchemy>=2.0`, `geoalchemy2` — ORM + tipe spasial.
- `psycopg2-binary` — driver PostgreSQL.
- `pydantic>=2`, `pydantic-settings` — validasi & konfigurasi env.
- `httpx` — panggilan API eksternal (Open-Meteo, TideCheck, DeepSeek).
- `python-multipart` — upload file audio (`/laporan/suara`).
- `alembic` — migrasi skema (opsional pengganti create_all; dipakai untuk migrasi produksi).
- `apscheduler` — job terjadwal (refresh zona satelit & kondisi laut).
- `expo-server-sdk` — push notification SOS.
- `earthengine-api` — GEE (optional; di-import secara lazy, backend tetap jalan tanpa install).
- `faster-whisper` — STT self-host (optional; lazy import, mock fallback).
- `openai` — klien DeepSeek (API OpenAI-compatible, base_url `https://api.deepseek.com`) **atau** cukup `httpx` (pilih httpx untuk mengurangi dependensi; openai di listing sebagai opsi).
- `pytest`, `pytest-asyncio`, `httpx` (test client FastAPI) — di `requirements-dev.txt`.

**Layanan eksternal (dibutuhkan saat kredensial tersedia):**

- PostgreSQL 16 + PostGIS 3 via `docker-compose.yml` (`postgis/postgis:16-3.4`).
- Supabase untuk produksi — **tanpa perubahan kode**, cukup ubah `DATABASE_URL`.

**Panduan kredensial (lengkap di `server/README.md`):**

1. **Google Earth Engine** → daftar di `https://earthengine.google.com/signup`; buat Cloud Project di Google Cloud Console → aktifkan "Earth Engine API"; buat Service Account (IAM → Service Accounts) + download JSON key; set `GEE_PROJECT_ID=<cloud project id>`; untuk lokal bisa `earthengine authenticate` atau set `GOOGLE_APPLICATION_CREDENTIALS=<path ke JSON>`.
2. **DeepSeek** → daftar `https://platform.deepseek.com` → buat API key `sk-...` → set `DEEPSEEK_API_KEY`.
3. **TideCheck** → daftar `https://tidecheck.com/developers` → dapat API key → set `TIDECHECK_API_KEY`.
4. **WorldTides** (cadangan) → `https://www.worldtides.info` → set `WORLDTIDES_API_KEY` (opsional).
5. **Expo Access Token** → buat project di `https://expo.dev` → Settings → Access tokens → set `EXPO_ACCESS_TOKEN`.
6. **Supabase** (produksi) → buat project → SQL Editor jalankan `CREATE EXTENSION postgis;` → copy connection string → set `DATABASE_URL`.
7. **Open-Meteo** → gratis tanpa key, tidak perlu env.
8. `WHISPER_MODEL_SIZE=small`, `SOS_RADIUS_KM=10`, `MOCK_EXTERNAL=true` (untuk development sebelum kredensial tersedia).

[Testing]

Menambahkan test suite pytest untuk unit (pure function) dan API integration dengan PostGIS lokal dan mock layanan eksternal.

- `tests/conftest.py`: fixture membuat database test terpisah di instance PostGIS Docker (mis. `muarotrack_test`), apply schema via `Base.metadata.create_all`, seed muara, override `get_db`, dan `TestClient` dari FastAPI.
- **Unit tests:** `test_scoring.py` (normalisasi tiap faktor, bobot total = 1.0, bonus komunitas aktif saat ≥3 laporan, clamp pada nilai ekstrem), `test_geo.py` (haversine antar titik dengan jarak diketahui, prediksi BBM pulang-pergi), `test_moon.py` (iluminasi 0–1, bulan baru ~0, purnama ~1).
- **API tests:** `test_nelayan.py`, `test_laporan.py` (mock SttService/DeepSeekClient), `test_zona.py` (seeding `zona_satelit` dummy → cek response format kontrak), `test_trip_bbm.py`, `test_kondisi_laut.py` (mock MarineClient/WeatherClient/TideClient), `test_titik_favorit.py`, `test_sos.py` (mock `SosDispatch`).
- **Validasi:** semua test dijalankan dengan `MOCK_EXTERNAL=true` sehingga tidak butuh kredensial; kredensial asli diuji manual lewat README checklist.
- Perintah: `cd server && docker compose up -d && pytest -q`.

[Implementation Order]

Membangun backend secara bertahap: fondasi infra → model/schema → logika murni → endpoint v1 → klien eksternal + endpoint v2 → job terjadwal → test → dokumentasi.

1. **Scaffold & infra lokal:** buat `server/` (struktur folder, `requirements.txt`, `.env.example`, `.gitignore`, `docker-compose.yml` PostGIS); inisialisasi git repo di root proyek; jalankan `docker compose up -d`.
2. **Config & koneksi DB:** `core/config.py` (Settings), `db/base.py`, `db/session.py`, `init_db()`; pastikan koneksi ke PostGIS Docker berhasil.
3. **Model & schema:** semua kelas ORM di `models/` + kelas Pydantic di `schemas/`; setup Alembic dan buat migrasi `0001_initial` (create_all untuk dev, migrasi untuk produksi).
4. **Seed data:** `data/muara_seed.json` (3 muara, koordinat perkiraan) + `data/batimetri.json`; `init_db()` menyemaikan muara.
5. **Pure functions:** `services/geo.py`, `services/moon.py`, `services/scoring.py` + unit test dasar (`test_scoring.py`, `test_geo.py`, `test_moon.py`).
6. **Router v1:** `routers/nelayan.py`, `routers/muara.py`, `routers/trip_bbm.py`, `routers/zona.py` (scoring dengan data zona_satelit yang di-seed/dummy), `routers/laporan.py` (teks + batch sync).
7. **Klien eksternal dengan mock:** `gee_client.py`, `marine_client.py`, `weather_client.py`, `tide_client.py`, `deepseek_client.py`, `stt.py` — semua dilindungi flag `MOCK_EXTERNAL`; lengkapi `/laporan/suara`.
8. **Router v2:** `routers/kondisi_laut.py`, `routers/titik_favorit.py`, `routers/sos.py` (+ `push-token`, `sos_dispatch.py`).
9. **Job terjadwal:** `jobs/refresh_zona_satelit.py`, `jobs/refresh_kondisi_laut.py`; wire ke `main.py` via lifespan (APScheduler, interval 3 jam untuk kondisi laut; guard pasut 1×/hari).
10. **Test lengkap:** selesaikan `tests/` (konteks, semua test API), jalankan `pytest -q` sampai hijau.
11. **Dokumentasi:** `server/README.md` berisi setup Docker, panduan kredensial langkah demi langkah (Bagian Dependencies), dan cara menonaktifkan mock (`MOCK_EXTERNAL=false`).


TASK DONE
# Daftar Tugas Implementasi Backend MuaroTrack

- `[x]` 1. Scaffold Projek Konfigurasi
  - `[x]` Buat `server/docker-compose.yml` (PostgreSQL + PostGIS)
  - `[x]` Buat `server/requirements.txt`
  - `[x]` Buat `server/.env.example` dan `.env`
  - `[x]` Buat `server/.gitignore`
  - `[x]` Buat `server/README.md`
- `[x]` 2. Setup Core & Database Connection
  - `[x]` Buat `server/core/config.py` (Pydantic Settings)
  - `[x]` Buat `server/core/deps.py` (Dependency injection `get_db`)
  - `[x]` Buat `server/db/base.py` (DeclarativeBase)
  - `[x]` Buat `server/db/session.py` (Engine, SessionLocal, `init_db`)
- `[x]` 3. Database Models (SQLAlchemy ORM)
  - `[x]` Buat model `Nelayan`, `LaporanTangkapan`, `ZonaSatelit`, `ZonaRekomendasi`, `TripBbm`, `KondisiLaut`, `TitikFavorit`, `SosSignal`, `PushToken`
  - `[x]` Buat file `server/models/__init__.py` untuk mendaftarkan semua model
- `[x]` 4. Pydantic Schemas
  - `[x]` Buat berkas-berkas skema di `server/schemas/` untuk validasi request/response
- `[x]` 5. Services Layer (Pure Functions & API Clients)
  - `[x]` Buat `server/services/geo.py` (Haversine, bearing, BBM)
  - `[x]` Buat `server/services/moon.py` (Fase & iluminasi bulan)
  - `[x]` Buat `server/services/scoring.py` (Scoring zona tangkap)
  - `[x]` Buat integrasi API client (`gee_client.py`, `marine_client.py`, `weather_client.py`, `tide_client.py`, `stt.py`, `deepseek_client.py`, `sos_dispatch.py`) dengan mock fallback
- `[x]` 6. Router API (FastAPI Endpoints)
  - `[x]` Buat router endpoints (`nelayan.py`, `zona.py`, `laporan.py`, `trip_bbm.py`, `kondisi_laut.py`, `titik_favorit.py`, `sos.py`, `sync.py`)
- `[x]` 7. Background Jobs & Main Entrypoint
  - `[x]` Buat background jobs scheduler (`jobs/refresh_zona_satelit.py`, `jobs/refresh_kondisi_laut.py`)
  - `[x]` Buat `server/main.py` terintegrasi dengan background jobs
- `[x]` 8. Automated Tests (pytest)
  - `[x]` Buat test fixtures di `server/tests/conftest.py`
  - `[x]` Jalankan dan verifikasi semua pengujian otomatis (`pytest -v`) — **24 passed**

> **Catatan:** Rangkuman *walkthrough* lengkap struktur kode dan hasil pengujian kini tersedia di berkas terpisah: [walkthrough.md](walkthrough.md).
