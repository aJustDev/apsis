"""Servicio puro de propagacion SGP4.

Sin side-effects, sin IO de red ni BD. Recibe un TLE (dos lineas) e
instantes tz-aware en UTC y devuelve el punto sub-satelite (lat, lon,
altura) en cada instante. La carga del TLE la hace el use_case o el job;
aqui solo se propaga. skyfield es sincrono y CPU-bound: el caller lo
ejecuta via `run_blocking`.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from skyfield.api import wgs84

from app.tracking.services._skyfield import build_satellite, timescale


@dataclass(frozen=True, slots=True)
class GeodeticPoint:
    at: datetime
    latitude: float
    longitude: float
    altitude_km: float


def tle_epoch(*, line1: str, line2: str) -> datetime:
    """Epoch del TLE como datetime tz-aware en UTC."""
    satellite = build_satellite(line1, line2)
    epoch: datetime = satellite.epoch.utc_datetime()
    return epoch


def tle_norad_id(*, line1: str) -> int:
    """Numero de catalogo NORAD leido de la linea 1 del TLE (columnas 3-7)."""
    return int(line1[2:7])


def subpoints(
    *, line1: str, line2: str, instants: Sequence[datetime]
) -> list[GeodeticPoint]:
    if not instants:
        raise ValueError("instants must not be empty")
    if any(instant.tzinfo is None for instant in instants):
        raise ValueError("instants must be timezone-aware (UTC)")

    satellite = build_satellite(line1, line2)
    times = timescale().from_datetimes(list(instants))
    subpoint = wgs84.subpoint(satellite.at(times))
    latitudes = subpoint.latitude.degrees
    longitudes = subpoint.longitude.degrees
    altitudes_km = subpoint.elevation.km
    return [
        GeodeticPoint(
            at=instant,
            latitude=float(latitude),
            longitude=float(longitude),
            altitude_km=float(altitude),
        )
        for instant, latitude, longitude, altitude in zip(
            instants, latitudes, longitudes, altitudes_km, strict=True
        )
    ]


__all__ = ["GeodeticPoint", "subpoints", "tle_epoch", "tle_norad_id"]
