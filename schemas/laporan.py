import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class LaporanTeksCreate(BaseModel):
    nelayan_id: Optional[uuid.UUID] = None
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    jenis_ikan: Optional[str] = None
    estimasi_kg: Optional[float] = Field(None, ge=0)
    catatan: Optional[str] = None

class LaporanSuaraOut(BaseModel):
    id: uuid.UUID
    jenis_ikan: Optional[str] = None
    estimasi_kg: Optional[float] = None
    catatan: Optional[str] = None
    perlu_review: bool

    model_config = {
        "from_attributes": True
    }

class LaporanOut(BaseModel):
    id: uuid.UUID
    nelayan_id: Optional[uuid.UUID] = None
    lat: float
    lng: float
    jenis_ikan: Optional[str] = None
    estimasi_kg: Optional[float] = None
    catatan: Optional[str] = None
    perlu_review: bool
    waktu: datetime
    synced: bool

    model_config = {
        "from_attributes": True
    }

class LaporanBatchItem(BaseModel):
    id: Optional[uuid.UUID] = None
    nelayan_id: Optional[uuid.UUID] = None
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    jenis_ikan: Optional[str] = None
    estimasi_kg: Optional[float] = Field(None, ge=0)
    catatan: Optional[str] = None
    perlu_review: Optional[bool] = None
    waktu: Optional[datetime] = None

class LaporanBatchRequest(BaseModel):
    laporan: List[LaporanBatchItem]
