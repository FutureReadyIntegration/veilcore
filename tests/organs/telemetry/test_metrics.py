def test_telemetry_metrics_module_imports():
    """Telemetry organ should import and expose metric collection primitives."""
    import veil.telemetry as telemetry

    assert hasattr(telemetry, "collect_metrics")
    assert callable(telemetry.collect_metrics)
