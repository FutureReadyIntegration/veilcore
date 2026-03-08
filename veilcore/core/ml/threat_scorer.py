"""
VeilCore Threat Scorer
=======================
Composite threat scoring engine that combines ML predictions
with rule-based heuristics for a unified 0-100 threat score.

The scorer weights multiple signal sources:
    - ML anomaly score (from Isolation Forest)
    - ML classification confidence (from Random Forest)
    - Rule-based indicators (failed logins, PHI access, etc.)
    - Temporal patterns (after-hours, burst activity)
    - Historical context (escalation chains, prior alerts)

Output is a single score 0-100 with severity mapping:
    0-20:  Normal
    20-40: Elevated
    40-60: High
    60-80: Critical
    80-100: Emergency
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np

from core.ml.features import FeatureExtractor, FEATURE_NAMES
from core.ml.models import PredictionResult

logger = logging.getLogger("veilcore.ml.threat_scorer")


@dataclass
class ThreatScore:
    """Composite threat assessment."""
    score: float = 0.0                  # 0-100
    severity: str = "normal"
    components: dict[str, float] = field(default_factory=dict)
    contributing_factors: list[str] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": round(self.score, 1),
            "severity": self.severity,
            "components": {k: round(v, 2) for k, v in self.components.items()},
            "contributing_factors": self.contributing_factors,
            "recommended_actions": self.recommended_actions,
            "timestamp": self.timestamp,
        }


class ThreatScorer:
    """
    Composite threat scoring engine.

    Combines ML predictions with deterministic rules to produce
    a single threat score for the current security posture.

    Usage:
        scorer = ThreatScorer()
        features = extractor.extract()
        ml_result = predictor.predict_features(features)
        score = scorer.score(features, ml_result)
        print(f"Threat: {score.score}/100 ({score.severity})")
    """

    # Severity thresholds
    NORMAL = 20
    ELEVATED = 40
    HIGH = 60
    CRITICAL = 80

    # Component weights (must sum to 1.0)
    WEIGHTS = {
        "ml_anomaly": 0.25,
        "ml_classification": 0.20,
        "behavioral": 0.20,
        "network": 0.15,
        "clinical": 0.10,
        "escalation": 0.10,
    }

    def __init__(self):
        self._history: list[ThreatScore] = []
        self._max_history = 1000

    def score(
        self,
        features: np.ndarray,
        ml_result: Optional[PredictionResult] = None,
    ) -> ThreatScore:
        """
        Compute composite threat score from features and ML prediction.
        """
        components = {}
        factors = []
        actions = []

        # Component 1: ML Anomaly Score (0-100)
        ml_anomaly_score = 0.0
        if ml_result and ml_result.is_anomaly:
            # Convert anomaly score (-1 to +1) to (0 to 100)
            # More negative = more anomalous = higher score
            ml_anomaly_score = max(0, min(100, (1 - ml_result.anomaly_score) * 50))
            if ml_anomaly_score > 50:
                factors.append(f"ML anomaly detected (score: {ml_result.anomaly_score:.3f})")
        components["ml_anomaly"] = ml_anomaly_score

        # Component 2: ML Classification (0-100)
        ml_class_score = 0.0
        if ml_result and ml_result.is_threat:
            ml_class_score = ml_result.confidence * 100
            factors.append(f"ML classified as {ml_result.threat_class} ({ml_result.confidence:.1%})")
            actions.extend(self._get_actions_for_class(ml_result.threat_class))
        components["ml_classification"] = ml_class_score

        # Component 3: Behavioral Score (0-100)
        behavioral_score = self._score_behavioral(features, factors, actions)
        components["behavioral"] = behavioral_score

        # Component 4: Network Score (0-100)
        network_score = self._score_network(features, factors, actions)
        components["network"] = network_score

        # Component 5: Clinical Score (0-100)
        clinical_score = self._score_clinical(features, factors, actions)
        components["clinical"] = clinical_score

        # Component 6: Escalation Score (0-100)
        escalation_score = self._score_escalation(features, factors, actions)
        components["escalation"] = escalation_score

        # Weighted composite
        total = sum(
            components[k] * self.WEIGHTS[k]
            for k in self.WEIGHTS
        )

        # Clamp to 0-100
        total = max(0.0, min(100.0, total))

        # Determine severity
        if total >= self.CRITICAL:
            severity = "emergency"
        elif total >= self.HIGH:
            severity = "critical"
        elif total >= self.ELEVATED:
            severity = "high"
        elif total >= self.NORMAL:
            severity = "elevated"
        else:
            severity = "normal"

        # Always add monitoring action
        if severity != "normal" and not actions:
            actions.append("Continue monitoring, gather additional evidence")

        result = ThreatScore(
            score=total,
            severity=severity,
            components=components,
            contributing_factors=factors,
            recommended_actions=actions,
        )

        # Store in history
        self._history.append(result)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        return result

    def _score_behavioral(self, f: np.ndarray, factors: list, actions: list) -> float:
        """Score behavioral indicators (features 8-17)."""
        score = 0.0

        # Failed login rate
        failed_rate = f[8]
        if failed_rate > 5:
            score += min(30, failed_rate * 3)
            factors.append(f"High failed login rate: {failed_rate:.1f}/sec")
            actions.append("Investigate source of failed logins")
        elif failed_rate > 1:
            score += failed_rate * 5

        # Privilege escalation attempts
        priv_esc = f[12]
        if priv_esc > 2:
            score += min(25, priv_esc * 5)
            factors.append(f"Privilege escalation attempts: {priv_esc:.0f}")
            actions.append("Audit privilege changes immediately")

        # MFA failures
        mfa_fail = f[16]
        if mfa_fail > 2:
            score += min(20, mfa_fail * 4)
            factors.append(f"MFA failure rate: {mfa_fail:.1f}/sec")

        # After hours + session anomaly
        if f[13] > 0.5 and f[11] > 0.3:
            score += 15
            factors.append("Anomalous after-hours session activity")

        # Concurrent sessions spike
        if f[17] > 15:
            score += min(10, (f[17] - 15) * 2)

        return min(100, score)

    def _score_network(self, f: np.ndarray, factors: list, actions: list) -> float:
        """Score network indicators (features 18-27)."""
        score = 0.0

        # Port scanning
        port_scan = f[27]
        if port_scan > 0.3:
            score += min(30, port_scan * 40)
            factors.append(f"Port scanning detected (score: {port_scan:.2f})")
            actions.append("Block scanning source, deploy decoys")

        # Lateral movement
        lateral = f[25]
        if lateral > 3:
            score += min(30, lateral * 5)
            factors.append(f"Lateral movement events: {lateral:.0f}")
            actions.append("Micro-segment affected network zone")

        # Unusual traffic ratio
        ratio = f[23]
        if ratio > 3:
            score += min(20, ratio * 3)
            factors.append(f"Abnormal traffic ratio (out/in): {ratio:.1f}")

        # High external connections
        external = f[26]
        if external > 20:
            score += min(15, (external - 20) * 1.5)
            factors.append(f"High external connections: {external:.0f}")

        # DNS anomaly
        dns_rate = f[24]
        if dns_rate > 10:
            score += min(10, (dns_rate - 10) * 2)

        return min(100, score)

    def _score_clinical(self, f: np.ndarray, factors: list, actions: list) -> float:
        """Score clinical system indicators (features 28-37)."""
        score = 0.0

        # Bulk export
        if f[34] > 0.5:
            score += 40
            factors.append("Bulk data export detected")
            actions.append("URGENT: Block bulk exports, investigate immediately")

        # Abnormal query pattern
        if f[35] > 0.5:
            score += 25
            factors.append("Abnormal clinical query pattern")

        # High PHI access
        phi = f[32]
        if phi > 20:
            score += min(20, (phi - 20) * 1.5)
            factors.append(f"Elevated PHI access: {phi:.0f} records")

        # Clinical off-hours
        off_hours = f[37]
        if off_hours > 5:
            score += min(15, off_hours * 2)
            factors.append(f"Clinical system access outside business hours")

        return min(100, score)

    def _score_escalation(self, f: np.ndarray, factors: list, actions: list) -> float:
        """Score escalation indicators (features 38-47)."""
        score = 0.0

        # Active threat alerts
        threat_rate = f[38]
        if threat_rate > 1:
            score += min(25, threat_rate * 10)
            factors.append(f"Active threat alert rate: {threat_rate:.1f}/sec")

        # P0 organs offline
        p0_offline = f[42]
        if p0_offline > 0:
            score += min(30, p0_offline * 15)
            factors.append(f"Critical (P0) organs offline: {p0_offline:.0f}")
            actions.append("EMERGENCY: Restore P0 organs immediately")

        # HMAC failures (integrity attacks)
        hmac_fail = f[44]
        if hmac_fail > 0:
            score += min(25, hmac_fail * 10)
            factors.append(f"HMAC integrity failures: {hmac_fail:.0f}")
            actions.append("Investigate message tampering, rotate mesh key")

        # Quarantine triggers
        quarantine = f[46]
        if quarantine > 0:
            score += min(15, quarantine * 5)
            factors.append(f"Quarantine triggered: {quarantine:.0f} times")

        # Overall existing threat score
        existing = f[47]
        if existing > 30:
            score += min(10, (existing - 30) * 0.5)

        return min(100, score)

    def _get_actions_for_class(self, threat_class: str) -> list[str]:
        """Get recommended actions for a threat classification."""
        action_map = {
            "brute_force": ["Block source IPs", "Force MFA re-enrollment"],
            "ransomware": ["EMERGENCY: Isolate segments", "Snapshot all volumes", "Activate incident response"],
            "exfiltration": ["Block outbound transfers", "Forensic capture on source"],
            "lateral_movement": ["Micro-segment network", "Force re-authentication"],
            "insider_threat": ["Enable enhanced monitoring", "Restrict data access"],
            "phishing": ["Quarantine related emails", "Reset compromised credentials"],
            "port_scan": ["Rate-limit source", "Deploy honeypots"],
            "credential_stuffing": ["Enable CAPTCHA", "Lock affected accounts"],
            "privilege_escalation": ["Revoke escalated privileges", "Audit role assignments"],
        }
        return action_map.get(threat_class, ["Investigate and gather evidence"])

    def get_trend(self, window: int = 20) -> dict[str, Any]:
        """Get threat score trend from recent history."""
        recent = self._history[-window:]
        if not recent:
            return {"trend": "stable", "scores": [], "mean": 0, "max": 0}

        scores = [s.score for s in recent]
        mean = sum(scores) / len(scores)
        max_score = max(scores)

        if len(scores) >= 3:
            first_half = sum(scores[:len(scores)//2]) / (len(scores)//2)
            second_half = sum(scores[len(scores)//2:]) / (len(scores) - len(scores)//2)
            if second_half > first_half * 1.3:
                trend = "increasing"
            elif second_half < first_half * 0.7:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        return {
            "trend": trend,
            "scores": [round(s, 1) for s in scores],
            "mean": round(mean, 1),
            "max": round(max_score, 1),
            "current_severity": recent[-1].severity if recent else "unknown",
        }
