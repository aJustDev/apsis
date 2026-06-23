from geoalchemy2 import Geometry, WKBElement
from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TimestampsMixin, UUIDPkMixin


class GroundStationORM(UUIDPkMixin, TimestampsMixin, Base):
    __tablename__ = "ground_stations"

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    # WGS84 lon/lat point. spatial_index=True -> a GiST index is emitted.
    location: Mapped[WKBElement] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=True),
        nullable=False,
    )
    altitude_m: Mapped[float] = mapped_column(Float, nullable=False, server_default="0")
