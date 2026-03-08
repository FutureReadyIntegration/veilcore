import pytest
from veil.organs.telemetry import TelemetryOrgan
from veil.organ_base import OrganConfig

@pytest.fixture
def organ():
    return TelemetryOrgan(OrganConfig(name="telemetry"))

def test_process_metrics_reports_expected_fields(organ):
    pass

def test_process_metrics_handles_errors(organ):
    pass
