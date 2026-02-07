import pytest
from veil.organs.telemetry import TelemetryOrgan
from veil.organ_base import OrganConfig

@pytest.fixture
def organ():
    return TelemetryOrgan(OrganConfig(name="telemetry"))

def test_event_emitter_sends_event(organ):
    pass

def test_event_emitter_handles_failure(organ):
    pass
