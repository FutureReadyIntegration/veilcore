def test_core_imports_and_eventbus_present():
    """Core should import and expose an event bus or messaging primitive."""
    import veil.core as core

    assert hasattr(core, "eventbus")
