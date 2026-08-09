from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from core.deps import get_db
from models.trip_bbm import TripBbm
from schemas.trip_bbm import TripBbmCreate, TripBbmOut

router = APIRouter(prefix="/trip-bbm", tags=["Trip BBM"])

@router.post("", response_model=TripBbmOut, status_code=status.HTTP_201_CREATED)
def trip_bbm_create(schema: TripBbmCreate, db: Session = Depends(get_db)):
    """
    Mencatat data prediksi kebutuhan BBM per kapal nelayan versus data realisasi aktual di lapangan.
    """
    trip = TripBbm(
        nelayan_id=schema.nelayan_id,
        jarak_km=schema.jarak_km,
        prediksi_liter=schema.prediksi_liter,
        liter_aktual=schema.liter_aktual
    )
    
    db.add(trip)
    db.commit()
    db.refresh(trip)
    return trip
