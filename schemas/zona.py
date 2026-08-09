import uuid
from datetime import datetime
from typing import List, Dict, Optional
from pydantic import BaseModel


class ZonaRekomendasiOut(BaseModel):
    id: uuid.UUID
    lat: float
    lng: float
    skor: float
    detail_skor: Dict[str, float]
    dihitung_pada: datetime

    # Field tambahan: efisiensi BBM/waktu & penanda sedimen pasca-banjir
    jarak_km: Optional[float] = None            # jarak dari posisi nelayan ke titik zona
    estimasi_bbm_liter: Optional[float] = None  # prediksi BBM pulang-pergi (jarak x konsumsi x 2)
    peringkat: Optional[int] = None             # urutan rekomendasi (1 = paling disarankan)
    skor_efektif: Optional[float] = None        # skor setelah mempertimbangkan jarak/BBM
    terdampak_sedimen: Optional[bool] = False   # penanda area sedimen pasca-banjir
    catatan_sedimen: Optional[str] = None       # penjelasan jika terdampak sedimen

    model_config = {
        "from_attributes": True
    }


class ZonaRekomendasiListResponse(BaseModel):
    zonas: List[ZonaRekomendasiOut]