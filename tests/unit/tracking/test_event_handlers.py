def test_recompute_passes_is_registered_for_tle_refreshed() -> None:
    import app.tracking.event_handlers.recompute_passes  # noqa: F401
    from app.core.events.dispatcher import dispatcher

    assert "tle.refreshed" in dispatcher.registered_events
