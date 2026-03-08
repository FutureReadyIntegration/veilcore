def test_telemetry_emitter_interface_exists():
    """Telemetry organ should expose an event emission interface."""
    import veil.telemetry as telemetry

    assert hasattr(telemetry, "emit")
    assert callable(telemetry.emit)
