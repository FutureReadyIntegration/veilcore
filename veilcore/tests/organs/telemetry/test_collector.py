def test_telemetry_collector_interface_exists():
    """Telemetry organ should expose a collector entrypoint."""
    import veil.telemetry as telemetry

    assert hasattr(telemetry, "collect")
    assert callable(telemetry.collect)
