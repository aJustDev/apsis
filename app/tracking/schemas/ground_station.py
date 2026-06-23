import uuid
from datetime import datetime

from pydantic import Field

from app.core.schema import BaseSchema


class GroundStationCreate(BaseSchema):
    name: str = Field(min_length=1, max_length=255)
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    altitude_m: float = Field(default=0.0, ge=-500.0, le=100_000.0)


class GroundStationRead(BaseSchema):
    id: uuid.UUID
    name: str
    latitude: float
    longitude: float
    altitude_m: float
    created_at: datetime
    updated_at: datetime | None


class GroundStationListResponse(BaseSchema):
    items: list[GroundStationRead]
    total: int
