def test_telemetry_thresholds_interface_exists():
    """Telemetry organ should expose a way to evaluate metric thresholds."""
    import veil.telemetry as telemetry

    assert hasattr(telemetry, "evaluate_thresholds")
    assert callable(telemetry.evaluate_thresholds)
