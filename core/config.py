import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # Model config to load from .env file
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    MOCK_EXTERNAL: bool = True
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/muarotrack"
    
    DEEPSEEK_API_KEY: str = ""
    TIDECHECK_API_KEY: str = ""
    WORLDTIDES_API_KEY: str = ""
    GEE_PROJECT_ID: str = ""
    EXPO_ACCESS_TOKEN: str = ""
    
    WHISPER_MODEL_SIZE: str = "small"
    SOS_RADIUS_KM: float = 10.0
    
    # Konfigurasi grid zona rekomendasi dinamis (dari posisi nelayan)
    ZONA_RADIUS_MAKS_KM: float = 22.0   # radius maksimum pencarian (≈12 mil laut)
    ZONA_JUMLAH_TITIK: int = 5          # jumlah titik grid (dibatasi agar GEE cepat)
    BEARING_LAUT_DEG: float = 270.0     # arah laut dari posisi nelayan (default Barat, Padang)
    
    # Scheduler background jobs (false = matikan saat produksi berjalan multi-instance)
    RUN_SCHEDULER: bool = True

@lru_cache
def get_settings() -> Settings:
    return Settings()
