from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from geoalchemy2.shape import to_shape
from core.deps import get_db
from models.kondisi_laut import KondisiLaut
from schemas.kondisi_laut import KondisiLautOut

router = APIRouter(prefix="/kondisi-laut", tags=["Kondisi Laut"])

@router.get("", response_model=KondisiLautOut)
def ambil_kondisi_laut(
    lat: float = Query(..., ge=-90, le=90, description="Latitude lokasi nelayan"),
    lng: float = Query(..., ge=-180, le=180, description="Longitude lokasi nelayan"),
    db: Session = Depends(get_db)
):
    """
    Mengambil data cache ramalan gelombang, cuaca, dan pasang surut terdekat dari lokasi nelayan.
    """
    # Titik referensi koordinat nelayan
    point_wkt = f"SRID=4326;POINT({lng} {lat})"
    
    # Query untuk mencari stasiun kondisi_laut terdekat menggunakan ST_Distance
    stasiun = db.query(KondisiLaut).order_by(
        func.ST_Distance(KondisiLaut.lokasi, point_wkt)
    ).first()
    
    if not stasiun:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data kondisi laut untuk area ini belum tersedia."
        )
        
    point = to_shape(stasiun.lokasi)
    return KondisiLautOut(
        id=stasiun.id,
        lat=point.y,
        lng=point.x,
        diperbarui_pada=stasiun.diperbarui_pada,
        gelombang_gabungan=stasiun.gelombang_gabungan,
        gelombang_angin=stasiun.gelombang_angin,
        gelombang_swell=stasiun.gelombang_swell,
        cuaca_per_jam=stasiun.cuaca_per_jam,
        pasang_surut=stasiun.pasang_surut
    )
