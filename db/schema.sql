-- ============================================================
-- MuaroTrack — Skema Database PostgreSQL (PostGIS)
-- Dibuat sinkron dengan definisi ORM di server/models/*.py
-- Jalankan: psql -U postgres -d muarotrack -f db/schema.sql
-- ============================================================

CREATE EXTENSION IF NOT EXISTS postgis;

-- 1. nelayan
CREATE TABLE IF NOT EXISTS nelayan (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nama TEXT NOT NULL,
    konsumsi_bbm_per_km DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 2. laporan_tangkapan
CREATE TABLE IF NOT EXISTS laporan_tangkapan (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nelayan_id UUID REFERENCES nelayan(id) ON DELETE SET NULL,
    lokasi GEOGRAPHY(POINT, 4326) NOT NULL,
    jenis_ikan TEXT,
    estimasi_kg DOUBLE PRECISION,
    catatan TEXT,
    perlu_review BOOLEAN DEFAULT false,
    waktu TIMESTAMPTZ DEFAULT now(),
    synced BOOLEAN DEFAULT true
);

-- 3. zona_satelit
CREATE TABLE IF NOT EXISTS zona_satelit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lokasi GEOGRAPHY(POINT, 4326) NOT NULL,
    sst DOUBLE PRECISION,
    klorofil DOUBLE PRECISION,
    turbiditas_ndti DOUBLE PRECISION,
    diperbarui_pada TIMESTAMPTZ DEFAULT now()
);

-- 4. zona_rekomendasi
CREATE TABLE IF NOT EXISTS zona_rekomendasi (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lokasi GEOGRAPHY(POINT, 4326) NOT NULL,
    skor DOUBLE PRECISION NOT NULL,
    detail_skor JSONB,
    dihitung_pada TIMESTAMPTZ DEFAULT now()
);

-- 5. trip_bbm
CREATE TABLE IF NOT EXISTS trip_bbm (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nelayan_id UUID NOT NULL REFERENCES nelayan(id) ON DELETE CASCADE,
    jarak_km DOUBLE PRECISION NOT NULL,
    prediksi_liter DOUBLE PRECISION NOT NULL,
    liter_aktual DOUBLE PRECISION,
    waktu TIMESTAMPTZ DEFAULT now()
);

-- 6. kondisi_laut
CREATE TABLE IF NOT EXISTS kondisi_laut (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lokasi GEOGRAPHY(POINT, 4326) NOT NULL UNIQUE,
    gelombang_gabungan JSONB,
    gelombang_angin JSONB,
    gelombang_swell JSONB,
    cuaca_per_jam JSONB,
    pasang_surut JSONB,
    sumber_gelombang_cuaca TEXT DEFAULT 'open-meteo',
    sumber_pasut TEXT DEFAULT 'tidecheck',
    diperbarui_pada TIMESTAMPTZ DEFAULT now()
);

-- 7. titik_favorit
CREATE TABLE IF NOT EXISTS titik_favorit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nelayan_id UUID NOT NULL REFERENCES nelayan(id) ON DELETE CASCADE,
    nama_label TEXT NOT NULL,
    lokasi GEOGRAPHY(POINT, 4326) NOT NULL,
    catatan TEXT,
    laporan_tangkapan_id UUID REFERENCES laporan_tangkapan(id) ON DELETE SET NULL,
    dibuat_pada TIMESTAMPTZ DEFAULT now(),
    synced BOOLEAN DEFAULT true
);

-- 8. sos_signal
CREATE TABLE IF NOT EXISTS sos_signal (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nelayan_id UUID REFERENCES nelayan(id) ON DELETE SET NULL,
    lokasi GEOGRAPHY(POINT, 4326) NOT NULL,
    pesan TEXT,
    waktu_kejadian TIMESTAMPTZ NOT NULL,
    waktu_terkirim TIMESTAMPTZ,
    status TEXT DEFAULT 'tertunda',
    dibuat_pada TIMESTAMPTZ DEFAULT now()
);

-- 9. push_token
CREATE TABLE IF NOT EXISTS push_token (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nelayan_id UUID NOT NULL REFERENCES nelayan(id) ON DELETE CASCADE,
    expo_push_token TEXT NOT NULL UNIQUE,
    diperbarui_pada TIMESTAMPTZ DEFAULT now()
);

-- Indeks spasial
CREATE INDEX IF NOT EXISTS idx_laporan_lokasi ON laporan_tangkapan USING GIST (lokasi);
CREATE INDEX IF NOT EXISTS idx_zona_satelit_lokasi ON zona_satelit USING GIST (lokasi);
CREATE INDEX IF NOT EXISTS idx_zona_rekomendasi_lokasi ON zona_rekomendasi USING GIST (lokasi);
CREATE INDEX IF NOT EXISTS idx_kondisi_laut_lokasi ON kondisi_laut USING GIST (lokasi);
CREATE INDEX IF NOT EXISTS idx_titik_favorit_lokasi ON titik_favorit USING GIST (lokasi);
CREATE INDEX IF NOT EXISTS idx_sos_lokasi ON sos_signal USING GIST (lokasi);

-- Seed 3 stasiun kondisi_laut
INSERT INTO kondisi_laut (lokasi) VALUES
    (ST_GeogFromText('SRID=4326;POINT(100.3508 -0.8972)')),
    (ST_GeogFromText('SRID=4326;POINT(100.3167 -0.8256)')),
    (ST_GeogFromText('SRID=4326;POINT(100.3444 -0.8988)'))
ON CONFLICT (lokasi) DO NOTHING;
