from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from core.deps import get_db
from models.nelayan import Nelayan
from schemas.nelayan import NelayanCreate, NelayanOut

router = APIRouter(prefix="/nelayan", tags=["Nelayan"])

@router.post("", response_model=NelayanOut, status_code=status.HTTP_201_CREATED)
def daftar_nelayan(schema: NelayanCreate, db: Session = Depends(get_db)):
    """
    Registrasi nelayan baru dan hitung rata-rata konsumsi bahan bakar (BBM) per kilometer kapal.
    """
    # Hitung konsumsi bbm per km: total_liter / jarak_km
    if schema.jarak_km_biasa <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Jarak perjalanan rata-rata harus lebih besar dari 0"
        )
    
    konsumsi = schema.total_liter_biasa / schema.jarak_km_biasa
    
    nelayan = Nelayan(
        nama=schema.nama,
        konsumsi_bbm_per_km=round(konsumsi, 4)
    )
    
    db.add(nelayan)
    db.commit()
    db.refresh(nelayan)
    return nelayan
