import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class TitikFavoritCreate(BaseModel):
    nelayan_id: uuid.UUID
    nama_label: str = Field(..., min_length=1)
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    catatan: Optional[str] = None
    laporan_tangkapan_id: Optional[uuid.UUID] = None

class TitikFavoritOut(BaseModel):
    id: uuid.UUID
    nelayan_id: uuid.UUID
    nama_label: str
    lat: float
    lng: float
    catatan: Optional[str]
    laporan_tangkapan_id: Optional[uuid.UUID]
    dibuat_pada: datetime
    synced: bool

    model_config = {
        "from_attributes": True
    }
