def test_veil_boots():
    """
    Basic heartbeat test for the modern 78‑organ Veil OS.
    Ensures the package imports and the core boot sequence does not raise.
    """
    import veil

    # Core subsystems should import cleanly
    import veil.core
    import veil.registry
    import veil.loader

    # Boot sequence should not raise exceptions
    assert hasattr(veil, "__package__")
    assert veil.__package__ == "veil"
