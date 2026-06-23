from sqlalchemy import select

from app.core.repo import BaseRepo
from app.tracking.models import GroundStationORM


class GroundStationRepo(BaseRepo[GroundStationORM]):
    model = GroundStationORM

    async def get_by_name(self, name: str) -> GroundStationORM | None:
        stmt = select(GroundStationORM).where(GroundStationORM.name == name)
        return (await self.session.execute(stmt)).scalars().first()

    async def list_all(self) -> list[GroundStationORM]:
        stmt = select(GroundStationORM).order_by(GroundStationORM.name)
        return list((await self.session.execute(stmt)).scalars().all())
