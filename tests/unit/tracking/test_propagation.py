from datetime import UTC, datetime, timedelta

import pytest

from app.tracking.services.propagation import subpoints, tle_epoch, tle_norad_id

ISS_LINE1 = "1 25544U 98067A   24001.50000000  .00016717  00000-0  10270-3 0  9000"
ISS_LINE2 = "2 25544  51.6400 208.0000 0006703 130.0000 325.0000 15.50000000    07"


def test_tle_epoch_is_utc_aware() -> None:
    epoch = tle_epoch(line1=ISS_LINE1, line2=ISS_LINE2)
    expected = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    assert epoch.tzinfo is not None
    assert abs((epoch - expected).total_seconds()) < 1.0


def test_subpoints_returns_a_point_per_instant_in_range() -> None:
    base = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    instants = [base + timedelta(minutes=minute) for minute in range(0, 10, 2)]
    track = subpoints(line1=ISS_LINE1, line2=ISS_LINE2, instants=instants)
    assert len(track) == len(instants)
    for point in track:
        assert -90.0 <= point.latitude <= 90.0
        assert -180.0 <= point.longitude <= 180.0
        assert 300.0 < point.altitude_km < 600.0  # orbita baja tipica de la ISS


def test_subpoints_rejects_naive_datetimes() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        subpoints(line1=ISS_LINE1, line2=ISS_LINE2, instants=[datetime(2024, 1, 1, 12, 0)])


def test_subpoints_rejects_empty() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        subpoints(line1=ISS_LINE1, line2=ISS_LINE2, instants=[])


def test_tle_norad_id_parses_catalog_number() -> None:
    assert tle_norad_id(line1=ISS_LINE1) == 25544
