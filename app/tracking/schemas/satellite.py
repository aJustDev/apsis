import uuid
from datetime import datetime

from app.core.schema import BaseSchema


class SatelliteRead(BaseSchema):
    id: uuid.UUID
    norad_id: int
    name: str
    epoch: datetime
    created_at: datetime
    updated_at: datetime | None


class SatelliteListResponse(BaseSchema):
    items: list[SatelliteRead]
    total: int
    limit: int
    offset: int
