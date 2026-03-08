def test_registry_imports_and_has_entrypoints():
    """Registry module should import and expose organ registration primitives."""
    import veil.registry as registry

    assert hasattr(registry, "get_registered_organs")
    assert callable(registry.get_registered_organs)
