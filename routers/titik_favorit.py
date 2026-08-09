import uuid
from typing import List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from geoalchemy2.shape import to_shape
from core.deps import get_db
from models.titik_favorit import TitikFavorit
from schemas.titik_favorit import TitikFavoritCreate, TitikFavoritOut

router = APIRouter(prefix="/titik-favorit", tags=["Titik Favorit"])

@router.post("", response_model=TitikFavoritOut, status_code=status.HTTP_201_CREATED)
def simpan_titik_favorit(schema: TitikFavoritCreate, db: Session = Depends(get_db)):
    """
    Menyimpan lokasi koordinat kustom favorit pilihan nelayan.
    """
    lokasi_wkt = f"SRID=4326;POINT({schema.lng} {schema.lat})"
    titik = TitikFavorit(
        nelayan_id=schema.nelayan_id,
        nama_label=schema.nama_label,
        lokasi=lokasi_wkt,
        catatan=schema.catatan,
        laporan_tangkapan_id=schema.laporan_tangkapan_id,
        synced=True
    )
    
    db.add(titik)
    db.commit()
    db.refresh(titik)
    
    point = to_shape(titik.lokasi)
    return TitikFavoritOut(
        id=titik.id,
        nelayan_id=titik.nelayan_id,
        nama_label=titik.nama_label,
        lat=point.y,
        lng=point.x,
        catatan=titik.catatan,
        laporan_tangkapan_id=titik.laporan_tangkapan_id,
        dibuat_pada=titik.dibuat_pada,
        synced=titik.synced
    )

@router.get("", response_model=List[TitikFavoritOut])
def ambil_daftar_favorit(
    nelayan_id: uuid.UUID = Query(..., description="ID nelayan pemilik titik favorit"),
    db: Session = Depends(get_db)
):
    """
    Mengambil seluruh daftar titik koordinat favorit yang dimiliki oleh nelayan tertentu.
    """
    results = db.query(TitikFavorit).filter(TitikFavorit.nelayan_id == nelayan_id).all()
    
    fav_list = []
    for f in results:
        point = to_shape(f.lokasi)
        fav_list.append(TitikFavoritOut(
            id=f.id,
            nelayan_id=f.nelayan_id,
            nama_label=f.nama_label,
            lat=point.y,
            lng=point.x,
            catatan=f.catatan,
            laporan_tangkapan_id=f.laporan_tangkapan_id,
            dibuat_pada=f.dibuat_pada,
            synced=f.synced
        ))
        
    return fav_list
