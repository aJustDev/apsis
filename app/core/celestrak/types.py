from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TleRecord:
    """Un registro TLE de 3 lineas tal y como lo sirve CelesTrak."""

    name: str
    line1: str
    line2: str
