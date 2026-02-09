"""
VeilCore Feature Extraction
============================
Transforms raw mesh events into numerical feature vectors for ML models.

Feature Categories:
    - Temporal: event rates, burst detection, time-of-day patterns
    - Behavioral: login patterns, access anomalies, session deviations
    - Network: connection counts, port diversity, traffic volume ratios
    - Clinical: Epic/FHIR/HL7/DICOM access patterns, PHI touch frequency
    - Escalation: alert density, organ error rates, response times

Each mesh event is converted to a fixed-width feature vector (48 features)
that feeds into both the anomaly detector and threat classifier.
"""

from __future__ import annotations

import math
import time
import logging
from collections import deque, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np

logger = logging.getLogger("veilcore.ml.features")

# Total feature vector width
FEATURE_DIM = 48

# Feature name registry (index → name) for interpretability
FEATURE_NAMES = [
    # Temporal (0-7)
    "events_per_sec_1min",
    "events_per_sec_5min",
    "events_per_sec_15min",
    "burst_score",
    "hour_of_day_sin",
    "hour_of_day_cos",
    "day_of_week_sin",
    "day_of_week_cos",
    # Behavioral (8-17)
    "failed_login_rate",
    "unique_users_1min",
    "unique_users_5min",
    "session_anomaly_score",
    "privilege_escalation_count",
    "after_hours_flag",
    "new_user_flag",
    "password_reset_rate",
    "mfa_failure_rate",
    "concurrent_sessions",
    # Network (18-27)
    "unique_src_ips_1min",
    "unique_dst_ips_1min",
    "unique_ports_1min",
    "bytes_in_rate",
    "bytes_out_rate",
    "in_out_ratio",
    "dns_query_rate",
    "internal_lateral_count",
    "external_connection_count",
    "port_scan_score",
    # Clinical (28-37)
    "epic_access_rate",
    "fhir_request_rate",
    "hl7_message_rate",
    "dicom_transfer_rate",
    "phi_access_count",
    "patient_record_diversity",
    "bulk_export_flag",
    "abnormal_query_pattern",
    "iomt_device_events",
    "clinical_off_hours_access",
    # Escalation (38-47)
    "threat_alert_rate",
    "organ_error_rate",
    "escalation_chain_length",
    "mean_response_time_ms",
    "p0_organ_offline_count",
    "dead_letter_rate",
    "hmac_failure_count",
    "rate_limit_hit_count",
    "quarantine_trigger_count",
    "overall_threat_score",
]

assert len(FEATURE_NAMES) == FEATURE_DIM, f"Expected {FEATURE_DIM} names, got {len(FEATURE_NAMES)}"


class RingBuffer:
    """Time-windowed event buffer for rate calculations."""

    def __init__(self, window_seconds: float = 60.0):
        self._window = window_seconds
        self._events: deque[float] = deque()

    def record(self, timestamp: Optional[float] = None) -> None:
        self._events.append(timestamp or time.monotonic())
        self._prune()

    def count(self) -> int:
        self._prune()
        return len(self._events)

    def rate(self) -> float:
        self._prune()
        if len(self._events) < 2:
            return float(len(self._events))
        elapsed = self._events[-1] - self._events[0]
        return len(self._events) / elapsed if elapsed > 0 else 0.0

    def _prune(self) -> None:
        cutoff = time.monotonic() - self._window
        while self._events and self._events[0] < cutoff:
            self._events.popleft()


class UniqueTracker:
    """Tracks unique values within a time window."""

    def __init__(self, window_seconds: float = 60.0):
        self._window = window_seconds
        self._entries: deque[tuple[float, str]] = deque()

    def record(self, value: str) -> None:
        self._entries.append((time.monotonic(), value))
        self._prune()

    def unique_count(self) -> int:
        self._prune()
        return len(set(v for _, v in self._entries))

    def _prune(self) -> None:
        cutoff = time.monotonic() - self._window
        while self._entries and self._entries[0][0] < cutoff:
            self._entries.popleft()


