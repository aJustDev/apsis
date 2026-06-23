import uuid
from datetime import datetime

from sqlalchemy import delete, func, select

from app.core.repo import BaseRepo
from app.tracking.models import PassPredictionORM


class PassPredictionRepo(BaseRepo[PassPredictionORM]):
    model = PassPredictionORM

    async def list_for_ground_station(
        self, ground_station_id: uuid.UUID, *, after: datetime
    ) -> list[PassPredictionORM]:
        stmt = (
            select(PassPredictionORM)
            .where(
                PassPredictionORM.ground_station_id == ground_station_id,
                PassPredictionORM.aos_at >= after,
            )
            .order_by(PassPredictionORM.aos_at)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def delete_for_satellite_and_station(
        self, satellite_id: uuid.UUID, ground_station_id: uuid.UUID
    ) -> None:
        await self.session.execute(
            delete(PassPredictionORM).where(
                PassPredictionORM.satellite_id == satellite_id,
                PassPredictionORM.ground_station_id == ground_station_id,
            )
        )
        await self.session.flush()

    async def list_in_bbox(
        self, *, min_lon: float, min_lat: float, max_lon: float, max_lat: float
    ) -> list[PassPredictionORM]:
        # Passes whose ground track intersects the bbox (PostGIS GiST index on track).
        envelope = func.ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326)
        stmt = (
            select(PassPredictionORM)
            .where(PassPredictionORM.track.ST_Intersects(envelope))
            .order_by(PassPredictionORM.aos_at)
        )
        return list((await self.session.execute(stmt)).scalars().all())
