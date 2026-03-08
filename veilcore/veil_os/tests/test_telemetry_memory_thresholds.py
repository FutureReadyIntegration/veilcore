import pytest
from veil.organs.telemetry import TelemetryOrgan
from veil.organ_base import OrganConfig

@pytest.fixture
def organ():
    return TelemetryOrgan(OrganConfig(name="telemetry"))

def test_memory_warning_threshold(organ):
    pass

def test_memory_critical_threshold(organ):
    pass