@dataclass
class FeatureState:
    """Mutable state that accumulates as mesh events arrive."""
    # Temporal
    event_buffer_1min: RingBuffer = field(default_factory=lambda: RingBuffer(60))
    event_buffer_5min: RingBuffer = field(default_factory=lambda: RingBuffer(300))
    event_buffer_15min: RingBuffer = field(default_factory=lambda: RingBuffer(900))

    # Behavioral
    failed_logins: RingBuffer = field(default_factory=lambda: RingBuffer(300))
    unique_users_1min: UniqueTracker = field(default_factory=lambda: UniqueTracker(60))
    unique_users_5min: UniqueTracker = field(default_factory=lambda: UniqueTracker(300))
    privilege_escalations: RingBuffer = field(default_factory=lambda: RingBuffer(300))
    password_resets: RingBuffer = field(default_factory=lambda: RingBuffer(300))
    mfa_failures: RingBuffer = field(default_factory=lambda: RingBuffer(300))
    concurrent_sessions: int = 0

    # Network
    unique_src_ips: UniqueTracker = field(default_factory=lambda: UniqueTracker(60))
    unique_dst_ips: UniqueTracker = field(default_factory=lambda: UniqueTracker(60))
    unique_ports: UniqueTracker = field(default_factory=lambda: UniqueTracker(60))
    bytes_in: RingBuffer = field(default_factory=lambda: RingBuffer(60))
    bytes_out: RingBuffer = field(default_factory=lambda: RingBuffer(60))
    dns_queries: RingBuffer = field(default_factory=lambda: RingBuffer(60))
    lateral_movements: RingBuffer = field(default_factory=lambda: RingBuffer(300))
    external_connections: RingBuffer = field(default_factory=lambda: RingBuffer(60))

    # Clinical
    epic_accesses: RingBuffer = field(default_factory=lambda: RingBuffer(60))
    fhir_requests: RingBuffer = field(default_factory=lambda: RingBuffer(60))
    hl7_messages: RingBuffer = field(default_factory=lambda: RingBuffer(60))
    dicom_transfers: RingBuffer = field(default_factory=lambda: RingBuffer(60))
    phi_accesses: RingBuffer = field(default_factory=lambda: RingBuffer(300))
    patient_records: UniqueTracker = field(default_factory=lambda: UniqueTracker(300))
    iomt_events: RingBuffer = field(default_factory=lambda: RingBuffer(60))

    # Escalation
    threat_alerts: RingBuffer = field(default_factory=lambda: RingBuffer(300))
    organ_errors: RingBuffer = field(default_factory=lambda: RingBuffer(300))
    escalation_chains: list[int] = field(default_factory=list)
    response_times_ms: deque = field(default_factory=lambda: deque(maxlen=100))
    p0_offline_count: int = 0
    dead_letters: RingBuffer = field(default_factory=lambda: RingBuffer(300))
    hmac_failures: RingBuffer = field(default_factory=lambda: RingBuffer(300))
    rate_limit_hits: RingBuffer = field(default_factory=lambda: RingBuffer(300))
    quarantine_triggers: RingBuffer = field(default_factory=lambda: RingBuffer(300))


