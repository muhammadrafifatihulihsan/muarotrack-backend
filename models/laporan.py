import uuid
from datetime import datetime
from sqlalchemy import text, func, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geography
from db.base import Base

class LaporanTangkapan(Base):
    __tablename__ = "laporan_tangkapan"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4, 
        server_default=text("gen_random_uuid()")
    )
    nelayan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("nelayan.id", ondelete="SET NULL"), 
        nullable=True
    )
    lokasi = mapped_column(
        Geography(geometry_type="POINT", srid=4326), 
        nullable=False
    )
    jenis_ikan: Mapped[str] = mapped_column(nullable=True)
    estimasi_kg: Mapped[float] = mapped_column(nullable=True)
    catatan: Mapped[str] = mapped_column(nullable=True)
    perlu_review: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    waktu: Mapped[datetime] = mapped_column(server_default=func.now())
    synced: Mapped[bool] = mapped_column(default=True, server_default=text("true"))

    nelayan = relationship("Nelayan", backref="laporan_tangkapan")
