import uuid
from datetime import datetime
from sqlalchemy import text, func, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.base import Base

class TripBbm(Base):
    __tablename__ = "trip_bbm"
    
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
    jarak_km: Mapped[float] = mapped_column(nullable=False)
    prediksi_liter: Mapped[float] = mapped_column(nullable=False)
    liter_aktual: Mapped[float] = mapped_column(nullable=True)
    waktu: Mapped[datetime] = mapped_column(server_default=func.now())

    nelayan = relationship("Nelayan", backref="trip_bbm")
