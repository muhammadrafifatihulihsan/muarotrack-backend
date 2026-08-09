from datetime import datetime

from sqlalchemy import func
from geoalchemy2.shape import to_shape

from db.session import SessionLocal
from models.laporan import LaporanTangkapan
from models.zona import ZonaRekomendasi, ZonaSatelit
from services.gee_client import GeeClient
from services.moon import fraksi_iluminasi_bulan
from services.scoring import hitung_skor_zona

# CATATAN: Grid zona TIDAK lagi di-hardcode global. Rekomendasi dibangun
# secara dinamis dari posisi nelayan di routers/zona.py. Job ini melanjutkan
# tugas refresh: memperbarui ulang data satelit & skor untuk titik zona yang
# SUDAH tersimpan di cache (hasil permintaan sebelumnya), agar saat nelayan
# online kembali data cache tetap segar untuk mode offline.


def run() -> dict:
    """
    Job terjadwal untuk memperbarui data satelit (GEE) dan skor zona
    untuk semua titik zona yang sudah tersimpan di tabel cache.
    """
    db = SessionLocal()
    gee_client = GeeClient()

    total_updated = 0
    now = datetime.now()

    try:
        # Hitung fraksi iluminasi bulan hari ini secara offline
        fase_bulan_illum = fraksi_iluminasi_bulan(now.date())

        # Ambil semua titik zona_rekomendasi yang tersimpan.
        titik_zona = db.query(ZonaRekomendasi).all()

        for zona in titik_zona:
            point = to_shape(zona.lokasi)
            lat, lng = point.y, point.x

            titik_wkt = f"SRID=4326;POINT({lng} {lat})"

            # 1. Ambil data satelit (SST, Chlorophyll, NDTI) - atau mock.
            sat_data = gee_client.fetch_satellite_data(lat, lng)

            # 2. Upsert ke zona_satelit.
            zona_sat = db.query(ZonaSatelit).filter(
                func.ST_Distance(zona.lokasi, titik_wkt) < 0.0001
            ).first()

            if not zona_sat:
                zona_sat = ZonaSatelit(lokasi=titik_wkt)
                db.add(zona_sat)

            zona_sat.sst = sat_data["sst"]
            zona_sat.klorofil = sat_data["klorofil"]
            zona_sat.turbiditas_ndti = sat_data["turbiditas_ndti"]
            zona_sat.diperbarui_pada = now

            # 3. Ambil kedalaman laut placeholder (batimetri statis).
            depth_m = 25.0

            # 4. Hitung laporan nelayan sekitar (radius 500m) untuk bonus komunitas.
            laporan_count = db.query(LaporanTangkapan).filter(
                func.ST_Distance(LaporanTangkapan.lokasi, titik_wkt) < 500.0
            ).count()

            # 5. Hitung skor gabungan (skor_zona).
            skor, detail_skor, _ = hitung_skor_zona(
                sst=sat_data["sst"],
                klorofil=sat_data["klorofil"],
                turbiditas_ndti=sat_data["turbiditas_ndti"],
                depth_m=depth_m,
                fase_bulan_illum=fase_bulan_illum,
                lat=lat,
                lng=lng,
                jarak_km_dari_titik_mulai=0.0,
                laporan_dalam_500m=laporan_count,
            )

            # 6. Update zona_rekomendasi yang sudah ada.
            zona.skor = skor
            zona.detail_skor = detail_skor
            zona.dihitung_pada = now

            total_updated += 1

        db.commit()
        print(f"Sukses memperbarui {total_updated} titik zona rekomendasi dari cache.")
        return {"status": "success", "updated_points": total_updated}

    except Exception as e:
        db.rollback()
        print(f"Gagal memperbarui zona satelit: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()