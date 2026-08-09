# Deployment Backend MuaroTrack (Docker Production)

Panduan untuk menjalankan backend MuaroTrack dalam mode **production** menggunakan Docker.

---

## 1. Prasyarat

- Docker Engine + Docker Compose plugin (versi terbaru).
- Git (untuk clone/pull repo ke server).
- Akses ke VPS/Server (Linux) atau platform PaaS yang mendukung Docker.

> Untuk mesin Windows lokal Anda, Docker Desktop juga bisa dipakai — alur sama,
> hanya sintaks terminal disesuaikan (PowerShell).

---

## 2. Struktur File Production

```
server/
├── Dockerfile                  # Image aplikasi FastAPI (multi-stage, non-root)
├── .dockerignore               # Mengecualikan env/cache/docs saat build
├── docker-compose.prod.yml     # Orkestrasi production: db (PostGIS) + api
├── .env.production.example     # Template env production (salin -> .env.production)
└── main.py                     # Entrypoint aplikasi
```

---

## 3. Langkah Deploy (Docker Compose)

### 3.1. Salin & isi environment production

```bash
cd server
cp .env.production.example .env.production
# lalu edit .env.production — isi POSTGRES_PASSWORD & semua API key
```

### 3.2. Build & jalankan

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

### 3.3. Verifikasi

```bash
# Status container
docker compose -f docker-compose.prod.yml ps

# Healthcheck API
curl http://localhost:8000/health
# -> {"status":"ok","message":"MuaroTrack API Server is running"}

# Log API
docker compose -f docker-compose.prod.yml logs -f api
```

---

## 4. Konfigurasi Env Penting

| Variabel                | Keterangan                                                                                   |
| ----------------------- | -------------------------------------------------------------------------------------------- |
| `MOCK_EXTERNAL`         | `false` = panggil API asli (wajib untuk production)                                          |
| `POSTGRES_PASSWORD`     | Wajib diganti dengan password kuat                                                           |
| `RUN_SCHEDULER`         | `true` (default). Set `false` hanya jika menjalankan >1 replika API                          |
| `ZONA_RADIUS_MAKS_KM`   | Radius maksimum zona rekomendasi (default 22 km ≈ 12 mil laut)                               |
| `ZONA_JUMLAH_TITIK`     | Jumlah titik grid dinamis dari posisi nelayan (default 5)                                    |
| `BEARING_LAUT_DEG`      | Arah laut dari posisi nelayan (default 270° = Barat, untuk pesisir Padang)                   |
| `SOS_RADIUS_KM`         | Radius fan-out push notification SOS (default 10 km)                                         |

---

## 5. Backup & Restore Database

### Backup (dump SQL + PostGIS)

```bash
# Tulis ke file
docker exec muarotrack-db-prod pg_dump -U postgres -d muarotrack --no-owner > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Restore

```bash
cat backup_20260808_120000.sql | docker exec -i muarotrack-db-prod psql -U postgres -d muarotrack
```

### Cadangan volume (opsional, untuk backup byte-for-byte)

```bash
docker run --rm -v muarotrack_postgres_data_prod:/data -v "$PWD":/backup \
  alpine tar czf /backup/postgres_data.tar.gz -C /data .
```

---

## 6. Update / Rollback

### Update ke versi image terbaru

```bash
git pull                      # ambil kode terbaru
docker compose -f docker-compose.prod.yml up -d --build
```

### Rollback ke versi sebelumnya

```bash
# Lihat daftar image
docker images | grep muarotrack

# Jalankan ulang dengan image lama
docker compose -f docker-compose.prod.yml up -d --no-build
```

---

## 7. Catatan Deployment Non-Compose (PaaS: Railway/Render/Fly)

`Dockerfile` tetap dipakai. Yang berbeda hanya cara mengatur environment:

1. Buat project di platform pilih.
2. Atur **Build**: Dockerfile di folder `server/`.
3. Set environment variables manual (lihat daftar di Bagian 4).
4. `DATABASE_URL` diisi manual (pakai Supabase/Postgres eksternal), contoh:
   ```env
   DATABASE_URL=postgresql://user:pass@host:5432/muarotrack
   ```
5. Untuk platform yang menjalankan banyak replika otomatis, set `RUN_SCHEDULER=false`
   pada SEMUA replika dan gunakan cron/job terpisah untuk `jobs/`.

---

## 8. Keamanan Ringkas

- `docker-compose.prod.yml` hanya mengekspos API di `127.0.0.1:8000` — letakkan reverse proxy
  (Nginx/Caddy/Traefik) untuk HTTPS publik.
- Jangan pernah commit `.env.production`.
- Ganti password default pada penyetelan pertama.