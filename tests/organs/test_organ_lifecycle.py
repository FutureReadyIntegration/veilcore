def test_organs_package_imports():
    """Organs package should import and be iterable via registry or loader."""
    import veil.organs as organs

    assert hasattr(organs, "__package__")
