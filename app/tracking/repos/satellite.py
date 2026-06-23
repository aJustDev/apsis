from sqlalchemy import select

from app.core.repo import BaseRepo
from app.tracking.models import SatelliteORM


class SatelliteRepo(BaseRepo[SatelliteORM]):
    model = SatelliteORM

    async def get_by_norad_id(self, norad_id: int) -> SatelliteORM | None:
        stmt = select(SatelliteORM).where(SatelliteORM.norad_id == norad_id)
        return (await self.session.execute(stmt)).scalars().first()

    async def list_all(self) -> list[SatelliteORM]:
        stmt = select(SatelliteORM).order_by(SatelliteORM.name)
        return list((await self.session.execute(stmt)).scalars().all())
