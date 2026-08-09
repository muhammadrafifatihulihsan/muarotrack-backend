import uuid
from datetime import datetime
from sqlalchemy import text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from db.base import Base

class Nelayan(Base):
    __tablename__ = "nelayan"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4, 
        server_default=text("gen_random_uuid()")
    )
    nama: Mapped[str] = mapped_column(nullable=False)
    konsumsi_bbm_per_km: Mapped[float] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
