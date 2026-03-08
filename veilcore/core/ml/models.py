"""
VeilCore ML Models
===================
Two-stage threat detection:

Stage 1 — Anomaly Detection (Isolation Forest):
    Unsupervised. Learns "normal" hospital network behavior from
    baseline feature vectors. Flags deviations as anomalies with
    a score from -1 (most anomalous) to +1 (most normal).

Stage 2 — Threat Classification (Random Forest):
    Supervised. When an anomaly is detected, classifies the threat
    type: brute_force, ransomware, exfiltration, lateral_movement,
    insider_threat, phishing, port_scan, or benign.

Both models are serialized with joblib for fast load/save and
are stored at /var/lib/veilcore/models/.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import numpy as np

logger = logging.getLogger("veilcore.ml.models")

MODEL_DIR = "/var/lib/veilcore/models"

THREAT_CLASSES = [
    "benign",
    "brute_force",
    "ransomware",
    "exfiltration",
    "lateral_movement",
    "insider_threat",
    "phishing",
    "port_scan",
    "credential_stuffing",
    "privilege_escalation",
]


@dataclass
class PredictionResult:
    """Result from anomaly detection or threat classification."""
    is_anomaly: bool = False
    anomaly_score: float = 0.0          # -1 to 1 (lower = more anomalous)
    threat_class: str = "benign"
    threat_probabilities: dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0             # 0 to 1
    features_used: int = 0
    prediction_time_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def is_threat(self) -> bool:
        return self.is_anomaly and self.threat_class != "benign"

    @property
    def severity(self) -> str:
        if not self.is_anomaly:
            return "none"
        if self.confidence >= 0.85:
            return "critical"
        if self.confidence >= 0.65:
            return "high"
        if self.confidence >= 0.45:
            return "medium"
        return "low"

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_anomaly": self.is_anomaly,
            "anomaly_score": round(self.anomaly_score, 4),
            "threat_class": self.threat_class,
            "threat_probabilities": {k: round(v, 4) for k, v in self.threat_probabilities.items()},
            "confidence": round(self.confidence, 4),
            "severity": self.severity,
            "is_threat": self.is_threat,
            "features_used": self.features_used,
            "prediction_time_ms": round(self.prediction_time_ms, 2),
            "timestamp": self.timestamp,
        }


class AnomalyDetector:
    """
    Stage 1: Isolation Forest anomaly detection.

    Learns baseline "normal" behavior and flags deviations.
    Runs unsupervised — no labeled data required.

    Usage:
        detector = AnomalyDetector()
        detector.fit(baseline_features)  # shape (n_samples, 48)
        result = detector.predict(feature_vector)  # shape (48,)
    """

    def __init__(
        self,
        contamination: float = 0.05,
        n_estimators: int = 200,
        max_samples: str = "auto",
        random_state: int = 42,
    ):
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.max_samples = max_samples
        self.random_state = random_state
        self._model = None
        self._fitted = False
        self._fit_timestamp: Optional[str] = None
        self._n_training_samples: int = 0
        self._feature_means: Optional[np.ndarray] = None
        self._feature_stds: Optional[np.ndarray] = None

    def fit(self, X: np.ndarray) -> None:
        """
        Fit the anomaly detector on baseline (normal) feature vectors.
        X shape: (n_samples, 48)
        """
        from sklearn.ensemble import IsolationForest

        logger.info(f"Training anomaly detector on {X.shape[0]} samples, {X.shape[1]} features...")
        start = time.monotonic()

        # Store normalization stats
        self._feature_means = np.mean(X, axis=0)
        self._feature_stds = np.std(X, axis=0) + 1e-8  # avoid div by zero

        # Normalize
        X_norm = (X - self._feature_means) / self._feature_stds

        self._model = IsolationForest(
            contamination=self.contamination,
            n_estimators=self.n_estimators,
            max_samples=self.max_samples,
            random_state=self.random_state,
            n_jobs=-1,
        )
        self._model.fit(X_norm)
        self._fitted = True
        self._fit_timestamp = datetime.now(timezone.utc).isoformat()
        self._n_training_samples = X.shape[0]

        elapsed = (time.monotonic() - start) * 1000
        logger.info(f"Anomaly detector trained in {elapsed:.1f}ms")

    def predict(self, features: np.ndarray) -> tuple[bool, float]:
        """
        Predict if a feature vector is anomalous.
        Returns (is_anomaly, anomaly_score).
        Score: -1 = most anomalous, +1 = most normal.
        """
        if not self._fitted:
            return False, 0.0

        features_norm = (features - self._feature_means) / self._feature_stds
        X = features_norm.reshape(1, -1)

        score = self._model.score_samples(X)[0]
        prediction = self._model.predict(X)[0]
        is_anomaly = prediction == -1

        return is_anomaly, float(score)

    def save(self, path: Optional[str] = None) -> str:
        """Save model to disk."""
        import joblib
        path = path or os.path.join(MODEL_DIR, "anomaly_detector.joblib")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = {
            "model": self._model,
            "feature_means": self._feature_means,
            "feature_stds": self._feature_stds,
            "contamination": self.contamination,
            "n_estimators": self.n_estimators,
            "fit_timestamp": self._fit_timestamp,
            "n_training_samples": self._n_training_samples,
        }
        joblib.dump(data, path)
        logger.info(f"Anomaly detector saved to {path}")
        return path

    def load(self, path: Optional[str] = None) -> bool:
        """Load model from disk."""
        import joblib
        path = path or os.path.join(MODEL_DIR, "anomaly_detector.joblib")
        if not os.path.exists(path):
            logger.warning(f"Model file not found: {path}")
            return False
        data = joblib.load(path)
        self._model = data["model"]
        self._feature_means = data["feature_means"]
        self._feature_stds = data["feature_stds"]
        self.contamination = data.get("contamination", self.contamination)
        self._fit_timestamp = data.get("fit_timestamp")
        self._n_training_samples = data.get("n_training_samples", 0)
        self._fitted = True
        logger.info(f"Anomaly detector loaded from {path} (trained on {self._n_training_samples} samples)")
        return True

    @property
    def is_fitted(self) -> bool:
        return self._fitted


class ThreatClassifier:
    """
    Stage 2: Random Forest threat classification.

    Given an anomalous feature vector, classifies the threat type.
    Requires labeled training data.

    Usage:
        classifier = ThreatClassifier()
        classifier.fit(X_train, y_train)  # y = threat class labels
        result = classifier.predict(feature_vector)
    """

    def __init__(
        self,
        n_estimators: int = 300,
        max_depth: Optional[int] = 20,
        min_samples_leaf: int = 5,
        random_state: int = 42,
    ):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.min_samples_leaf = min_samples_leaf
        self.random_state = random_state
        self._model = None
        self._fitted = False
        self._fit_timestamp: Optional[str] = None
        self._n_training_samples: int = 0
        self._classes: list[str] = []
        self._feature_importances: Optional[np.ndarray] = None
        self._feature_means: Optional[np.ndarray] = None
        self._feature_stds: Optional[np.ndarray] = None

    def fit(self, X: np.ndarray, y: np.ndarray) -> dict[str, Any]:
        """
        Train the threat classifier.
        X shape: (n_samples, 48)
        y: array of threat class labels (strings from THREAT_CLASSES)
        Returns training metrics.
        """
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import cross_val_score

        logger.info(f"Training threat classifier on {X.shape[0]} samples...")
        start = time.monotonic()

        # Store normalization stats
        self._feature_means = np.mean(X, axis=0)
        self._feature_stds = np.std(X, axis=0) + 1e-8

        X_norm = (X - self._feature_means) / self._feature_stds

        self._model = RandomForestClassifier(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            min_samples_leaf=self.min_samples_leaf,
            random_state=self.random_state,
            class_weight="balanced",
            n_jobs=-1,
        )
        self._model.fit(X_norm, y)
        self._fitted = True
        self._fit_timestamp = datetime.now(timezone.utc).isoformat()
        self._n_training_samples = X.shape[0]
        self._classes = list(self._model.classes_)
        self._feature_importances = self._model.feature_importances_

        # Cross-validation score
        cv_scores = cross_val_score(self._model, X_norm, y, cv=min(5, X.shape[0]), scoring="f1_weighted")

        elapsed = (time.monotonic() - start) * 1000

        metrics = {
            "n_samples": X.shape[0],
            "n_classes": len(self._classes),
            "classes": self._classes,
            "cv_f1_mean": float(np.mean(cv_scores)),
            "cv_f1_std": float(np.std(cv_scores)),
            "training_time_ms": round(elapsed, 1),
            "top_features": self._get_top_features(10),
        }

        logger.info(
            f"Threat classifier trained in {elapsed:.1f}ms | "
            f"CV F1: {metrics['cv_f1_mean']:.3f} ± {metrics['cv_f1_std']:.3f}"
        )
        return metrics

    def predict(self, features: np.ndarray) -> tuple[str, dict[str, float], float]:
        """
        Classify a threat from a feature vector.
        Returns (threat_class, probabilities_dict, confidence).
        """
        if not self._fitted:
            return "benign", {}, 0.0

        features_norm = (features - self._feature_means) / self._feature_stds
        X = features_norm.reshape(1, -1)

        probabilities = self._model.predict_proba(X)[0]
        predicted_class = self._classes[np.argmax(probabilities)]
        confidence = float(np.max(probabilities))

        prob_dict = {cls: float(prob) for cls, prob in zip(self._classes, probabilities)}

        return predicted_class, prob_dict, confidence

    def _get_top_features(self, n: int = 10) -> list[dict[str, Any]]:
        """Get the top N most important features."""
        if self._feature_importances is None:
            return []
        from core.ml.features import FEATURE_NAMES
        indices = np.argsort(self._feature_importances)[::-1][:n]
        return [
            {"name": FEATURE_NAMES[i], "importance": round(float(self._feature_importances[i]), 4)}
            for i in indices
        ]

    def save(self, path: Optional[str] = None) -> str:
        """Save model to disk."""
        import joblib
        path = path or os.path.join(MODEL_DIR, "threat_classifier.joblib")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = {
            "model": self._model,
            "feature_means": self._feature_means,
            "feature_stds": self._feature_stds,
            "classes": self._classes,
            "feature_importances": self._feature_importances,
            "n_estimators": self.n_estimators,
            "max_depth": self.max_depth,
            "fit_timestamp": self._fit_timestamp,
            "n_training_samples": self._n_training_samples,
        }
        joblib.dump(data, path)
        logger.info(f"Threat classifier saved to {path}")
        return path

    def load(self, path: Optional[str] = None) -> bool:
        """Load model from disk."""
        import joblib
        path = path or os.path.join(MODEL_DIR, "threat_classifier.joblib")
        if not os.path.exists(path):
            logger.warning(f"Model file not found: {path}")
            return False
        data = joblib.load(path)
        self._model = data["model"]
        self._feature_means = data["feature_means"]
        self._feature_stds = data["feature_stds"]
        self._classes = data.get("classes", [])
        self._feature_importances = data.get("feature_importances")
        self._fit_timestamp = data.get("fit_timestamp")
        self._n_training_samples = data.get("n_training_samples", 0)
        self._fitted = True
        logger.info(f"Threat classifier loaded from {path} (trained on {self._n_training_samples} samples)")
        return True

    @property
    def is_fitted(self) -> bool:
        return self._fitted

    @property
    def classes(self) -> list[str]:
        return list(self._classes)
