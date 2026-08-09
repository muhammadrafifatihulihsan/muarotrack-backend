import uuid
from datetime import datetime
from sqlalchemy import text, func, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geography
from db.base import Base

class SosSignal(Base):
    __tablename__ = "sos_signal"
    
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
    pesan: Mapped[str] = mapped_column(nullable=True)
    waktu_kejadian: Mapped[datetime] = mapped_column(nullable=False)
    waktu_terkirim: Mapped[datetime] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(default="tertunda", server_default=text("'tertunda'"))
    dibuat_pada: Mapped[datetime] = mapped_column(server_default=func.now())

    nelayan = relationship("Nelayan", backref="sos_signal")

class PushToken(Base):
    __tablename__ = "push_token"
    
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
    expo_push_token: Mapped[str] = mapped_column(nullable=False, unique=True)
    diperbarui_pada: Mapped[datetime] = mapped_column(server_default=func.now())

    nelayan = relationship("Nelayan", backref="push_token")
