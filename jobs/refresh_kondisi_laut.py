from datetime import datetime
from geoalchemy2.shape import to_shape
from db.session import SessionLocal
from models.kondisi_laut import KondisiLaut
from services.marine_client import MarineClient
from services.weather_client import WeatherClient
from services.tide_client import TideClient

def run() -> dict:
    """
    Job terjadwal untuk memperbarui cache ramalan cuaca, gelombang,
    dan pasang surut air laut untuk setiap koordinat stasiun yang terdaftar.
    """
    db = SessionLocal()
    marine_client = MarineClient()
    weather_client = WeatherClient()
    tide_client = TideClient()
    
    total_updated = 0
    now = datetime.now()
    
    try:
        stasiun_list = db.query(KondisiLaut).all()
        
        for stasiun in stasiun_list:
            point = to_shape(stasiun.lokasi)
            lat, lng = point.y, point.x
            
            # 1. Ambil data gelombang
            waves = marine_client.fetch_gelombang(lat, lng)
            
            # 2. Ambil data cuaca
            weather = weather_client.fetch_cuaca(lat, lng)
            
            # 3. Ambil data pasang surut
            tides = tide_client.fetch_pasut(lat, lng)
            
            # Update cache stasiun
            stasiun.gelombang_gabungan = waves.get("gelombang_gabungan", [])
            stasiun.gelombang_angin = waves.get("gelombang_angin", [])
            stasiun.gelombang_swell = waves.get("gelombang_swell", [])
            stasiun.cuaca_per_jam = weather
            stasiun.pasang_surut = tides
            stasiun.diperbarui_pada = now
            
            total_updated += 1
            
        db.commit()
        print(f"Sukses memperbarui cache kondisi laut untuk {total_updated} titik.")
        return {"status": "success", "updated_stations": total_updated}
        
    except Exception as e:
        db.rollback()
        print(f"Gagal memperbarui cache kondisi laut: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()
