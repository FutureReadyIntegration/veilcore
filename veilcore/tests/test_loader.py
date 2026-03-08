def test_loader_imports_and_can_enumerate_organs():
    """Loader should import and expose a way to enumerate loadable organs."""
    import veil.loader as loader

    assert hasattr(loader, "discover_organs")
    assert callable(loader.discover_organs)
