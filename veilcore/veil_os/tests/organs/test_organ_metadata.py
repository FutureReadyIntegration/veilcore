def test_organ_metadata_module_imports():
    """Organ metadata module should import and expose lookup primitives."""
    import veil.organ_metadata as organ_metadata

    assert hasattr(organ_metadata, "get_organ_spec")
