"""
VeilCore ML Threat Prediction Engine
=====================================
The predictive cortex of VeilCore — analyzes patterns across all 82
organ data streams to predict threats before they fully materialize.

Models:
    - Isolation Forest: Anomaly detection on behavioral baselines
    - Random Forest: Threat classification (brute_force, ransomware,
      exfiltration, lateral_movement, insider_threat, phishing)
    - Statistical: Time-series trend prediction for escalation forecasting

Integrates with the Mesh via MeshClient to receive real-time events
and publish threat predictions to topic:threat_alerts.

Author: Future Ready
System: VeilCore Hospital Cybersecurity Defense
"""

__version__ = "1.0.0"
__codename__ = "PredictiveCortex"

from core.ml.features import FeatureExtractor
from core.ml.models import AnomalyDetector, ThreatClassifier
from core.ml.predictor import ThreatPredictor
from core.ml.trainer import ModelTrainer
from core.ml.threat_scorer import ThreatScorer

__all__ = [
    "FeatureExtractor",
    "AnomalyDetector",
    "ThreatClassifier",
    "ThreatPredictor",
    "ModelTrainer",
    "ThreatScorer",
]
