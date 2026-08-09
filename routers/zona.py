import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.config import get_settings
from core.deps import get_db
from models.laporan import LaporanTangkapan
from models.zona import ZonaRekomendasi, ZonaSatelit
from schemas.zona import ZonaRekomendasiListResponse, ZonaRekomendasiOut
from services.geo import haversine_km
from services.gee_client import GeeClient
from services.moon import fraksi_iluminasi_bulan
from services.scoring import faktor_hemat_bbm, hitung_skor_zona, tanda_sedimen
from services.zona_grid import bangun_grid

router = APIRouter(prefix="/zona-rekomendasi", tags=["Zona Rekomendasi"])

settings = get_settings()
gee_client = GeeClient()


def _skor_efektif(skor_mentah: float, jarak_km: float) -> float:
    """Skor efektif = potensi tangkapan x bobot efisiensi jarak/BBM (untuk pengurutan)."""
    return round(skor_mentah * (0.6 + 0.4 * faktor_hemat_bbm(jarak_km)), 4)


@router.get("", response_model=ZonaRekomendasiListResponse)
def ambil_zona_rekomendasi(
    lat: float = Query(..., ge=-90, le=90, description="Latitude GPS posisi nelayan (titik mulai melaut)"),
    lng: float = Query(..., ge=-180, le=180, description="Longitude GPS posisi nelayan (titik mulai melaut)"),
    radius_km: float = Query(22.0, gt=0, description="Radius pencarian maksimum dalam kilometer"),
    konsumsi_bbm_per_km: float = Query(None, gt=0, description="Konsumsi BBM (liter/km) untuk estimasi BBM"),
    db: Session = Depends(get_db)
):
    """
    Mengambil daftar rekomendasi zona tangkap BERPANDU dari posisi nelayan.

    Grid dibangun DINAMIS di sekitar titik tempat nelayan menyiapkan sampan,
    bukan dari koordinat yang di-hardcode. Titik di luar radius maksimum tidak
    dibangkitkan (menghindari rekomendasi boros BBM). Hasil diurutkan dari
    skor efektif tertinggi (keseimbangan potensi tangkapan vs jarak/BBM),
    masing-masing diberi peringkat 1..N.
    """
    titik_mulai = {"lat": lat, "lng": lng}

    # 1. Bangun grid dinamis di sekitar posisi nelayan.
    grid = bangun_grid(
        pusat_lat=lat,
        pusat_lng=lng,
        radius_km_maks=radius_km,
        jumlah_titik=settings.ZONA_JUMLAH_TITIK,
        bearing_laut_deg=settings.BEARING_LAUT_DEG,
    )

    if not grid:
        return ZonaRekomendasiListResponse(zonas=[])

    # 2. Hitung skor untuk tiap titik grid (online) atau baca cache tersimpan.
    now = datetime.now()
    fase_bulan_illum = fraksi_iluminasi_bulan(now.date())

    hasil_zona = []
    for titik in grid:
        lat_t = titik["lat"]
        lng_t = titik["lng"]
        jarak_dari_mulai_km = haversine_km(lat, lng, lat_t, lng_t)
        if jarak_dari_mulai_km > radius_km:
            continue

        # Cek cache zona_rekomendasi terdekat (jarak < 1 km) yang masih fresh.
        titik_wkt = f"SRID=4326;POINT({lng_t} {lat_t})"
        zona_cache = (
            db.query(ZonaRekomendasi)
            .filter(func.ST_DWithin(ZonaRekomendasi.lokasi, titik_wkt, 1000.0))
            .order_by(func.ST_Distance(ZonaRekomendasi.lokasi, titik_wkt))
            .first()
        )

        if zona_cache is not None:
            skor_mentah = zona_cache.skor
            detail_skor = dict(zona_cache.detail_skor or {})
            dihitung_pada = zona_cache.dihitung_pada
            zona_id = zona_cache.id
        else:
            # Hitung real-time: data satelit (atau mock) -> skor -> simpan cache.
            sat_data = gee_client.fetch_satellite_data(lat_t, lng_t)
            laporan_count = (
                db.query(func.count())
                .select_from(LaporanTangkapan)
                .filter(func.ST_DWithin(LaporanTangkapan.lokasi, titik_wkt, 500.0))
            ).scalar() or 0

            skor_mentah, detail_skor, _ = hitung_skor_zona(
                sst=sat_data["sst"],
                klorofil=sat_data["klorofil"],
                turbiditas_ndti=sat_data["turbiditas_ndti"],
                depth_m=25.0,  # placeholder kedalaman (batimetri statis)
                fase_bulan_illum=fase_bulan_illum,
                lat=lat_t,
                lng=lng_t,
                jarak_km_dari_titik_mulai=jarak_dari_mulai_km,
                laporan_dalam_500m=laporan_count,
            )

            # Simpan ke zona_satelit (data mentah) & zona_rekomendasi (skor).
            zona_sat = (
                db.query(ZonaSatelit)
                .filter(func.ST_DWithin(ZonaSatelit.lokasi, titik_wkt, 100.0))
                .first()
            )
            if zona_sat is None:
                zona_sat = ZonaSatelit(lokasi=titik_wkt)
                db.add(zona_sat)
            zona_sat.sst = sat_data["sst"]
            zona_sat.klorofil = sat_data["klorofil"]
            zona_sat.turbiditas_ndti = sat_data["turbiditas_ndti"]
            zona_sat.diperbarui_pada = now

            zona_rek = (
                db.query(ZonaRekomendasi)
                .filter(func.ST_DWithin(ZonaRekomendasi.lokasi, titik_wkt, 100.0))
                .first()
            )
            if zona_rek is None:
                zona_rek = ZonaRekomendasi(lokasi=titik_wkt)
                db.add(zona_rek)
            zona_rek.skor = skor_mentah
            zona_rek.detail_skor = detail_skor
            zona_rek.dihitung_pada = now

            db.commit()
            dihitung_pada = now
            zona_id = zona_rek.id

        # 3. Atribut per-request: skor efektif, jarak, BBM, dan penanda sedimen.
        skor_efektif = _skor_efektif(skor_mentah, jarak_dari_mulai_km)

        sedimen = tanda_sedimen(lat_t, lng_t)
        estimasi_bbm = None
        if konsumsi_bbm_per_km:
            estimasi_bbm = round(jarak_dari_mulai_km * konsumsi_bbm_per_km * 2.0, 2)

        hasil_zona.append({
            "id": zona_id,
            "lat": lat_t,
            "lng": lng_t,
            "skor": skor_mentah,
            "detail_skor": detail_skor,
            "dihitung_pada": dihitung_pada,
            "jarak_km": round(jarak_dari_mulai_km, 2),
            "estimasi_bbm_liter": estimasi_bbm,
            "skor_efektif": skor_efektif,
            **sedimen,
        })

    # 4. Urutkan berdasarkan skor efektif (tertinggi dulu), lalu beri peringkat.
    hasil_zona.sort(key=lambda z: z["skor_efektif"], reverse=True)
    zonas_out = []
    for i, z in enumerate(hasil_zona, start=1):
        zonas_out.append(ZonaRekomendasiOut(
            id=z["id"] or uuid.uuid4(),
            lat=z["lat"],
            lng=z["lng"],
            skor=z["skor"],
            detail_skor=z["detail_skor"],
            dihitung_pada=z["dihitung_pada"],
            jarak_km=z["jarak_km"],
            estimasi_bbm_liter=z["estimasi_bbm_liter"],
            peringkat=i,
            skor_efektif=z["skor_efektif"],
            terdampak_sedimen=z["terdampak_sedimen"],
            catatan_sedimen=z["catatan_sedimen"],
        ))

    return ZonaRekomendasiListResponse(zonas=zonas_out)