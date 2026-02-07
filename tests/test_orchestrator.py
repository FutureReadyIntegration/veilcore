def test_orchestrator_imports_and_has_status():
    """Orchestrator should import and expose a status or health surface."""
    import veil.orchestrator as orchestrator

    assert hasattr(orchestrator, "status")
