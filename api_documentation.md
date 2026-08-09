# Dokumentasi Lengkap API Server & Pengujian MuaroTrack

Dokumentasi ini merinci seluruh endpoint API, arsitektur backend, konfigurasi variabel lingkungan, kecocokan dengan **Python 3.13**, dan cara menjalankan pengujian otomatis (_unit_ & _integration test_).

---

## 1. Prasyarat & Lingkungan Python 3.13

Backend server MuaroTrack dikembangkan dengan dukungan penuh untuk **Python 3.13**. Seluruh dependensi utama seperti `fastapi`, `pydantic v2`, dan `sqlalchemy 2.0` telah diperbarui agar kompatibel dengan interpreter Python 3.13.

### Setup Virtual Environment (`venv`)

Gunakan terminal Windows untuk mengaktifkan `venv` yang sudah Anda buat di direktori `server/` dan pasang dependensi:

```powershell
# Masuk ke direktori server
cd server

# Aktifkan virtual environment
.\venv\Scripts\activate

# Perbarui pip
python -m pip install --upgrade pip

# Pasang seluruh dependensi (termasuk library pengujian)
pip install -r requirements-dev.txt

# Jalankan server API
uvicorn main:app --reload --host [IP_ADDRESS] --port 8000
# atau
uvicorn main:app --reload
# atau dengan 
python -m uvicorn main:app --reload --host [IP_ADDRESS] --port 8000
python -m uvicorn main:app --reload

# Jalankan pengujian
pytest -v

# Hentikan server
# Tekan Ctrl + C di terminal tempat server berjalan

# Cek status API dan tunggu sampai "status":"ok"
curl http://localhost:8000/health

# Swagger UI (Dokumentasi interaktif)
http://localhost:8000/docs
```

---

## 2. Arsitektur API & Endpoints

Server API ini diakses secara bawaan melalui: `http://localhost:8000`  
Dokumentasi interaktif bawaan (Swagger UI) dapat dibuka di: [http://localhost:8000/docs](http://localhost:8000/docs)

### Ringkasan Endpoint

| No  | Kategori             | Method | Endpoint              | Deskripsi                                                        |
| :-- | :------------------- | :----- | :-------------------- | :--------------------------------------------------------------- |
| 1   | Nelayan              | `POST` | `/nelayan`            | Pendaftaran nelayan + perhitungan konsumsi BBM awal              |
| 2   | Zona Rekomendasi     | `GET`  | `/zona-rekomendasi`   | Mengambil titik rekomendasi zona tangkap terdekat                |
| 3   | Laporan Tangkapan    | `POST` | `/laporan/teks`       | Input laporan tangkapan secara manual (teks/form)                |
| 4   | Laporan Tangkapan    | `POST` | `/laporan/suara`      | Upload file suara -> STT (Whisper) -> parsing (DeepSeek)         |
| 5   | Laporan Tangkapan    | `POST` | `/sync/laporan-batch` | Sinkronisasi batch laporan offline dari SQLite lokal             |
| 6   | Trip BBM             | `POST` | `/trip-bbm`           | Pencatatan prediksi vs aktual penggunaan BBM                     |
| 7   | Kondisi Laut         | `GET`  | `/kondisi-laut`       | Mengambil cache ramalan gelombang, cuaca, & pasut                |
| 8   | Titik Favorit        | `POST` | `/titik-favorit`      | Menyimpan koordinat favorit kustom nelayan                       |
| 9   | Titik Favorit        | `GET`  | `/titik-favorit`      | Mengambil seluruh lokasi favorit milik nelayan tertentu          |
| 10  | Sinyal Darurat (SOS) | `POST` | `/sos`                | Registrasi SOS baru & push notification spasial                  |
| 11  | Sinyal Darurat (SOS) | `GET`  | `/sos/aktif`          | Mengambil SOS aktif dalam radius tertentu untuk digambar di peta |
| 12  | Sinyal Darurat (SOS) | `POST` | `/push-token`         | Pendaftaran Expo Push Token per perangkat                        |

---

## 2.1 Mencoba Semua Endpoint dengan `curl` (Mandiri)

> Prasyarat: server sudah berjalan (`uvicorn main:app --reload`), database aktif (`docker compose up -d`).
> Base URL dev: `http://localhost:8000` · Android emulator: `http://10.0.2.2:8000`

**1) Registrasi Nelayan**
```bash
curl -X POST http://localhost:8000/nelayan \
  -H "Content-Type: application/json" \
  -d '{"nama":"Pak Anto","total_liter_biasa":10.0,"jarak_km_biasa":20.0}'
```
→ Response 201, `konsumsi_bbm_per_km` dihitung otomatis (`0.5`). Catat `id` yang dihasilkan untuk dipakai di contoh lain.

