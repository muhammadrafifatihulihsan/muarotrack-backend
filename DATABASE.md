# Panduan Database MuaroTrack (PostgreSQL + PostGIS)

Dokumen ini menjelaskan **di mana letak database**, bagaimana melihat isinya, dan perintah-perintah dasarnya. Cocok untuk Anda yang baru belajar PostgreSQL.

---

## 1. Database-nya di mana?

Database ada di dalam **container Docker** bernama `muarotrack-db` dan berjalan otomatis saat Anda menjalankan:

```powershell
docker compose up -d
```

Detail koneksi (lihat `server/.env` → `DATABASE_URL`):

| Item      | Nilai                                        |
| --------- | -------------------------------------------- |
| Host      | `localhost` (dev) / `db` (docker compose prod) |
| Port      | `5433`                                       |
| Database  | `muarotrack`                                 |
| User      | `postgres`                                   |
| Password  | `postgres`                                   |

> **Kenapa tidak ada file `.db`/`.sqlite`?** Karena proyek memakai PostgreSQL (database server), bukan SQLite (file tunggal). PostgreSQL berjalan sebagai service di Docker; datanya disimpan di volume Docker `postgres_data` (tetap aman walau container dimatikan).

---

## 2. Struktur Tabel (9 tabel)

Semua tabel dibuat otomatis oleh aplikasi (`init_db()` → `Base.metadata.create_all()`) dan juga tersedia sebagai file SQL: **[`db/schema.sql`](db/schema.sql)**.

| Tabel               | Fungsi                                                                 |
| ------------------- | ---------------------------------------------------------------------- |
| `nelayan`           | Profil kapal nelayan + konsumsi BBM per km                             |
| `laporan_tangkapan` | Laporan tangkapan (teks & suara)                                       |
| `zona_satelit`      | Data mentah satelit (SST, klorofil, turbiditas) per titik grid         |
| `zona_rekomendasi`  | Skor rekomendasi zona tangkap + detail skor                            |
| `trip_bbm`          | Catatan prediksi vs realisasi BBM                                      |
| `kondisi_laut`      | Cache gelombang, cuaca, pasang surut per stasiun                       |
| `titik_favorit`     | Lokasi favorit yang disimpan nelayan                                   |
| `sos_signal`        | Sinyal darurat SOS                                                     |
| `push_token`        | Token notifikasi push (Expo) per perangkat                             |

Kolom bertipe `GEOGRAPHY(POINT, 4326)` = koordinat GPS (PostGIS). Query jarak memakai fungsi `ST_DWithin`, `ST_Distance`.

---

## 3. Cara Melihat Isi Database (Visual / GUI)

Paling mudah pakai aplikasi GUI gratis:

| Aplikasi  | Link                                 |
| --------- | ------------------------------------ |
| DBeaver   | https://dbeaver.io (Community, gratis) |
| pgAdmin 4 | https://www.pgadmin.org              |
| VS Code   | Install extension **PostgreSQL** (untuk koneksi & query) |

Langkah umum:
1. Install salah satu aplikasi di atas.
2. Buat koneksi baru dengan detail pada §1 (Host `localhost`, Port `5433`, Database `muarotrack`, User `postgres`, Password `postgres`).
3. Setelah tersambung, Anda bisa melihat 9 tabel dan menjalankan query.

---

## 4. Perintah `psql` (Terminal)

`psql` tersedia di dalam container docker:

```bash
# Masuk ke container database
docker exec -it muarotrack-db psql -U postgres -d muarotrack

# Di dalam psql:
\dt          # daftar semua tabel
\d nelayan   # detail kolom tabel nelayan
SELECT * FROM nelayan LIMIT 5;
SELECT id, nama, konsumsi_bbm_per_km FROM nelayan;

# Keluar dari psql
\q
```

Menjalankan file skema SQL dari dalam container:

```bash
# Salin schema.sql ke dalam container lalu eksekusi
docker cp db/schema.sql muarotrack-db:/tmp/schema.sql
docker exec -it muarotrack-db psql -U postgres -d muarotrack -f /tmp/schema.sql
```

> `schema.sql` memakai `CREATE TABLE IF NOT EXISTS` & `ON CONFLICT DO NOTHING`, jadi **aman dijalankan berulang kali**.

---

## 5. Kaitan ORM ↔ Tabel

Definisi tabel sebenarnya ada di kode Python (`server/models/*.py`). `schema.sql` hanyalah salinan SQL-nya agar mudah dibaca/diperiksa, dan **harus tetap sinkron** dengan model ORM.

| File model             | Tabel yang didefinisikan |
| ---------------------- | ------------------------ |
| `models/nelayan.py`    | `nelayan`                |
| `models/laporan.py`    | `laporan_tangkapan`      |
| `models/zona.py`       | `zona_satelit`, `zona_rekomendasi` |
| `models/trip_bbm.py`   | `trip_bbm`               |
| `models/kondisi_laut.py` | `kondisi_laut`          |
| `models/titik_favorit.py` | `titik_favorit`       |
| `models/sos.py`        | `sos_signal`, `push_token` |

---

## 6. Reset Database (Opsional)

Jika ingin database bersih dari data percobaan:

```bash
docker compose down          # matikan container
docker volume rm server_postgres_data   # hapus volume (data hilang permanen!)
docker compose up -d         # buat ulang + seed otomatis
```

> ⚠️ Perintah di atas **menghapus semua data**. Hanya lakukan jika yakin.