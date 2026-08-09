from fastapi import APIRouter, Depends, Query, status, HTTPException
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from geoalchemy2.shape import to_shape
from core.deps import get_db
from models.sos import SosSignal, PushToken
from schemas.sos import SosCreate, SosOut, PushTokenCreate
from services.sos_dispatch import SosDispatch

router = APIRouter(tags=["Sinyal Darurat (SOS)"])
sos_dispatcher = SosDispatch()

@router.post("/sos", response_model=SosOut, status_code=status.HTTP_201_CREATED)
def sos_create(schema: SosCreate, db: Session = Depends(get_db)):
    """
    Mengirimkan sinyal darurat SOS baru dari lokasi nelayan saat ini.
    Memicu push notification darurat secara spasial ke nelayan terdekat.
    """
    lokasi_wkt = f"SRID=4326;POINT({schema.lng} {schema.lat})"
    
    # Simpan status awal 'tertunda'
    sos = SosSignal(
        nelayan_id=schema.nelayan_id,
        lokasi=lokasi_wkt,
        pesan=schema.pesan,
        waktu_kejadian=schema.waktu_kejadian,
        status="tertunda"
    )
    db.add(sos)
    db.commit()
    db.refresh(sos)
    
    # Kirim Push Notification ke nelayan sekitar secara async/sync
    notified_count = sos_dispatcher.notify_nearby(sos, db)
    
    # Update status ke 'terkirim'
    sos.status = "terkirim" if notified_count > 0 else "tertunda"
    sos.waktu_terkirim = datetime.now()
    db.commit()
    db.refresh(sos)
    
    point = to_shape(sos.lokasi)
    return SosOut(
        id=sos.id,
        nelayan_id=sos.nelayan_id,
        lat=point.y,
        lng=point.x,
        pesan=sos.pesan,
        waktu_kejadian=sos.waktu_kejadian,
        waktu_terkirim=sos.waktu_terkirim,
        status=sos.status,
        dibuat_pada=sos.dibuat_pada
    )

@router.get("/sos/aktif", response_model=List[SosOut])
def sos_aktif(
    lat: float = Query(..., ge=-90, le=90, description="Latitude GPS posisi nelayan"),
    lng: float = Query(..., ge=-180, le=180, description="Longitude GPS posisi nelayan"),
    radius_km: float = Query(10.0, gt=0, description="Radius jangkauan pencarian SOS"),
    db: Session = Depends(get_db)
):
    """
    Mengambil daftar sinyal darurat SOS yang masih aktif (status 'tertunda' atau 'terkirim')
    yang berada di sekitar radius nelayan untuk digambar di peta navigasi.
    """
    center_point = f"SRID=4326;POINT({lng} {lat})"
    
    # Query PostGIS: mencari SOS aktif dalam radius meter (radius_km * 1000)
    results = db.query(SosSignal).filter(
        SosSignal.status.in_(["tertunda", "terkirim"]),
        func.ST_DWithin(SosSignal.lokasi, center_point, radius_km * 1000.0)
    ).order_by(SosSignal.waktu_kejadian.desc()).all()
    
    sos_list = []
    for s in results:
        point = to_shape(s.lokasi)
        sos_list.append(SosOut(
            id=s.id,
            nelayan_id=s.nelayan_id,
            lat=point.y,
            lng=point.x,
            pesan=s.pesan,
            waktu_kejadian=s.waktu_kejadian,
            waktu_terkirim=s.waktu_terkirim,
            status=s.status,
            dibuat_pada=s.dibuat_pada
        ))
        
    return sos_list

@router.post("/push-token", status_code=status.HTTP_200_OK)
def push_token_upsert(schema: PushTokenCreate, db: Session = Depends(get_db)):
    """
    Mendaftarkan atau memperbarui Expo Push Token milik perangkat nelayan.
    Satu token unik hanya boleh dipetakan ke satu nelayan terdaftar.
    """
    # Cari jika token sudah terdaftar sebelumnya
    token_entry = db.query(PushToken).filter(PushToken.expo_push_token == schema.expo_push_token).first()
    
    if token_entry:
        token_entry.nelayan_id = schema.nelayan_id
        token_entry.diperbarui_pada = func.now()
    else:
        token_entry = PushToken(
            nelayan_id=schema.nelayan_id,
            expo_push_token=schema.expo_push_token
        )
        db.add(token_entry)
        
    db.commit()
    return {"status": "success", "message": "Push token berhasil didaftarkan/diperbarui"}
