import pytest
from veil.organs.telemetry import TelemetryOrgan
from veil.organ_base import OrganConfig

@pytest.fixture
def organ():
    return TelemetryOrgan(OrganConfig(name="telemetry"))

def test_output_format_is_valid_json(organ):
    pass

def test_output_format_includes_timestamp(organ):
    pass
