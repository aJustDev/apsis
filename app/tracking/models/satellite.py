from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TimestampsMixin, UUIDPkMixin


class SatelliteORM(UUIDPkMixin, TimestampsMixin, Base):
    __tablename__ = "satellites"
    __table_args__ = (Index("ix_satellites_name", "name"),)

    norad_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tle_line1: Mapped[str] = mapped_column(Text, nullable=False)
    tle_line2: Mapped[str] = mapped_column(Text, nullable=False)
    epoch: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
