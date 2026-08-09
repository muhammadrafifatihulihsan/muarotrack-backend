from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.deps import get_db
from schemas.laporan import LaporanBatchRequest, LaporanOut
from routers.laporan import laporan_batch

router = APIRouter(prefix="/sync", tags=["Sinkronisasi Offline"])

@router.post("/laporan-batch", response_model=List[LaporanOut])
def sync_laporan_batch(schema: LaporanBatchRequest, db: Session = Depends(get_db)):
    """
    Sinkronisasi massal untuk laporan offline nelayan (delegasi ke endpoint laporan).
    """
    return laporan_batch(schema, db)
