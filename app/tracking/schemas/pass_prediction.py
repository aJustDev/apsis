from datetime import datetime
from typing import Any

from app.core.schema import BaseSchema


class PassRead(BaseSchema):
    satellite_norad_id: int
    satellite_name: str
    aos_at: datetime
    los_at: datetime
    peak_at: datetime
    peak_elevation_deg: float
    # GeoJSON LineString of the sub-satellite ground track during the pass.
    track: dict[str, Any]


class PassListResponse(BaseSchema):
    items: list[PassRead]
    total: int
