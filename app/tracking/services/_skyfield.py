"""Helpers de skyfield compartidos por los servicios de tracking.

Aislan la construccion del Timescale (efemerides empaquetadas, sin red) y
del EarthSatellite a partir de un TLE, para que `propagation` y `passes`
no dupliquen el setup ni dependan de la API de skyfield directamente.
"""

from functools import lru_cache

from skyfield.api import EarthSatellite, load
from skyfield.timelib import Timescale


@lru_cache(maxsize=1)
def timescale() -> Timescale:
    # builtin=True por defecto: carga iers.npz empaquetado, sin acceso a red.
    return load.timescale()


def build_satellite(line1: str, line2: str) -> EarthSatellite:
    return EarthSatellite(line1, line2, ts=timescale())


__all__ = ["build_satellite", "timescale"]
