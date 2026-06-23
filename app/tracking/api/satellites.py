from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.deps.repository import get_repo
from app.tracking.repos import SatelliteRepo
from app.tracking.schemas import SatelliteListResponse, SatelliteRead
from app.tracking.use_cases.list_satellites import ListSatellitesUseCase

router = APIRouter(prefix="/satellites", tags=["Satellites"])

SatelliteRepoDep = Annotated[SatelliteRepo, Depends(get_repo(SatelliteRepo))]


@router.get("", response_model=SatelliteListResponse)
async def list_satellites(
    satellite_repo: SatelliteRepoDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    use_case = ListSatellitesUseCase(satellite_repo=satellite_repo)
    items, total = await use_case.execute(limit=limit, offset=offset)
    return SatelliteListResponse(
        items=[SatelliteRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )
