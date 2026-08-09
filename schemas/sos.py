import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class SosCreate(BaseModel):
    nelayan_id: Optional[uuid.UUID] = None
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    pesan: Optional[str] = None
    waktu_kejadian: datetime = Field(default_factory=datetime.now)

class SosOut(BaseModel):
    id: uuid.UUID
    nelayan_id: Optional[uuid.UUID]
    lat: float
    lng: float
    pesan: Optional[str]
    waktu_kejadian: datetime
    waktu_terkirim: Optional[datetime]
    status: str
    dibuat_pada: datetime

    model_config = {
        "from_attributes": True
    }

class PushTokenCreate(BaseModel):
    nelayan_id: uuid.UUID
    expo_push_token: str = Field(..., min_length=1)
