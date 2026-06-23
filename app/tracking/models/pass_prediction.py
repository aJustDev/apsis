import uuid
from datetime import datetime

from geoalchemy2 import Geometry, WKBElement
from sqlalchemy import DateTime, Float, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TimestampsMixin, UUIDPkMixin


class PassPredictionORM(UUIDPkMixin, TimestampsMixin, Base):
    __tablename__ = "pass_predictions"
    __table_args__ = (
        UniqueConstraint(
            "satellite_id",
            "ground_station_id",
            "aos_at",
            name="uq_pass_predictions_sat_station_aos",
        ),
        Index("ix_pass_predictions_ground_station_id_aos_at", "ground_station_id", "aos_at"),
    )

    satellite_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("satellites.id", ondelete="CASCADE"),
        nullable=False,
    )
    ground_station_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ground_stations.id", ondelete="CASCADE"),
        nullable=False,
    )
    aos_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    los_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    peak_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    peak_elevation_deg: Mapped[float] = mapped_column(Float, nullable=False)
    # Sub-satellite ground track during the pass (WGS84 line).
    track: Mapped[WKBElement] = mapped_column(
        Geometry(geometry_type="LINESTRING", srid=4326, spatial_index=True),
        nullable=False,
    )
