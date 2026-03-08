import pytest
from veil.organs.telemetry import TelemetryOrgan
from veil.organ_base import OrganConfig

@pytest.fixture
def organ():
    return TelemetryOrgan(OrganConfig(name="telemetry"))

def test_collector_runs_all_checks(organ):
    pass

def test_collector_handles_exceptions(organ):
    pass
