import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class TripBbmCreate(BaseModel):
    nelayan_id: uuid.UUID
    jarak_km: float = Field(..., gt=0)
    prediksi_liter: float = Field(..., gt=0)
    liter_aktual: Optional[float] = Field(None, ge=0)

class TripBbmOut(BaseModel):
    id: uuid.UUID
    nelayan_id: uuid.UUID
    jarak_km: float
    prediksi_liter: float
    liter_aktual: Optional[float]
    waktu: datetime

    model_config = {
        "from_attributes": True
    }
