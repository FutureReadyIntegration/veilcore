"""
VeilCore Threat Predictor
==========================
Real-time prediction engine that connects to the mesh network,
ingests events from all organs, extracts features, and runs
two-stage ML prediction (anomaly detection → threat classification).

Publishes predictions back to the mesh as threat alerts so all
82 organs can react to predicted threats.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np

from core.ml.features import FeatureExtractor, FEATURE_DIM
from core.ml.models import AnomalyDetector, ThreatClassifier, PredictionResult

logger = logging.getLogger("veilcore.ml.predictor")


@dataclass
class PredictorConfig:
    """Configuration for the real-time threat predictor."""
    # Prediction frequency
    prediction_interval: float = 5.0        # seconds between predictions
    min_events_for_prediction: int = 10     # minimum events before first prediction

    # Anomaly thresholds
    anomaly_score_threshold: float = -0.3   # scores below this trigger classification
    high_confidence_threshold: float = 0.75 # above this = high confidence alert

    # Alert suppression (avoid flooding)
    alert_cooldown: float = 30.0            # seconds between alerts for same threat type
    max_alerts_per_minute: int = 10

    # Model paths
    anomaly_model_path: str = "/var/lib/veilcore/models/anomaly_detector.joblib"
    classifier_model_path: str = "/var/lib/veilcore/models/threat_classifier.joblib"

    # Feature extraction
    feature_reset_interval: float = 900.0   # reset feature state every 15 min


class ThreatPredictor:
    """
    Real-time ML threat prediction engine.

    Connects to the VeilCore mesh as an organ, receives events,
    runs continuous prediction, and publishes threat alerts.

    Usage:
        predictor = ThreatPredictor()
        await predictor.start()  # connects to mesh and begins prediction loop
    """

    def __init__(self, config: Optional[PredictorConfig] = None):
        self.config = config or PredictorConfig()
        self._extractor = FeatureExtractor()
        self._anomaly_detector = AnomalyDetector()
        self._classifier = ThreatClassifier()
        self._mesh_client = None
        self._running = False
        self._tasks: list[asyncio.Task] = []
        self._event_count: int = 0
        self._prediction_count: int = 0
        self._threat_count: int = 0
        self._last_alerts: dict[str, float] = {}  # threat_class → last alert timestamp
        self._alert_times: deque[float] = deque(maxlen=100)
        self._predictions: deque[PredictionResult] = deque(maxlen=1000)
        self._last_feature_reset: float = time.monotonic()

    async def start(self, mesh_client=None) -> None:
        """Start the prediction engine and connect to mesh."""
        logger.info("╔══════════════════════════════════════════════════╗")
        logger.info("║    VEILCORE ML THREAT PREDICTOR — STARTING      ║")
        logger.info("║    The predictive cortex of hospital defense     ║")
        logger.info("╚══════════════════════════════════════════════════╝")

        # Load models if they exist
        if self._anomaly_detector.load(self.config.anomaly_model_path):
            logger.info("✓ Anomaly detector model loaded")
        else:
            logger.warning("⚠ No anomaly detector model found — will need training")

        if self._classifier.load(self.config.classifier_model_path):
            logger.info("✓ Threat classifier model loaded")
        else:
            logger.warning("⚠ No threat classifier model found — will need training")

        # Connect to mesh
        if mesh_client:
            self._mesh_client = mesh_client
        else:
            from core.mesh.client import MeshClient
            from core.mesh.protocol import MeshTopic
            self._mesh_client = MeshClient(
                organ_name="ml-predictor",
                subscriptions=[
                    MeshTopic.THREAT_ALERTS,
                    MeshTopic.STATUS_UPDATES,
                    MeshTopic.NETWORK_EVENTS,
                    MeshTopic.EPIC_EVENTS,
                    MeshTopic.IMPRIVATA_EVENTS,
                    MeshTopic.HL7_EVENTS,
                    MeshTopic.FHIR_EVENTS,
                    MeshTopic.DICOM_EVENTS,
                    MeshTopic.IOMT_EVENTS,
                    MeshTopic.HIPAA_EVENTS,
                    MeshTopic.FORENSIC_EVENTS,
                    MeshTopic.COMPLIANCE_EVENTS,
                ],
            )
            connected = await self._mesh_client.connect_with_retry()
            if not connected:
                logger.error("Failed to connect to mesh — predictions will run offline")

        # Register handlers
        if self._mesh_client:
            self._mesh_client.on_message(self._on_mesh_event)

        self._running = True
        self._tasks = [
            asyncio.create_task(self._prediction_loop(), name="prediction-loop"),
            asyncio.create_task(self._maintenance_loop(), name="maintenance-loop"),
        ]
        logger.info("ML threat predictor active — ingesting events from mesh")

    async def stop(self) -> None:
        """Stop the prediction engine."""
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        if self._mesh_client:
            await self._mesh_client.disconnect()
        logger.info(
            f"ML predictor stopped | Events: {self._event_count} | "
            f"Predictions: {self._prediction_count} | Threats: {self._threat_count}"
        )

    async def _on_mesh_event(self, envelope) -> None:
        """Process incoming mesh events for feature extraction."""
        try:
            payload = envelope.payload or {}
            payload["_source_organ"] = envelope.source
            payload["_msg_type"] = envelope.msg_type.value
            payload["_timestamp"] = envelope.timestamp
            self._extractor.ingest(payload)
            self._event_count += 1
        except Exception as e:
            logger.debug(f"Event ingestion error: {e}")

    async def _prediction_loop(self) -> None:
        """Main prediction loop — runs every prediction_interval seconds."""
        logger.info(f"Prediction loop started (interval: {self.config.prediction_interval}s)")
        while self._running:
            try:
                await asyncio.sleep(self.config.prediction_interval)

                if self._event_count < self.config.min_events_for_prediction:
                    continue

                result = self.predict_current()
                self._predictions.append(result)
                self._prediction_count += 1

                if result.is_threat:
                    self._threat_count += 1
                    await self._handle_threat(result)

                if self._prediction_count % 100 == 0:
                    logger.info(
                        f"📊 ML stats | Events: {self._event_count} | "
                        f"Predictions: {self._prediction_count} | "
                        f"Threats: {self._threat_count} | "
                        f"Latest: {result.threat_class} ({result.confidence:.2f})"
                    )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Prediction loop error: {e}")

    async def _maintenance_loop(self) -> None:
        """Periodic maintenance: feature reset, alert cleanup."""
        while self._running:
            try:
                await asyncio.sleep(60)

                # Reset feature state periodically to prevent drift
                elapsed = time.monotonic() - self._last_feature_reset
                if elapsed >= self.config.feature_reset_interval:
                    self._extractor.reset()
                    self._last_feature_reset = time.monotonic()
                    logger.debug("Feature state reset")

                # Clean old alert cooldowns
                now = time.monotonic()
                expired = [k for k, t in self._last_alerts.items()
                           if now - t > self.config.alert_cooldown * 10]
                for k in expired:
                    del self._last_alerts[k]

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Maintenance error: {e}")

    def predict_current(self) -> PredictionResult:
        """
        Run prediction on the current feature state.
        Returns a PredictionResult.
        """
        start = time.monotonic()
        features = self._extractor.extract()

        # Stage 1: Anomaly detection
        is_anomaly, anomaly_score = self._anomaly_detector.predict(features)

        result = PredictionResult(
            is_anomaly=is_anomaly,
            anomaly_score=anomaly_score,
            features_used=FEATURE_DIM,
        )

        # Stage 2: If anomalous, classify the threat
        if is_anomaly and anomaly_score < self.config.anomaly_score_threshold:
            threat_class, probabilities, confidence = self._classifier.predict(features)
            result.threat_class = threat_class
            result.threat_probabilities = probabilities
            result.confidence = confidence
        elif is_anomaly:
            result.threat_class = "anomaly_unclassified"
            result.confidence = abs(anomaly_score)

        result.prediction_time_ms = (time.monotonic() - start) * 1000
        return result

    def predict_features(self, features: np.ndarray) -> PredictionResult:
        """
        Run prediction on an explicit feature vector.
        Useful for batch prediction or testing.
        """
        start = time.monotonic()

        is_anomaly, anomaly_score = self._anomaly_detector.predict(features)

        result = PredictionResult(
            is_anomaly=is_anomaly,
            anomaly_score=anomaly_score,
            features_used=FEATURE_DIM,
        )

        if is_anomaly and anomaly_score < self.config.anomaly_score_threshold:
            threat_class, probabilities, confidence = self._classifier.predict(features)
            result.threat_class = threat_class
            result.threat_probabilities = probabilities
            result.confidence = confidence
        elif is_anomaly:
            result.threat_class = "anomaly_unclassified"
            result.confidence = abs(anomaly_score)

        result.prediction_time_ms = (time.monotonic() - start) * 1000
        return result

    async def _handle_threat(self, result: PredictionResult) -> None:
        """Handle a detected threat — publish to mesh if not suppressed."""
        now = time.monotonic()

        # Check alert cooldown for this threat type
        last_alert = self._last_alerts.get(result.threat_class, 0)
        if now - last_alert < self.config.alert_cooldown:
            logger.debug(f"Alert suppressed for {result.threat_class} (cooldown)")
            return

        # Check rate limit
        self._alert_times.append(now)
        recent = sum(1 for t in self._alert_times if now - t < 60)
        if recent > self.config.max_alerts_per_minute:
            logger.warning("Alert rate limit reached, suppressing")
            return

        self._last_alerts[result.threat_class] = now

        logger.warning(
            f"🧠 ML PREDICTION: {result.threat_class} | "
            f"Confidence: {result.confidence:.2f} | "
            f"Severity: {result.severity} | "
            f"Anomaly score: {result.anomaly_score:.4f}"
        )

        # Publish to mesh
        if self._mesh_client and self._mesh_client.is_connected:
            await self._mesh_client.send_threat_alert(
                threat_type=f"ml_predicted_{result.threat_class}",
                severity=result.severity,
                details={
                    "prediction": result.to_dict(),
                    "source": "ml-predictor",
                    "model_type": "isolation_forest+random_forest",
                    "recommended_action": self._get_recommended_action(result),
                },
            )

    def _get_recommended_action(self, result: PredictionResult) -> str:
        """Get recommended response action based on threat type."""
        actions = {
            "brute_force": "Block source IPs, force MFA re-enrollment, alert security team",
            "ransomware": "EMERGENCY: Isolate affected segments, snapshot all volumes, activate IR",
            "exfiltration": "Block outbound transfers, quarantine source, forensic capture",
            "lateral_movement": "Micro-segment affected zone, force re-auth, scan for implants",
            "insider_threat": "Enable enhanced monitoring, restrict data access, notify compliance",
            "phishing": "Quarantine email, reset compromised credentials, scan endpoints",
            "port_scan": "Rate-limit source, deploy honeypots, monitor for follow-up exploitation",
            "credential_stuffing": "Enable CAPTCHA, lock affected accounts, rotate secrets",
            "privilege_escalation": "Revoke escalated privileges, audit role assignments, forensic review",
        }
        return actions.get(result.threat_class, "Monitor closely, gather additional evidence")

    def ingest_event(self, event: dict[str, Any]) -> None:
        """Manually ingest an event (for testing or non-mesh usage)."""
        self._extractor.ingest(event)
        self._event_count += 1

    def get_stats(self) -> dict[str, Any]:
        """Get predictor statistics."""
        recent = list(self._predictions)[-10:]
        return {
            "events_ingested": self._event_count,
            "predictions_made": self._prediction_count,
            "threats_detected": self._threat_count,
            "models": {
                "anomaly_detector": self._anomaly_detector.is_fitted,
                "threat_classifier": self._classifier.is_fitted,
            },
            "recent_predictions": [r.to_dict() for r in recent],
            "running": self._running,
        }
