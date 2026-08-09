import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class KondisiLautOut(BaseModel):
    id: uuid.UUID
    lat: float
    lng: float
    diperbarui_pada: datetime
    gelombang_gabungan: Optional[List[Dict[str, Any]]] = []
    gelombang_angin: Optional[List[Dict[str, Any]]] = []
    gelombang_swell: Optional[List[Dict[str, Any]]] = []
    cuaca_per_jam: Optional[List[Dict[str, Any]]] = []
    pasang_surut: Optional[List[Dict[str, Any]]] = []

    model_config = {
        "from_attributes": True
    }
