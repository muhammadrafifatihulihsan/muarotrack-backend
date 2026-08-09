import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from db.base import Base
from main import app
from core.deps import get_db
from core.config import get_settings
from fastapi.testclient import TestClient

settings = get_settings()

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """
    Menyiapkan database pengujian dengan mengaktifkan PostGIS dan membuat seluruh tabel.
    """
    engine = create_engine(settings.DATABASE_URL)
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
    Base.metadata.create_all(bind=engine)
    yield
    # Kita tidak drop_all secara otomatis untuk mempercepat run berikutnya,
    # namun tabel dibersihkan di setiap pengujian individual.

@pytest.fixture(autouse=True)
def clean_db(db):
    """
    Membersihkan isi tabel sebelum setiap test dijalankan agar tidak ada konflik data.
    """
    # Matikan foreign key check atau urutkan pembersihan dari tabel dependensi terdalam
    db.execute(text("TRUNCATE TABLE trip_bbm, titik_favorit, sos_signal, push_token, laporan_tangkapan, nelayan, zona_satelit, zona_rekomendasi, kondisi_laut CASCADE;"))
    db.commit()
    
    # Seed ulang kondisi_laut stasiun default agar endpoint kondisi-laut tidak kosong
    from models.kondisi_laut import KondisiLaut
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
    yield

@pytest.fixture
def db():
    """
    Menyediakan sesi database terisolasi untuk pengujian.
    """
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def client(db):
    """
    Menyediakan FastAPI TestClient dengan dependensi get_db yang telah di-override ke DB pengujian.

    PENTING: Membuat TestClient memicu lifespan FastAPI (di main.py) yang menjalankan job
    refresh_zona_satelit.run() dan refresh_kondisi_laut.run(). Job ini memasukkan 9 titik
    grid zona_rekomendasi ke DB. Karena fixture clean_db (autouse) berjalan SEBELUM client,
    data dari job tersebut tidak ikut ter-bersihkan. Oleh karena itu, setelah TestClient dibuat,
    kita bersihkan ulang seluruh tabel + seed ulang stasiun kondisi laut default agar setiap test
    dimulai dari state yang bersih dan deterministik.
    """
    def override_get_db():
        try:
            yield db
        finally:
            pass
            
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        # Bersihkan ulang data yang mungkin dimasukkan oleh job refresh saat startup lifespan
        db.execute(text("TRUNCATE TABLE trip_bbm, titik_favorit, sos_signal, push_token, laporan_tangkapan, nelayan, zona_satelit, zona_rekomendasi, kondisi_laut CASCADE;"))
        db.commit()

        # Seed ulang kondisi_laut stasiun default agar endpoint kondisi-laut tidak kosong
        from models.kondisi_laut import KondisiLaut
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

        yield c
    app.dependency_overrides.clear()
