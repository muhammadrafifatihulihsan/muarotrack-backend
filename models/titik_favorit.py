import uuid
from datetime import datetime
from sqlalchemy import text, func, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geography
from db.base import Base

class TitikFavorit(Base):
    __tablename__ = "titik_favorit"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4, 
        server_default=text("gen_random_uuid()")
    )
    nelayan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("nelayan.id", ondelete="CASCADE"), 
        nullable=False
    )
    nama_label: Mapped[str] = mapped_column(nullable=False)
    lokasi = mapped_column(
        Geography(geometry_type="POINT", srid=4326), 
        nullable=False
    )
    catatan: Mapped[str] = mapped_column(nullable=True)
    laporan_tangkapan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("laporan_tangkapan.id", ondelete="SET NULL"), 
        nullable=True
    )
    dibuat_pada: Mapped[datetime] = mapped_column(server_default=func.now())
    synced: Mapped[bool] = mapped_column(default=True, server_default=text("true"))

    nelayan = relationship("Nelayan", backref="titik_favorit")
    laporan_tangkapan = relationship("LaporanTangkapan", backref="titik_favorit")
