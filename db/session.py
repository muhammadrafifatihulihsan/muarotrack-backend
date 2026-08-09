from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from core.config import get_settings
from db.base import Base

settings = get_settings()

engine = create_engine(
    settings.DATABASE_URL,
    # psycopg2 needs no special arguments, but pool pre-ping is good for reliability
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db() -> None:
    # We import models here to ensure they are registered on the Base metadata before create_all
    import models  # noqa: F401
    
    # Enable PostGIS extension if it doesn't exist
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
        
    Base.metadata.create_all(bind=engine)
    
    # Seed default kondisi_laut stasiun coordinates if they don't exist
    db = SessionLocal()
    try:
        from models.kondisi_laut import KondisiLaut
        if db.query(KondisiLaut).count() == 0:
            # 3 default nearshore coordinate points for Padang:
            # 1. Batang Kuranji: lng=100.3508, lat=-0.8972
            # 2. Koto Tangah: lng=100.3167, lat=-0.8256
            # 3. Ulak Karang: lng=100.3444, lat=-0.8988
            coords = [
                "POINT(100.3508 -0.8972)",
                "POINT(100.3167 -0.8256)",
                "POINT(100.3444 -0.8988)"
            ]
            for coord_str in coords:
                stasiun = KondisiLaut(
                    lokasi=f"SRID=4326;{coord_str}",
                    gelombang_gabungan=[],
                    gelombang_angin=[],
                    gelombang_swell=[],
                    cuaca_per_jam=[],
                    pasang_surut=[]
                )
                db.add(stasiun)
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error seeding kondisi_laut: {e}")
    finally:
        db.close()
