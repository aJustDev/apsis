import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.deps.repository import get_repo
from app.tracking.models import GroundStationORM
from app.tracking.repos import GroundStationRepo, PassPredictionRepo, SatelliteRepo
from app.tracking.schemas import (
    GroundStationCreate,
    GroundStationListResponse,
    GroundStationRead,
    PassListResponse,
    PassRead,
)
from app.tracking.services.geometry import wkb_to_lonlat
from app.tracking.use_cases.get_ground_station_passes import GetGroundStationPassesUseCase
from app.tracking.use_cases.list_ground_stations import ListGroundStationsUseCase
from app.tracking.use_cases.register_ground_station import RegisterGroundStationUseCase

router = APIRouter(prefix="/ground-stations", tags=["Ground stations"])

GroundStationRepoDep = Annotated[GroundStationRepo, Depends(get_repo(GroundStationRepo))]
PassPredictionRepoDep = Annotated[PassPredictionRepo, Depends(get_repo(PassPredictionRepo))]
SatelliteRepoDep = Annotated[SatelliteRepo, Depends(get_repo(SatelliteRepo))]


def _to_read(station: GroundStationORM) -> GroundStationRead:
    longitude, latitude = wkb_to_lonlat(station.location)
    return GroundStationRead(
        id=station.id,
        name=station.name,
        latitude=latitude,
        longitude=longitude,
        altitude_m=station.altitude_m,
        created_at=station.created_at,
        updated_at=station.updated_at,
    )


@router.post("", response_model=GroundStationRead, status_code=201)
async def register_ground_station(
    body: GroundStationCreate, ground_station_repo: GroundStationRepoDep
):
    use_case = RegisterGroundStationUseCase(ground_station_repo=ground_station_repo)
    station = await use_case.execute(
        name=body.name,
        latitude=body.latitude,
        longitude=body.longitude,
        altitude_m=body.altitude_m,
    )
    return _to_read(station)


@router.get("", response_model=GroundStationListResponse)
async def list_ground_stations(ground_station_repo: GroundStationRepoDep):
    use_case = ListGroundStationsUseCase(ground_station_repo=ground_station_repo)
    stations = await use_case.execute()
    return GroundStationListResponse(
        items=[_to_read(station) for station in stations], total=len(stations)
    )


@router.get("/{ground_station_id}/passes", response_model=PassListResponse)
async def list_ground_station_passes(
    ground_station_id: uuid.UUID,
    ground_station_repo: GroundStationRepoDep,
    pass_prediction_repo: PassPredictionRepoDep,
    satellite_repo: SatelliteRepoDep,
    after: Annotated[datetime | None, Query()] = None,
):
    use_case = GetGroundStationPassesUseCase(
        ground_station_repo=ground_station_repo,
        pass_prediction_repo=pass_prediction_repo,
        satellite_repo=satellite_repo,
    )
    views = await use_case.execute(
        ground_station_id=ground_station_id, after=after or datetime.now(UTC)
    )
    return PassListResponse(
        items=[PassRead.model_validate(view) for view in views], total=len(views)
    )