**2) Zona Rekomendasi (grid dinamis dari posisi nelayan + estimasi BBM)**
```bash
curl "http://localhost:8000/zona-rekomendasi?lat=-0.9000&lng=100.3600&radius_km=22&konsumsi_bbm_per_km=0.5"
```
→ Response 200: array `zonas` berisi `peringkat`, `jarak_km`, `estimasi_bbm_liter`, `skor_efektif`, `terdampak_sedimen`.

**3) Laporan Tangkapan (teks)**
```bash
curl -X POST http://localhost:8000/laporan/teks \
  -H "Content-Type: application/json" \
  -d '{"nelayan_id":null,"lat":-0.8972,"lng":100.3508,"jenis_ikan":"Tongkol","estimasi_kg":15.5,"catatan":"Melaut lancar"}'
```

**4) Laporan Tangkapan (suara — upload file)**
```bash
curl -X POST http://localhost:8000/laporan/suara \
  -F "file=@laporan.wav" \
  -F "lat=-0.8988" \
  -F "lng=100.3444"
```

**5) Sinkronisasi Batch Laporan (offline)**
```bash
curl -X POST http://localhost:8000/sync/laporan-batch \
  -H "Content-Type: application/json" \
  -d '{"laporan":[{"id":"a98a313b-1b1a-4c2c-8d1e-88ee12ff34c1","nelayan_id":null,"lat":-0.8256,"lng":100.3167,"jenis_ikan":"Tuna","estimasi_kg":50.0,"catatan":"Offline 1","waktu":"2026-08-08T00:00:00Z"}]}'
```

**6) Trip BBM (prediksi vs aktual)**
```bash
curl -X POST http://localhost:8000/trip-bbm \
  -H "Content-Type: application/json" \
  -d '{"nelayan_id":"<UUID_NELAYAN>","jarak_km":20.0,"prediksi_liter":10.0,"liter_aktual":9.5}'
```

**7) Kondisi Laut (cuaca/gelombang/pasut ter-cache)**
```bash
curl "http://localhost:8000/kondisi-laut?lat=-0.8972&lng=100.3508"
```

**8) Titik Favorit — simpan**
```bash
curl -X POST http://localhost:8000/titik-favorit \
  -H "Content-Type: application/json" \
  -d '{"nelayan_id":"<UUID_NELAYAN>","nama_label":"Titik dapat banyak","lat":-0.8972,"lng":100.3508}'
```

**9) Titik Favorit — ambil daftar**
```bash
curl "http://localhost:8000/titik-favorit?nelayan_id=<UUID_NELAYAN>"
```

**10) SOS — kirim sinyal**
```bash
curl -X POST http://localhost:8000/sos \
  -H "Content-Type: application/json" \
  -d '{"nelayan_id":"<UUID_NELAYAN>","lat":-0.8972,"lng":100.3508,"pesan":"Mesin mati","waktu_kejadian":"2026-08-08T01:00:00Z"}'
```

**11) SOS — daftar aktif di sekitar**
```bash
curl "http://localhost:8000/sos/aktif?lat=-0.8972&lng=100.3508&radius_km=10"
```

**12) Push Token (untuk notifikasi SOS)**
```bash
curl -X POST http://localhost:8000/push-token \
  -H "Content-Type: application/json" \
  -d '{"nelayan_id":"<UUID_NELAYAN>","expo_push_token":"ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]"}'
```

**Health check**
```bash
curl http://localhost:8000/health
# {"status":"ok","message":"MuaroTrack API Server is running"}
```

---

## 3. Detail Payload & Response API

### 3.1 Nelayan

- **`POST /nelayan`** (Registrasi Nelayan)
  - **Request Body (`application/json`)**:
    ```json
    {
    	"nama": "Pak Anto",
    	"total_liter_biasa": 10.0,
    	"jarak_km_biasa": 20.0
    }
    ```
  - **Response (`201 Created`)**:
    ```json
    {
    	"id": "27685e13-1a22-48df-b593-c918ee0882e3",
    	"nama": "Pak Anto",
    	"konsumsi_bbm_per_km": 0.5,
    	"created_at": "2026-08-08T10:00:00.000Z"
    }
    ```

### 3.2 Zona Rekomendasi Spasial (Grid Dinamis dari Posisi Nelayan)

Rekomendasi zona **dibangun secara dinamis** dari posisi GPS nelayan (titik mereka
menyiapkan sampan di pantai), bukan dari koordinat yang dikunci ke 3 muara. Grid
dibangkitkan bertingkat ke arah laut dengan jarak dekat → jauh (default 3, 7, 12, 17, 22 km)
sesuai `BEARING_LAUT_DEG`, dibatasi radius maksimum (`radius_km`, default 22 km) agar tidak
memberi rekomendasi yang boros BBM, lalu diurutkan berdasarkan **skor efektif**
(keseimbangan potensi tangkapan vs jarak/BBM) dan diberi peringkat 1..N.

- **`GET /zona-rekomendasi?lat=-0.8972&lng=100.3508&radius_km=22&konsumsi_bbm_per_km=0.5`**
  - `konsumsi_bbm_per_km` (opsional): konsumsi BBM liter/km — dipakai menghitung `estimasi_bbm_liter = jarak_km × konsumsi × 2` (pulang-pergi). Tanpa parameter ini, `estimasi_bbm_liter` bernilai `null`.
  - **Response (`200 OK`)**:
    ```json
    {
    	"zonas": [
    		{
    			"id": "e98e29a9-34ba-49c0-82aa-c990ee1219b1",
    			"lat": -0.8972,
    			"lng": 100.3508,
    			"skor": 0.85,
    			"detail_skor": {
    				"sst": 0.8,
    				"klorofil": 0.9,
    				"turbiditas": 0.9,
    				"batimetri": 1.0,
    				"fase_bulan": 0.5,
    				"jarak_muara": 0.9,
    				"bonus_komunitas": 0.1,
    				"faktor_hemat_bbm": 0.76
    			},
    			"dihitung_pada": "2026-08-08T06:00:00Z",
    			"jarak_km": 6.0,
    			"estimasi_bbm_liter": 6.0,
    			"peringkat": 1,
    			"skor_efektif": 0.748,
    			"terdampak_sedimen": false,
    			"catatan_sedimen": null
    		}
    	]
    }
    ```

  - **Penjelasan field baru**:
    - `jarak_km` — jarak dari posisi nelayan ke titik zona.
    - `estimasi_bbm_liter` — prediksi BBM pulang-pergi (`jarak × konsumsi × 2`); `null` bila `konsumsi_bbm_per_km` tidak dikirim.
    - `peringkat` — urutan rekomendasi (1 = paling disarankan, diurutkan dari `skor_efektif` tertinggi).
    - `skor_efektif` — skor setelah mempertimbangkan faktor efisiensi jarak/BBM (untuk pengurutan).
    - `terdampak_sedimen` / `catatan_sedimen` — penanda & penjelasan area terdampak sedimen pasca-banjir (dekat muara).

### 3.3 Laporan Tangkapan

