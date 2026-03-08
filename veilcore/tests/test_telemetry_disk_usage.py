import pytest
from veil.organs.telemetry import TelemetryOrgan
from veil.organ_base import OrganConfig

@pytest.fixture
def organ():
    return TelemetryOrgan(OrganConfig(name="telemetry"))

def test_disk_usage_reports_expected_fields(organ):
    pass

def test_disk_usage_handles_errors(organ):
    pass
