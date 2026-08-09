import uuid
from datetime import datetime
from sqlalchemy import text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from geoalchemy2 import Geography
from db.base import Base

class ZonaSatelit(Base):
    __tablename__ = "zona_satelit"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4, 
        server_default=text("gen_random_uuid()")
    )
    lokasi = mapped_column(
        Geography(geometry_type="POINT", srid=4326), 
        nullable=False
    )
    sst: Mapped[float] = mapped_column(nullable=True)
    klorofil: Mapped[float] = mapped_column(nullable=True)
    turbiditas_ndti: Mapped[float] = mapped_column(nullable=True)
    diperbarui_pada: Mapped[datetime] = mapped_column(server_default=func.now())

class ZonaRekomendasi(Base):
    __tablename__ = "zona_rekomendasi"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4, 
        server_default=text("gen_random_uuid()")
    )
    lokasi = mapped_column(
        Geography(geometry_type="POINT", srid=4326), 
        nullable=False
    )
    skor: Mapped[float] = mapped_column(nullable=False)
    detail_skor: Mapped[dict] = mapped_column(JSONB, nullable=True)
    dihitung_pada: Mapped[datetime] = mapped_column(server_default=func.now())