class FeatureExtractor:
    """
    Transforms raw mesh events into fixed-width numerical feature vectors.

    Usage:
        extractor = FeatureExtractor()

        # Feed events as they arrive from the mesh
        extractor.ingest(envelope.payload)

        # Get current feature vector for prediction
        features = extractor.extract()  # np.ndarray of shape (48,)
    """

    def __init__(self):
        self._state = FeatureState()
        self._last_extract_time: float = time.monotonic()

    def ingest(self, event: dict[str, Any]) -> None:
        """
        Process a mesh event and update internal feature state.

        Events are dicts from mesh envelope payloads. The extractor
        looks for known keys and updates the appropriate counters.
        """
        now = time.monotonic()
        event_type = event.get("event_type", event.get("threat_type", event.get("action", "")))

        # Always record in temporal buffers
        self._state.event_buffer_1min.record(now)
        self._state.event_buffer_5min.record(now)
        self._state.event_buffer_15min.record(now)

        # Behavioral signals
        if event_type in ("failed_login", "brute_force_login", "auth_failure"):
            self._state.failed_logins.record(now)
        if "username" in event or "user" in event:
            user = event.get("username", event.get("user", ""))
            if user:
                self._state.unique_users_1min.record(user)
                self._state.unique_users_5min.record(user)
        if event_type in ("privilege_escalation", "sudo_attempt", "role_change"):
            self._state.privilege_escalations.record(now)
        if event_type == "password_reset":
            self._state.password_resets.record(now)
        if event_type in ("mfa_failure", "mfa_timeout"):
            self._state.mfa_failures.record(now)
        if "concurrent_sessions" in event:
            self._state.concurrent_sessions = event["concurrent_sessions"]

        # Network signals
        if "source_ip" in event:
            self._state.unique_src_ips.record(event["source_ip"])
        if "dest_ip" in event or "target_ip" in event:
            self._state.unique_dst_ips.record(event.get("dest_ip", event.get("target_ip", "")))
        if "port" in event or "dest_port" in event:
            self._state.unique_ports.record(str(event.get("port", event.get("dest_port", ""))))
        if "bytes_in" in event:
            self._state.bytes_in.record(now)
        if "bytes_out" in event:
            self._state.bytes_out.record(now)
        if event_type in ("dns_query", "dns_lookup"):
            self._state.dns_queries.record(now)
        if event_type in ("lateral_movement", "internal_scan"):
            self._state.lateral_movements.record(now)
        if event_type in ("external_connection", "outbound_connection"):
            self._state.external_connections.record(now)

        # Clinical signals
        if event_type in ("epic_access", "ehr_query") or "epic" in str(event).lower():
            self._state.epic_accesses.record(now)
        if event_type in ("fhir_request", "fhir_query"):
            self._state.fhir_requests.record(now)
        if event_type in ("hl7_message", "hl7_event"):
            self._state.hl7_messages.record(now)
        if event_type in ("dicom_transfer", "dicom_event"):
            self._state.dicom_transfers.record(now)
        if event_type in ("phi_access", "phi_view", "phi_export"):
            self._state.phi_accesses.record(now)
        if "patient_id" in event:
            self._state.patient_records.record(event["patient_id"])
        if event_type in ("iomt_event", "medical_device_event"):
            self._state.iomt_events.record(now)

        # Escalation signals
        if event.get("severity") in ("critical", "high") or event_type == "threat_alert":
            self._state.threat_alerts.record(now)
        if event_type in ("organ_error", "organ_unresponsive"):
            self._state.organ_errors.record(now)
        if "escalation_chain" in event:
            chain = event["escalation_chain"]
            if isinstance(chain, list):
                self._state.escalation_chains.append(len(chain))
                if len(self._state.escalation_chains) > 100:
                    self._state.escalation_chains = self._state.escalation_chains[-100:]
        if "response_time_ms" in event:
            self._state.response_times_ms.append(event["response_time_ms"])
        if event_type == "p0_organ_offline":
            self._state.p0_offline_count = event.get("count", self._state.p0_offline_count + 1)
        if event_type == "dead_letter":
            self._state.dead_letters.record(now)
        if event_type == "hmac_failure":
            self._state.hmac_failures.record(now)
        if event_type == "rate_limit_exceeded":
            self._state.rate_limit_hits.record(now)
        if event_type in ("quarantine_triggered", "quarantine"):
            self._state.quarantine_triggers.record(now)

    def extract(self) -> np.ndarray:
        """
        Extract the current 48-dimensional feature vector from accumulated state.
        Returns a numpy array of shape (48,).
        """
        s = self._state
        now = datetime.now(timezone.utc)
        hour = now.hour + now.minute / 60.0
        day = now.weekday()

        # Burst score: ratio of 1min rate to 15min rate (spikes = high)
        rate_1 = s.event_buffer_1min.rate()
        rate_15 = s.event_buffer_15min.rate()
        burst_score = (rate_1 / rate_15) if rate_15 > 0 else rate_1

        # After hours: 8pm - 6am = elevated risk
        after_hours = 1.0 if (hour >= 20 or hour < 6) else 0.0

        # In/out ratio
        bytes_in_rate = s.bytes_in.rate()
        bytes_out_rate = s.bytes_out.rate()
        in_out_ratio = (bytes_out_rate / bytes_in_rate) if bytes_in_rate > 0 else bytes_out_rate

        # Port scan score: high unique ports + low data = scanning
        port_count = s.unique_ports.unique_count()
        port_scan_score = min(port_count / 100.0, 1.0)

        # Bulk export flag: high PHI access + high bytes out
        phi_rate = s.phi_accesses.rate()
        bulk_export = 1.0 if (phi_rate > 5 and bytes_out_rate > 10) else 0.0

        # Abnormal query pattern: high FHIR/Epic rate outside business hours
        clinical_rate = s.epic_accesses.rate() + s.fhir_requests.rate()
        abnormal_query = 1.0 if (clinical_rate > 10 and after_hours) else 0.0

        # Clinical off-hours access
        clinical_off_hours = clinical_rate * after_hours

        # Mean escalation chain length
        mean_chain = (sum(s.escalation_chains) / len(s.escalation_chains)
                      if s.escalation_chains else 0.0)

        # Mean response time
        mean_response = (sum(s.response_times_ms) / len(s.response_times_ms)
                         if s.response_times_ms else 0.0)

        # Overall threat score (composite)
        threat_score = self._compute_threat_score(s)

        features = np.array([
            # Temporal (0-7)
            rate_1,
            s.event_buffer_5min.rate(),
            rate_15,
            burst_score,
            math.sin(2 * math.pi * hour / 24),
            math.cos(2 * math.pi * hour / 24),
            math.sin(2 * math.pi * day / 7),
            math.cos(2 * math.pi * day / 7),
            # Behavioral (8-17)
            s.failed_logins.rate(),
            float(s.unique_users_1min.unique_count()),
            float(s.unique_users_5min.unique_count()),
            0.0,  # session_anomaly_score — filled by predictor
            float(s.privilege_escalations.count()),
            after_hours,
            0.0,  # new_user_flag — filled by predictor
            s.password_resets.rate(),
            s.mfa_failures.rate(),
            float(s.concurrent_sessions),
            # Network (18-27)
            float(s.unique_src_ips.unique_count()),
            float(s.unique_dst_ips.unique_count()),
            float(port_count),
            bytes_in_rate,
            bytes_out_rate,
            in_out_ratio,
            s.dns_queries.rate(),
            float(s.lateral_movements.count()),
            float(s.external_connections.count()),
            port_scan_score,
            # Clinical (28-37)
            s.epic_accesses.rate(),
            s.fhir_requests.rate(),
            s.hl7_messages.rate(),
            s.dicom_transfers.rate(),
            float(s.phi_accesses.count()),
            float(s.patient_records.unique_count()),
            bulk_export,
            abnormal_query,
            float(s.iomt_events.count()),
            clinical_off_hours,
            # Escalation (38-47)
            s.threat_alerts.rate(),
            s.organ_errors.rate(),
            mean_chain,
            mean_response,
            float(s.p0_offline_count),
            s.dead_letters.rate(),
            float(s.hmac_failures.count()),
            float(s.rate_limit_hits.count()),
            float(s.quarantine_triggers.count()),
            threat_score,
        ], dtype=np.float64)

        assert features.shape == (FEATURE_DIM,), f"Expected {FEATURE_DIM} features, got {features.shape}"
        return features

    def _compute_threat_score(self, s: FeatureState) -> float:
        """Compute a 0-100 composite threat score from current state."""
        score = 0.0

        # Failed logins (max 20 points)
        score += min(s.failed_logins.rate() * 4, 20.0)

        # Lateral movement (max 15 points)
        score += min(s.lateral_movements.count() * 5, 15.0)

        # PHI access anomalies (max 15 points)
        score += min(s.phi_accesses.rate() * 3, 15.0)

        # Port scanning (max 10 points)
        score += min(s.unique_ports.unique_count() * 0.5, 10.0)

        # Active threat alerts (max 15 points)
        score += min(s.threat_alerts.count() * 3, 15.0)

        # P0 organs offline (max 15 points)
        score += min(s.p0_offline_count * 5, 15.0)

        # HMAC failures — integrity attacks (max 10 points)
        score += min(s.hmac_failures.count() * 5, 10.0)

        return min(score, 100.0)

    def get_feature_names(self) -> list[str]:
        """Return ordered list of feature names."""
        return list(FEATURE_NAMES)

    def reset(self) -> None:
        """Reset all accumulated state."""
        self._state = FeatureState()
