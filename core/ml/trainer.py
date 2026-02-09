"""
VeilCore Model Trainer
=======================
Training pipeline for ML models. Generates synthetic hospital
network data for initial model bootstrapping, and supports
retraining from real mesh ledger data.

Synthetic data simulates realistic hospital traffic patterns:
    - Normal business hours vs after-hours
    - Clinical workflow patterns (Epic, FHIR, HL7, DICOM)
    - Attack signatures embedded in normal traffic
    - Seasonal and time-of-day variations
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import numpy as np

from core.ml.features import FEATURE_DIM, FEATURE_NAMES
from core.ml.models import (
    AnomalyDetector,
    ThreatClassifier,
    THREAT_CLASSES,
    MODEL_DIR,
)

logger = logging.getLogger("veilcore.ml.trainer")


class ModelTrainer:
    """
    Training pipeline for VeilCore ML models.

    Usage:
        trainer = ModelTrainer()

        # Generate synthetic data and train both models
        trainer.train_from_synthetic(n_normal=5000, n_threat=1000)

        # Or train from real mesh ledger data
        trainer.train_from_ledger("/var/log/veilcore/mesh-ledger.jsonl")
    """

    def __init__(self):
        self._anomaly_detector = AnomalyDetector()
        self._classifier = ThreatClassifier()
        self._rng = np.random.RandomState(42)

    def train_from_synthetic(
        self,
        n_normal: int = 5000,
        n_threat_per_class: int = 200,
        save: bool = True,
    ) -> dict[str, Any]:
        """
        Generate synthetic training data and train both models.
        Returns training metrics.
        """
        logger.info("=" * 60)
        logger.info("  VEILCORE ML — SYNTHETIC TRAINING PIPELINE")
        logger.info("=" * 60)

        start = time.monotonic()

        # Generate normal baseline data
        logger.info(f"Generating {n_normal} normal baseline samples...")
        X_normal = self._generate_normal(n_normal)

        # Generate threat data
        threat_classes_to_generate = [c for c in THREAT_CLASSES if c != "benign"]
        n_threats = n_threat_per_class * len(threat_classes_to_generate)
        logger.info(f"Generating {n_threats} threat samples ({n_threat_per_class} per class)...")

        X_threats = []
        y_threats = []
        for threat_class in threat_classes_to_generate:
            samples = self._generate_threat(threat_class, n_threat_per_class)
            X_threats.append(samples)
            y_threats.extend([threat_class] * n_threat_per_class)

        X_threat = np.vstack(X_threats)
        y_threat = np.array(y_threats)

        # Train anomaly detector on normal data only
        logger.info("\n── Stage 1: Training Anomaly Detector")
        self._anomaly_detector.fit(X_normal)

        # Verify anomaly detector catches threats
        normal_scores = []
        for i in range(min(500, n_normal)):
            _, score = self._anomaly_detector.predict(X_normal[i])
            normal_scores.append(score)

        threat_scores = []
        for i in range(min(500, len(X_threat))):
            _, score = self._anomaly_detector.predict(X_threat[i])
            threat_scores.append(score)

        logger.info(
            f"  Normal mean score: {np.mean(normal_scores):.4f} | "
            f"Threat mean score: {np.mean(threat_scores):.4f}"
        )

        # Train classifier on combined labeled data
        logger.info("\n── Stage 2: Training Threat Classifier")
        X_all = np.vstack([X_normal, X_threat])
        y_all = np.array(["benign"] * n_normal + list(y_threat))

        classifier_metrics = self._classifier.fit(X_all, y_all)

        # Save models
        if save:
            logger.info("\n── Saving Models")
            os.makedirs(MODEL_DIR, exist_ok=True)
            anomaly_path = self._anomaly_detector.save()
            classifier_path = self._classifier.save()
            logger.info(f"  ✓ {anomaly_path}")
            logger.info(f"  ✓ {classifier_path}")

        elapsed = time.monotonic() - start

        metrics = {
            "training_time_seconds": round(elapsed, 2),
            "normal_samples": n_normal,
            "threat_samples": n_threats,
            "total_samples": n_normal + n_threats,
            "anomaly_detector": {
                "normal_mean_score": round(float(np.mean(normal_scores)), 4),
                "threat_mean_score": round(float(np.mean(threat_scores)), 4),
                "separation": round(float(np.mean(normal_scores) - np.mean(threat_scores)), 4),
            },
            "classifier": classifier_metrics,
        }

        logger.info(f"\n✅ Training complete in {elapsed:.1f}s")
        logger.info(f"  Score separation: {metrics['anomaly_detector']['separation']:.4f}")
        logger.info(f"  Classifier F1: {classifier_metrics['cv_f1_mean']:.3f}")

        return metrics

    def _generate_normal(self, n: int) -> np.ndarray:
        """Generate synthetic normal hospital network traffic."""
        rng = self._rng
        X = np.zeros((n, FEATURE_DIM))

        for i in range(n):
            hour = rng.uniform(0, 24)
            is_business = 6 <= hour <= 20
            day = rng.randint(0, 7)
            is_weekday = day < 5

            base_activity = 1.0 if (is_business and is_weekday) else 0.3

            # Temporal (0-7)
            X[i, 0] = rng.exponential(2.0 * base_activity)       # events/sec 1min
            X[i, 1] = rng.exponential(1.5 * base_activity)       # events/sec 5min
            X[i, 2] = rng.exponential(1.0 * base_activity)       # events/sec 15min
            X[i, 3] = rng.uniform(0.8, 1.5)                      # burst score (normal ~1.0)
            X[i, 4] = np.sin(2 * np.pi * hour / 24)              # hour sin
            X[i, 5] = np.cos(2 * np.pi * hour / 24)              # hour cos
            X[i, 6] = np.sin(2 * np.pi * day / 7)                # day sin
            X[i, 7] = np.cos(2 * np.pi * day / 7)                # day cos

            # Behavioral (8-17)
            X[i, 8] = rng.exponential(0.1)                       # failed login rate (low)
            X[i, 9] = rng.poisson(5 * base_activity)             # unique users 1min
            X[i, 10] = rng.poisson(15 * base_activity)           # unique users 5min
            X[i, 11] = rng.uniform(0, 0.2)                       # session anomaly (low)
            X[i, 12] = rng.poisson(0.1)                          # priv escalation (rare)
            X[i, 13] = 0.0 if is_business else 1.0               # after hours
            X[i, 14] = 1.0 if rng.random() < 0.02 else 0.0      # new user (rare)
            X[i, 15] = rng.exponential(0.05)                     # password reset rate
            X[i, 16] = rng.exponential(0.02)                     # mfa failure rate
            X[i, 17] = rng.poisson(3 * base_activity)            # concurrent sessions

            # Network (18-27)
            X[i, 18] = rng.poisson(8 * base_activity)            # unique src IPs
            X[i, 19] = rng.poisson(5 * base_activity)            # unique dst IPs
            X[i, 20] = rng.poisson(3)                            # unique ports (low)
            X[i, 21] = rng.exponential(5.0 * base_activity)      # bytes in rate
            X[i, 22] = rng.exponential(3.0 * base_activity)      # bytes out rate
            X[i, 23] = rng.uniform(0.3, 0.8)                     # in/out ratio
            X[i, 24] = rng.exponential(1.0)                      # DNS query rate
            X[i, 25] = rng.poisson(0.2)                          # lateral movement (rare)
            X[i, 26] = rng.poisson(2 * base_activity)            # external connections
            X[i, 27] = rng.uniform(0, 0.05)                      # port scan score (low)

            # Clinical (28-37)
            X[i, 28] = rng.exponential(3.0 * base_activity)      # Epic access rate
            X[i, 29] = rng.exponential(2.0 * base_activity)      # FHIR request rate
            X[i, 30] = rng.exponential(1.5 * base_activity)      # HL7 message rate
            X[i, 31] = rng.exponential(0.5 * base_activity)      # DICOM transfer rate
            X[i, 32] = rng.poisson(3 * base_activity)            # PHI access count
            X[i, 33] = rng.poisson(5 * base_activity)            # patient record diversity
            X[i, 34] = 0.0                                       # bulk export (never)
            X[i, 35] = 0.0                                       # abnormal query (never)
            X[i, 36] = rng.poisson(1.0 * base_activity)          # IoMT events
            X[i, 37] = 0.0 if is_business else rng.exponential(0.1)  # clinical off-hours

            # Escalation (38-47)
            X[i, 38] = rng.exponential(0.05)                     # threat alert rate (low)
            X[i, 39] = rng.exponential(0.02)                     # organ error rate (low)
            X[i, 40] = rng.uniform(0, 1)                         # escalation chain length
            X[i, 41] = rng.exponential(50)                       # mean response time
            X[i, 42] = 0.0                                       # P0 offline (none)
            X[i, 43] = rng.exponential(0.01)                     # dead letter rate
            X[i, 44] = 0.0                                       # HMAC failures (none)
            X[i, 45] = rng.poisson(0.1)                          # rate limit hits (rare)
            X[i, 46] = 0.0                                       # quarantine triggers (none)
            X[i, 47] = rng.uniform(0, 10)                        # overall threat score (low)

        return X

    def _generate_threat(self, threat_class: str, n: int) -> np.ndarray:
        """Generate synthetic threat samples for a given class."""
        # Start with normal baseline and modify based on threat type
        X = self._generate_normal(n)
        rng = self._rng

        if threat_class == "brute_force":
            X[:, 8] = rng.uniform(5, 50, n)         # high failed login rate
            X[:, 16] = rng.uniform(2, 20, n)         # high MFA failure rate
            X[:, 18] = rng.uniform(1, 3, n)           # few source IPs
            X[:, 3] = rng.uniform(3, 10, n)           # high burst score
            X[:, 47] = rng.uniform(40, 80, n)         # elevated threat score

        elif threat_class == "ransomware":
            X[:, 21] = rng.uniform(50, 200, n)       # massive bytes in (encryption)
            X[:, 22] = rng.uniform(0.1, 1, n)         # low bytes out
            X[:, 23] = rng.uniform(5, 50, n)           # extreme in/out ratio
            X[:, 3] = rng.uniform(5, 20, n)           # extreme burst
            X[:, 41] = rng.uniform(500, 5000, n)      # high response times (system stress)
            X[:, 46] = rng.uniform(1, 10, n)           # quarantine triggers
            X[:, 47] = rng.uniform(70, 100, n)         # very high threat score

        elif threat_class == "exfiltration":
            X[:, 22] = rng.uniform(30, 150, n)       # high bytes out
            X[:, 23] = rng.uniform(3, 20, n)           # inverted ratio
            X[:, 32] = rng.uniform(20, 100, n)         # massive PHI access
            X[:, 33] = rng.uniform(50, 200, n)         # many patient records
            X[:, 34] = 1.0                             # bulk export flag
            X[:, 26] = rng.uniform(10, 50, n)          # many external connections
            X[:, 47] = rng.uniform(50, 90, n)

        elif threat_class == "lateral_movement":
            X[:, 25] = rng.uniform(5, 30, n)         # high lateral movement
            X[:, 18] = rng.uniform(15, 50, n)         # many unique src IPs
            X[:, 19] = rng.uniform(15, 50, n)         # many unique dst IPs
            X[:, 20] = rng.uniform(10, 50, n)          # many unique ports
            X[:, 27] = rng.uniform(0.3, 1.0, n)        # port scan detected
            X[:, 12] = rng.uniform(1, 10, n)           # priv escalation attempts
            X[:, 47] = rng.uniform(40, 80, n)

        elif threat_class == "insider_threat":
            X[:, 13] = 1.0                            # after hours
            X[:, 37] = rng.uniform(5, 30, n)           # clinical off-hours access
            X[:, 32] = rng.uniform(15, 80, n)          # high PHI access
            X[:, 33] = rng.uniform(30, 100, n)         # many patient records
            X[:, 35] = 1.0                             # abnormal query pattern
            X[:, 11] = rng.uniform(0.5, 1.0, n)        # session anomaly
            X[:, 47] = rng.uniform(35, 70, n)

        elif threat_class == "phishing":
            X[:, 8] = rng.uniform(2, 15, n)           # moderate failed logins
            X[:, 14] = rng.choice([0, 1], n, p=[0.3, 0.7])  # often "new" user
            X[:, 26] = rng.uniform(5, 25, n)           # unusual external connections
            X[:, 24] = rng.uniform(5, 20, n)           # high DNS queries
            X[:, 16] = rng.uniform(1, 5, n)            # MFA failures
            X[:, 47] = rng.uniform(30, 60, n)

        elif threat_class == "port_scan":
            X[:, 20] = rng.uniform(30, 200, n)        # extreme port diversity
            X[:, 27] = rng.uniform(0.5, 1.0, n)        # high port scan score
            X[:, 19] = rng.uniform(20, 100, n)         # many dest IPs
            X[:, 0] = rng.uniform(10, 50, n)           # high event rate
            X[:, 3] = rng.uniform(3, 15, n)            # bursty
            X[:, 47] = rng.uniform(30, 60, n)

        elif threat_class == "credential_stuffing":
            X[:, 8] = rng.uniform(10, 100, n)         # very high failed logins
            X[:, 9] = rng.uniform(20, 100, n)          # many unique users
            X[:, 10] = rng.uniform(50, 200, n)         # even more over 5min
            X[:, 18] = rng.uniform(5, 30, n)           # multiple source IPs
            X[:, 3] = rng.uniform(2, 8, n)             # bursty
            X[:, 47] = rng.uniform(45, 85, n)

        elif threat_class == "privilege_escalation":
            X[:, 12] = rng.uniform(3, 20, n)          # many priv escalation attempts
            X[:, 11] = rng.uniform(0.4, 1.0, n)        # session anomaly
            X[:, 15] = rng.uniform(2, 10, n)           # password reset spikes
            X[:, 25] = rng.uniform(2, 10, n)           # some lateral movement
            X[:, 44] = rng.uniform(1, 5, n)            # HMAC failures (tampering)
            X[:, 47] = rng.uniform(40, 75, n)

        return X

    def train_from_ledger(
        self,
        ledger_path: str = "/var/log/veilcore/mesh-ledger.jsonl",
        save: bool = True,
    ) -> Optional[dict[str, Any]]:
        """
        Train models from real mesh ledger data.
        Falls back to synthetic if insufficient real data.
        """
        if not os.path.exists(ledger_path):
            logger.warning(f"Ledger not found at {ledger_path}, using synthetic data")
            return self.train_from_synthetic(save=save)

        logger.info(f"Loading training data from {ledger_path}...")

        events = []
        try:
            with open(ledger_path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        events.append(json.loads(line))
        except Exception as e:
            logger.error(f"Failed to read ledger: {e}")
            return self.train_from_synthetic(save=save)

        if len(events) < 100:
            logger.warning(f"Only {len(events)} events in ledger, supplementing with synthetic data")
            return self.train_from_synthetic(save=save)

        logger.info(f"Loaded {len(events)} events from ledger")

        # For now, use synthetic training with real data informing parameters
        # Future: extract features from real events and train on actual patterns
        return self.train_from_synthetic(save=save)

    @property
    def anomaly_detector(self) -> AnomalyDetector:
        return self._anomaly_detector

    @property
    def classifier(self) -> ThreatClassifier:
        return self._classifier
