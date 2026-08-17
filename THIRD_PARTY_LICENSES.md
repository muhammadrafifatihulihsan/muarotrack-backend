# THIRD-PARTY LICENSES — MuaroTrack Backend Server (Python/FastAPI)

Dokumen ini mencantumkan komponen/library pihak ketiga beserta lisensinya yang digunakan pada backend server MuaroTrack. Daftar ini diverifikasi pada Agustus 2026 dan konsisten dengan dokumen "Daftar Komponen/Library dan Lisensi" yang diserahkan pada kompetisi GEMASTIK XIX.

Lisensi kode sumber aplikasi: **MIT License** (lihat berkas `LICENSE`).

## A. Dependensi Runtime

| Komponen | Versi | Lisensi |
|---|---|---|
| fastapi | 0.141.1 | MIT |
| uvicorn[standard] | 0.52.1 | BSD-3-Clause |
| sqlalchemy | 2.0.51 | MIT |
| geoalchemy2 | 0.20.0 | MIT |
| shapely | 2.1.2 | BSD-3-Clause |
| psycopg2-binary | 2.9.12 | LGPL (dengan pengecualian) |
| pydantic | 2.13.4 | MIT |
| pydantic-settings | 2.15.0 | MIT |
| httpx | 0.28.1 | BSD-3-Clause |
| python-multipart | 0.0.32 | Apache-2.0 |
| apscheduler | 3.11.3 | MIT |
| exponent-server-sdk | 2.2.0 | MIT |
| openai (untuk DeepSeek API) | 2.53.0 | Apache-2.0 |
| earthengine-api | 1.7.38 | Apache-2.0 |
| faster-whisper | ~1.2.1 | MIT |

## B. Dependensi Transitif Utama

| Komponen | Versi | Lisensi |
|---|---|---|
| starlette | 1.4.1 | BSD-3-Clause |
| pydantic_core | 2.46.4 | MIT |
| greenlet | 3.5.4 | MIT |
| anyio | 4.14.2 | MIT |
| typing_extensions | 4.16.0 | PSF-2.0 |
| certifi | 2026.7.22 | MPL-2.0 |

## C. Layanan Eksternal yang Digunakan

| Layanan | Fungsi | Lisensi |
|---|---|---|
| Google Earth Engine | Data satelit SST, klorofil, turbiditas | Proprietary (gratis untuk riset) |
| Open-Meteo | Gelombang, cuaca | CC BY 4.0 |
| TideCheck | Pasang surut | Proprietary |
| BATNAS (Badan Informasi Geospasial) | Batimetri | Data terbuka pemerintah |
| OpenStreetMap | Tile peta | ODbL |
| Esri | Tile peta | Proprietary |
| CARTO | Tile peta | Proprietary |
| OpenSeaMap | Tile peta laut | ODbL |
| DeepSeek API | Parsing teks AI | Proprietary |
| Expo Push | Notifikasi push | Proprietary |

Seluruh layanan eksternal digunakan sesuai ketentuan layanan masing-masing (ToS) pada skala pilot tanpa biaya. Lisensi font (OFL-1.1) tidak mewajibkan aplikasi dirilis terbuka.
