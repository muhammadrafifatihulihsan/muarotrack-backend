# ============================================================
# MuaroTrack Backend — Dockerfile Produksi (multi-stage)
# ============================================================
# Tahap 1: Builder — instal dependensi Python ke direktori terpisah.
# Tahap 2: Runtime — image ramping, hanya berisi aplikasi + site-packages.

FROM python:3.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

# Salin requirements terlebih dahulu agar lapisan cache Docker efisien.
COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt


# ---------- Runtime ----------
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

# Runtime umum & librari sistem yang dibutuhkan ekstensi (jika ada).
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Salin site-packages dari builder.
COPY --from=builder /install /usr/local

# Salin seluruh kode aplikasi.
COPY . .

# Jalankan sebagai user non-root (praktik keamanan container).
RUN useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production: 1 worker karena scheduler APScheduler berjalan di dalam lifespan app.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]