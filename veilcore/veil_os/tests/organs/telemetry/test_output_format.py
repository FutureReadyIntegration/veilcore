def test_telemetry_output_format_is_structured():
    """Telemetry output should be structured as dicts or serializable records."""
    import veil.telemetry as telemetry

    assert hasattr(telemetry, "collect_metrics")
    records = telemetry.collect_metrics()
    assert isinstance(records, (list, tuple))
    assert all(isinstance(r, dict) for r in records)
