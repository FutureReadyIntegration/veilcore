def test_glyphs_module_imports():
    """Glyphs module should import to support symbolic overlays and UI lineage."""
    import veil.glyphs as glyphs

    assert hasattr(glyphs, "__package__")