- **`POST /laporan/teks`** (Input Manual)
  - **Request Body (`application/json`)**:
    ```json
    {
    	"nelayan_id": "27685e13-1a22-48df-b593-c918ee0882e3",
    	"lat": -0.8972,
    	"lng": 100.3508,
    	"jenis_ikan": "Tongkol",
    	"estimasi_kg": 15.5,
    	"catatan": "Melaut lancar"
    }
    ```
  - **Response (`201 Created`)**:
    ```json
    {
    	"id": "b182cb12-88f1-41ee-a9de-ab2391ea2a01",
    	"nelayan_id": "27685e13-1a22-48df-b593-c918ee0882e3",
    	"lat": -0.8972,
    	"lng": 100.3508,
    	"jenis_ikan": "Tongkol",
    	"estimasi_kg": 15.5,
    	"catatan": "Melaut lancar",
    	"perlu_review": false,
    	"waktu": "2026-08-08T10:05:00.000Z",
    	"synced": true
    }
    ```

- **`POST /laporan/suara`** (Upload Rekaman Audio)
  - **Request Body (`multipart/form-data`)**:
    - `file`: Berkas audio (`.wav`, `.m4a`, dll)
    - `nelayan_id`: UUID nelayan (Opsional)
    - `lat`: float (Latitude)
    - `lng`: float (Longitude)
  - **Response (`201 Created`)**:
    ```json
    {
    	"id": "c1992bb3-11ef-4001-a1b9-12a890eaab02",
    	"jenis_ikan": "Kembung",
    	"estimasi_kg": 25.0,
    	"catatan": "Saya hari ini melaut sejauh 10 km... [teks transkripsi]",
    	"perlu_review": false
    }
    ```

- **`POST /sync/laporan-batch`** (Sinkronisasi SQLite Lokal)
  - **Request Body (`application/json`)**:
    ```json
    {
    	"laporan": [
    		{
    			"id": "a98a313b-1b1a-4c2c-8d1e-88ee12ff34c1",
    			"nelayan_id": "27685e13-1a22-48df-b593-c918ee0882e3",
    			"lat": -0.8256,
    			"lng": 100.3167,
    			"jenis_ikan": "Tuna",
    			"estimasi_kg": 50.0,
    			"catatan": "Laporan offline 1",
    			"waktu": "2026-08-08T00:00:00Z"
    		}
    	]
    }
    ```
  - **Response (`200 OK`)**: Array daftar laporan yang sukses disinkronkan ke server.

### 3.4 Kondisi Laut (Cuaca & Gelombang Terdekat)

- **`GET /kondisi-laut?lat=-0.8972&lng=100.3508`**
  - **Response (`200 OK`)**:
    ```json
    {
      "id": "31cf02a3-2c1b-48ae-92da-39088ffea1b1",
      "lat": -0.8972,
      "lng": 100.3508,
      "diperbarui_pada": "2026-08-08T06:00:00Z",
      "gelombang_gabungan": [
        {
          "waktu": "2026-08-08T07:00",
          "tinggi_m": 1.2,
          "arah_derajat": 210,
          "periode_detik": 7.5
        }
      ],
      "gelombang_angin": [...],
      "gelombang_swell": [...],
      "cuaca_per_jam": [
        {
          "waktu": "2026-08-08T07:00",
          "suhu_c": 27.3,
          "kelembapan_persen": 84,
          "tekanan_hpa": 1010.2,
          "uv_index": 3.1,
          "presipitasi_mm": 0.0,
          "probabilitas_presipitasi_persen": 10,
          "kecepatan_angin_kmh": 14.2,
          "arah_angin_derajat": 250,
          "hembusan_angin_kmh": 22.5
        }
      ],
      "pasang_surut": [
        { "waktu": "2026-08-08T05:12", "tinggi_m": 0.3, "tipe": "surut" },
        { "waktu": "2026-08-08T11:40", "tinggi_m": 1.8, "tipe": "pasang" }
      ]
    }
    ```

---

## 3.5 Panduan "Siap Lanjut ke Tahap Android"

