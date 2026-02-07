def test_affirmations_module_imports():
    """Affirmations module should import for organ-level metadata and rituals."""
    import veil.affirmations as affirmations

    assert hasattr(affirmations, "__package__")
