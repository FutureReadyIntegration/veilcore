def test_organs_health_surface_exists():
    """There should be a way to query organ health via orchestrator or core."""
    import veil.orchestrator as orchestrator

    assert hasattr(orchestrator, "organ_health")
