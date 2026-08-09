import uuid
from datetime import datetime
from pydantic import BaseModel, Field, field_validator

class NelayanBase(BaseModel):
    nama: str

class NelayanCreate(NelayanBase):
    total_liter_biasa: float = Field(..., gt=0, description="Konsumsi liter bahan bakar biasanya")
    jarak_km_biasa: float = Field(..., gt=0, description="Jarak perjalanan biasanya dalam km")

    @field_validator("jarak_km_biasa")
    @classmethod
    def validate_jarak(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Jarak perjalanan harus lebih besar dari 0")
        return v

class NelayanOut(NelayanBase):
    id: uuid.UUID
    konsumsi_bbm_per_km: float
    created_at: datetime

    model_config = {
        "from_attributes": True
    }