**Base URL API untuk aplikasi mobile:**

| Lingkungan            | Base URL                                                                 |
| --------------------- | ------------------------------------------------------------------------ |
| Development (laptop)  | `http://localhost:8000`                                                  |
| Android Emulator      | `http://10.0.2.2:8000`                                                   |
| Perangkat fisik (LAN) | `http://<IP-LAPTOP>:8000` (mis. `http://192.168.1.10:8000`)              |
| Production (deploy)   | `https://<domain-anda>` (sesuai DEPLOYMENT.md)                           |

**Checklist sebelum mulai development Android:**
1. ✅ Server berjalan — `uvicorn main:app --reload` di folder `server/`.
2. ✅ Swagger terbuka — buka `http://localhost:8000/docs` (semua 12 endpoint terlihat).
3. ✅ Health check OK — `curl http://localhost:8000/health` → `{"status":"ok",...}`.
4. ✅ Sudah bisa registrasi nelayan & menghasilkan `konsumsi_bbm_per_km`.
5. ✅ Sudah bisa `GET /zona-rekomendasi` (grid dinamis) dengan `konsumsi_bbm_per_km`.
6. ✅ Sudah bisa `POST /laporan/teks`, `/sync/laporan-batch`, `/sos`, `/push-token`.

**Set di aplikasi Expo (React Native):**
```env
# app/.env
EXPO_PUBLIC_API_BASE_URL=http://10.0.2.2:8000
```
Ganti ke `http://<IP-LAPTOP>:8000` saat mencoba di perangkat fisik, dan ke domain production saat rilis.

**Endpoint yang paling dipakai mobile app (offline-first):**
- `GET  /zona-rekomendasi` → sync zona saat online, cache ke SQLite untuk offline.
- `POST /laporan/teks` & `POST /sync/laporan-batch` → kirim laporan online & sinkronisasi offline.
- `POST /sos` + `POST /push-token` → anti-SOS + daftar notifikasi push.
- `GET  /kondisi-laut` → cache cuaca/gelombang/pasut untuk tampil offline.
- `GET  /titik-favorit` → lokasi favorit yang disimpan offline.

---

## 4. Dokumentasi & Panduan Pengujian (Testing)

Pengujian dibagi menjadi dua jenis utama: **Unit Test** (pengujian logika matematika murni/offline) dan **Integration/API Test** (pengujian endpoint HTTP yang menyentuh database PostgreSQL+PostGIS).

### 4.1 Panduan Langkah-Demi-Langkah & Pemecahan Masalah Docker (Database PostGIS)

Karena sistem MuaroTrack menggunakan data geografis/spasial (seperti koordinat GPS dan kueri radius notifikasi SOS), kita membutuhkan PostgreSQL yang dilengkapi ekstensi **PostGIS**. Di komputer Anda, cara paling mudah menjalankannya adalah melalui **Docker Desktop**.

Berikut adalah panduan detail cara mengoperasikan Docker untuk database:

#### Langkah 1: Persiapan Awal Docker Desktop

