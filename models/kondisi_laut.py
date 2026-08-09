import uuid
from datetime import datetime
from sqlalchemy import text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from geoalchemy2 import Geography
from db.base import Base

class KondisiLaut(Base):
    __tablename__ = "kondisi_laut"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4, 
        server_default=text("gen_random_uuid()")
    )
    lokasi = mapped_column(
        Geography(geometry_type="POINT", srid=4326), 
        nullable=False,
        unique=True
    )
    gelombang_gabungan: Mapped[list] = mapped_column(JSONB, nullable=True)
    gelombang_angin: Mapped[list] = mapped_column(JSONB, nullable=True)
    gelombang_swell: Mapped[list] = mapped_column(JSONB, nullable=True)
    cuaca_per_jam: Mapped[list] = mapped_column(JSONB, nullable=True)
    pasang_surut: Mapped[list] = mapped_column(JSONB, nullable=True)
    
    sumber_gelombang_cuaca: Mapped[str] = mapped_column(default="open-meteo", server_default=text("'open-meteo'"))
    sumber_pasut: Mapped[str] = mapped_column(default="tidecheck", server_default=text("'tidecheck'"))
    diperbarui_pada: Mapped[datetime] = mapped_column(server_default=func.now())
