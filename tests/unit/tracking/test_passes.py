from datetime import UTC, datetime, timedelta

import pytest

from app.tracking.services.passes import ObserverSite, SatellitePass, compute_passes

ISS_LINE1 = "1 25544U 98067A   24001.50000000  .00016717  00000-0  10270-3 0  9000"
ISS_LINE2 = "2 25544  51.6400 208.0000 0006703 130.0000 325.0000 15.50000000    07"
MADRID = ObserverSite(latitude=40.4168, longitude=-3.7038, elevation_m=667.0)


def test_compute_passes_over_madrid_in_24h() -> None:
    start = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
    window = (start, start + timedelta(days=1))
    passes = compute_passes(line1=ISS_LINE1, line2=ISS_LINE2, observer=MADRID, window=window)

    assert passes  # al menos un paso en 24h
    for sat_pass in passes:
        assert isinstance(sat_pass, SatellitePass)
        assert sat_pass.aos_at < sat_pass.peak_at < sat_pass.los_at
        assert sat_pass.peak_elevation_deg >= 10.0
        assert len(sat_pass.ground_track) == 24
        lon, lat = sat_pass.ground_track[0]
        assert -180.0 <= lon <= 180.0
        assert -90.0 <= lat <= 90.0

    aos_times = [sat_pass.aos_at for sat_pass in passes]
    assert aos_times == sorted(aos_times)


def test_window_must_be_tz_aware() -> None:
    window = (datetime(2024, 1, 1), datetime(2024, 1, 2))
    with pytest.raises(ValueError, match="timezone-aware"):
        compute_passes(line1=ISS_LINE1, line2=ISS_LINE2, observer=MADRID, window=window)


def test_min_elevation_out_of_range() -> None:
    window = (
        datetime(2024, 1, 1, tzinfo=UTC),
        datetime(2024, 1, 2, tzinfo=UTC),
    )
    with pytest.raises(ValueError, match="min_elevation_deg"):
        compute_passes(
            line1=ISS_LINE1,
            line2=ISS_LINE2,
            observer=MADRID,
            window=window,
            min_elevation_deg=95.0,
        )