1. Pastikan Anda telah mengunduh dan menginstal [Docker Desktop untuk Windows](https://www.docker.com/products/docker-desktop/).
2. Jalankan aplikasi **Docker Desktop** dari menu Start Windows.
3. Pastikan status Docker aktif. Anda bisa melihat indikator warna **hijau** di pojok kiri bawah aplikasi Docker Desktop (menandakan Docker Engine aktif). Ikon paus Docker juga akan muncul di system tray taskbar Windows Anda.

#### Langkah 2: Menyalakan Database PostgreSQL + PostGIS

1. Buka terminal (PowerShell atau Command Prompt) di komputer Anda.
2. Masuk ke direktori `server/` dari proyek MuaroTrack.
3. Jalankan perintah berikut untuk mengunduh image database dan menjalankannya di latar belakang:
   ```powershell
   docker compose up -d
   ```
   _Penjelasan Perintah_:
   - `docker compose`: Utilitas untuk mendefinisikan dan menjalankan aplikasi Docker multi-container (dikonfigurasi melalui `docker-compose.yml`).
   - `up`: Membuat dan menjalankan container database.
   - `-d` (_detached_): Menjalankan container di latar belakang. Anda bisa terus menggunakan terminal tanpa perlu membuka tab baru.

#### Langkah 3: Verifikasi Status Database

Untuk memastikan container berjalan tanpa masalah, jalankan perintah:

```powershell
docker ps
```

Anda akan melihat daftar tabel container. Pastikan ada container dengan nama **`muarotrack-db`** dan statusnya adalah `Up` (berjalan) serta memetakan port `0.0.0.0:5432->5432/tcp`.

#### Langkah 4: Jalankan Pytest

Setelah database aktif di latar belakang, pastikan venv Anda aktif, lalu jalankan seluruh rangkaian pengujian:

```powershell
pytest -v
```

---

### 4.2 Perintah Operasional Docker Tambahan

Berikut beberapa perintah penting jika Anda ingin memantau atau menghentikan database Docker:

- **Melihat Log Database (Untuk Memeriksa Error)**:
  Jika database tidak bisa diakses, Anda bisa melihat log internal PostgreSQL dengan perintah:
  ```powershell
  docker logs muarotrack-db
  ```
- **Mematikan Database (Menghemat RAM)**:
  Jika Anda sudah selesai melatih kode dan ingin mematikan database agar tidak memakan RAM komputer, jalankan:
  ```powershell
  docker compose down
  ```
  _Tenang, data Anda tidak akan hilang_ karena telah disimpan secara persisten di volume lokal komputer Anda yang diatur oleh Docker (`postgres_data`).

---

### 4.3 Pemecahan Masalah (Troubleshooting) Konflik Port 5432

Jika saat menjalankan `docker compose up -d` Anda mendapatkan pesan error seperti ini:

> `driver failed programming external connectivity on endpoint muarotrack-db... bind: address already in use`

Ini berarti **Port 5432 di komputer Anda sudah digunakan oleh aplikasi lain** (biasanya karena Anda sudah menginstal PostgreSQL secara manual langsung di Windows sebelum ini).

#### Solusi 1: Hentikan PostgreSQL Bawaan Windows (Disarankan)

1. Buka pencarian Windows, ketik **PowerShell**, klik kanan dan pilih **Run as Administrator**.
2. Jalankan perintah berikut untuk menghentikan layanan PostgreSQL Windows:
   ```powershell
   Stop-Service -Name postgresql*
   ```
3. Kembali ke terminal proyek Anda dan jalankan ulang:
   ```powershell
   docker compose up -d
   ```

#### Solusi 2: Ganti Port Mapping di `docker-compose.yml`

Jika Anda tidak ingin mematikan PostgreSQL Windows Anda, Anda bisa mengubah port container Docker ke port lain (misalnya `5433`):

1. Buka [docker-compose.yml](docker-compose.yml).
2. Ubah bagian `ports` dari `- "5432:5432"` menjadi `- "5433:5432"`.
3. Buka berkas `.env` Anda dan ubah `DATABASE_URL` agar menggunakan port baru tersebut:
   ```env
   DATABASE_URL=postgresql://postgres:postgres@localhost:5433/muarotrack
   ```
4. Jalankan kembali `docker compose up -d`.

---

### 4.4 Struktur Berkas Pengujian & Hasil Verifikasi

Seluruh pengujian diletakkan pada folder `server/tests/` yang terdiri dari:

#### 1. `tests/test_geo.py` (Unit Test Geografis)

- **Logika yang diuji**:
  - Ketepatan jarak `haversine_km` (membandingkan rute Padang-Bukittinggi sekitar ~70 - 75 km).
  - Ketepatan arah mata angin `bearing` (Utara = 0°, Timur = 90°).
  - Perhitungan estimasi BBM pulang-pergi (`prediksi_bbm`).
  - Total akumulasi jarak dari rute multi-titik (`total_jarak_jalur`).
- **Verifikasi**: Lolos (Pass).

#### 2. `tests/test_moon.py` (Unit Test Astronomis)

- **Logika yang diuji**:
  - Memastikan fungsi `hitung_fase_bulan` mengembalikan nilai yang sah dalam rentang astronomis [0.0, 1.0].
  - Memastikan iluminasi bulan dan skor fase bulan bernilai di antara 0.0 (Bulan Baru) dan 1.0 (Purnama).
- **Verifikasi**: Lolos (Pass).

#### 3. `tests/test_scoring.py` (Unit Test Algoritma Scoring)

- **Logika yang diuji**:
  - Uji batas bawah & atas fungsi penahan nilai (`clamp`).
  - Kurva normalisasi SST (ideal ~24–31 °C), Klorofil (log 0.1-10), NDTI/kekeruhan, Batimetri (kedalaman 10-40m), dan Jarak Muara.
  - Formula pembobotan skor akhir dan pengaktifan bonus komunitas (+10% skor) saat terdapat 3 laporan nelayan sekitar.
- **Verifikasi**: Lolos (Pass).

#### 4. `tests/test_nelayan.py` (API Test Onboarding)

- **Logika yang diuji**:
  - `POST /nelayan` sukses menghitung `konsumsi_bbm_per_km` secara otomatis berdasarkan data onboarding.
  - Pencegahan input salah (`jarak_km_biasa = 0`) menghasilkan response error `422 Unprocessable Entity`.
- **Verifikasi**: Lolos (Pass).

#### 5. `tests/test_laporan.py` (API Test Input Laporan)

- **Logika yang diuji**:
  - `POST /laporan/teks` berhasil menyimpan data koordinat spasial dan tangkapan.
  - `POST /laporan/suara` berhasil mensimulasikan transkripsi audio ke teks (STT Whisper) dan mengekstrak entitas ikan & berat (DeepSeek AI).
  - `POST /sync/laporan-batch` berhasil melakukan sinkronisasi massal untuk data offline.
- **Verifikasi**: Lolos (Pass).

#### 6. `tests/test_zona.py` (API Test Rekomendasi Spasial)

- **Logika yang diuji**:
  - `GET /zona-rekomendasi` membangun grid **dinamis** dari posisi nelayan (mis. Pantai Gajah — bukan salah satu muara hardcode), menghasilkan minimal 1 zona, peringkat 1..N berurutan, semua dalam radius, dan diurutkan menurun berdasarkan `skor_efektif`.
  - Test kedua memverifikasi **estimasi BBM** pulang-pergi (`jarak × konsumsi × 2`) saat parameter `konsumsi_bbm_per_km` dikirim.
- **Verifikasi**: Lolos (Pass).

#### 7. `tests/test_kondisi_laut.py` (API Test Stasiun Laut)

- **Logika yang diuji**:
  - `GET /kondisi-laut` mengembalikan data cuaca, gelombang, dan pasang surut terdekat dari lokasi nelayan.
  - Menangani kasus jika stasiun kosong dengan error `404 Not Found`.
- **Verifikasi**: Lolos (Pass).

#### 8. `tests/test_titik_favorit.py` (API Test Titik Favorit)

- **Logika yang diuji**:
  - Pembuatan dan pengambilan daftar koordinat favorit per nelayan.
- **Verifikasi**: Lolos (Pass).

#### 9. `tests/test_sos.py` (API Test Sinyal Darurat)

- **Logika yang diuji**:
  - Pendaftaran Push Token nelayan B.
  - Pengiriman SOS nelayan A di titik koordinat terdekat B memicu algoritma penyebaran push notification darurat ke nelayan B (karena lokasi B berada dalam radius 10 km).
  - Pengambilan daftar SOS aktif untuk digambar di peta.
- **Verifikasi**: Lolos (Pass).

#### 10. Status Pengujian Terakhir

```text
========== 24 passed, 1 warning in 61.20s ==========
```
