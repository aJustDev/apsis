"""Servicio puro de calculo de pasos.

Sin side-effects, sin IO. Dado un TLE, un observador y una ventana
temporal tz-aware, devuelve los pasos COMPLETOS (rise -> culminate ->
set) por encima de `min_elevation_deg`, con su elevacion maxima y el
ground-track muestreado. Los pasos recortados por el borde de la ventana
se descartan: aos/los/peak son obligatorios. skyfield es sincrono y
CPU-bound: el caller lo ejecuta via `run_blocking`.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from skyfield.api import wgs84

from app.tracking.services._skyfield import build_satellite, timescale
from app.tracking.services.propagation import subpoints

_RISE, _CULMINATE, _SET = 0, 1, 2


@dataclass(frozen=True, slots=True)
class ObserverSite:
    latitude: float
    longitude: float
    elevation_m: float = 0.0


@dataclass(frozen=True, slots=True)
class SatellitePass:
    aos_at: datetime
    los_at: datetime
    peak_at: datetime
    peak_elevation_deg: float
    ground_track: tuple[tuple[float, float], ...]  # (lon, lat) en WGS84


def compute_passes(
    *,
    line1: str,
    line2: str,
    observer: ObserverSite,
    window: tuple[datetime, datetime],
    min_elevation_deg: float = 10.0,
    track_samples: int = 24,
) -> list[SatellitePass]:
    start, end = window
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("window bounds must be timezone-aware (UTC)")
    if start >= end:
        raise ValueError("window start must be earlier than end")
    if not 0.0 < min_elevation_deg < 90.0:
        raise ValueError("min_elevation_deg must be in (0, 90)")
    if track_samples < 2:
        raise ValueError("track_samples must be at least 2")

    ts = timescale()
    satellite = build_satellite(line1, line2)
    topos = wgs84.latlon(observer.latitude, observer.longitude, elevation_m=observer.elevation_m)

    times, events = satellite.find_events(
        topos, ts.from_datetime(start), ts.from_datetime(end), altitude_degrees=min_elevation_deg
    )

    passes: list[SatellitePass] = []
    aos_at: datetime | None = None
    peak_time: Any = None
    for event_time, event in zip(times, events, strict=True):
        code = int(event)
        if code == _RISE:
            aos_at = event_time.utc_datetime()
            peak_time = None
        elif code == _CULMINATE and aos_at is not None:
            peak_time = event_time
        elif code == _SET and aos_at is not None and peak_time is not None:
            passes.append(
                _build_pass(
                    line1=line1,
                    line2=line2,
                    topos=topos,
                    aos_at=aos_at,
                    peak_time=peak_time,
                    los_at=event_time.utc_datetime(),
                    track_samples=track_samples,
                )
            )
            aos_at = None
            peak_time = None
        elif code == _SET:
            aos_at = None
            peak_time = None
    return passes


def _build_pass(
    *,
    line1: str,
    line2: str,
    topos: Any,
    aos_at: datetime,
    peak_time: Any,
    los_at: datetime,
    track_samples: int,
) -> SatellitePass:
    satellite = build_satellite(line1, line2)
    altitude, _azimuth, _distance = (satellite - topos).at(peak_time).altaz()
    instants = _sample_instants(aos_at, los_at, track_samples)
    track = subpoints(line1=line1, line2=line2, instants=instants)
    return SatellitePass(
        aos_at=aos_at,
        los_at=los_at,
        peak_at=peak_time.utc_datetime(),
        peak_elevation_deg=float(altitude.degrees),
        ground_track=tuple((point.longitude, point.latitude) for point in track),
    )


def _sample_instants(start: datetime, end: datetime, count: int) -> list[datetime]:
    span = (end - start) / (count - 1)
    return [start + span * step for step in range(count)]


__all__ = ["ObserverSite", "SatellitePass", "compute_passes"]
