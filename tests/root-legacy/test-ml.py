#!/usr/bin/env python3
"""
VeilCore ML — Smoke Test
=========================
Trains models on synthetic data, runs predictions, verifies
the full pipeline: features → anomaly detection → classification → scoring.

Usage:
    sudo python3 /opt/veilcore/test-ml.py
"""

import sys
import os
import logging
import time

sys.path.insert(0, "/opt/veilcore")

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("ml-test")


def run_test():
    logger.info("=" * 60)
    logger.info("  VEILCORE ML — SMOKE TEST")
    logger.info("=" * 60)

    # ── Test 1: Feature Extraction
    logger.info("\n── Test 1: Feature Extraction")
    from core.ml.features import FeatureExtractor, FEATURE_DIM

    extractor = FeatureExtractor()

    # Simulate normal events
    for i in range(50):
        extractor.ingest({
            "event_type": "epic_access",
            "username": f"nurse_{i % 5}",
            "source_ip": f"10.0.1.{i % 20}",
            "patient_id": f"PAT-{i % 10}",
        })

    features = extractor.extract()
    assert features.shape == (FEATURE_DIM,), f"Expected ({FEATURE_DIM},), got {features.shape}"
    assert not np.any(np.isnan(features)), "NaN in features"
    logger.info(f"✓ Feature extraction: {FEATURE_DIM} features, no NaN")

    # ── Test 2: Model Training
    logger.info("\n── Test 2: Model Training (synthetic data)")
    from core.ml.trainer import ModelTrainer

    trainer = ModelTrainer()
    metrics = trainer.train_from_synthetic(
        n_normal=2000,
        n_threat_per_class=100,
        save=True,
    )

    assert metrics["anomaly_detector"]["separation"] > 0, "Anomaly detector has no separation"
    assert metrics["classifier"]["cv_f1_mean"] > 0.5, "Classifier F1 too low"
    logger.info(f"✓ Training complete")
    logger.info(f"  Anomaly separation: {metrics['anomaly_detector']['separation']:.4f}")
    logger.info(f"  Classifier F1: {metrics['classifier']['cv_f1_mean']:.3f}")

    # ── Test 3: Anomaly Detection
    logger.info("\n── Test 3: Anomaly Detection")
    from core.ml.models import AnomalyDetector

    detector = AnomalyDetector()
    assert detector.load(), "Failed to load anomaly detector"

    # Normal sample should not be anomalous
    normal_features = trainer._generate_normal(1)[0]
    is_anomaly, score = detector.predict(normal_features)
    logger.info(f"  Normal sample: anomaly={is_anomaly}, score={score:.4f}")

    # Threat sample should be anomalous
    threat_features = trainer._generate_threat("ransomware", 1)[0]
    is_anomaly_t, score_t = detector.predict(threat_features)
    logger.info(f"  Threat sample: anomaly={is_anomaly_t}, score={score_t:.4f}")
    assert score_t < score, "Threat should score lower (more anomalous) than normal"
    logger.info("✓ Anomaly detection working (threat scores lower than normal)")

    # ── Test 4: Threat Classification
    logger.info("\n── Test 4: Threat Classification")
    from core.ml.models import ThreatClassifier

    classifier = ThreatClassifier()
    assert classifier.load(), "Failed to load threat classifier"

    threat_class, probs, confidence = classifier.predict(threat_features)
    logger.info(f"  Classified as: {threat_class} (confidence: {confidence:.2f})")
    logger.info(f"  Top 3 probabilities:")
    sorted_probs = sorted(probs.items(), key=lambda x: x[1], reverse=True)[:3]
    for cls, prob in sorted_probs:
        logger.info(f"    {cls}: {prob:.3f}")
    assert confidence > 0, "Classification confidence should be > 0"
    logger.info("✓ Threat classification working")

    # ── Test 5: Full Predictor Pipeline
    logger.info("\n── Test 5: Full Predictor Pipeline")
    from core.ml.predictor import ThreatPredictor

    predictor = ThreatPredictor()
    # Load models manually (no mesh connection needed for test)
    predictor._anomaly_detector.load()
    predictor._classifier.load()

    # Ingest simulated brute force attack
    for i in range(100):
        predictor.ingest_event({
            "event_type": "failed_login",
            "username": "admin",
            "source_ip": "192.168.1.99",
            "port": 22,
        })

    result = predictor.predict_current()
    logger.info(f"  Prediction: anomaly={result.is_anomaly}, class={result.threat_class}")
    logger.info(f"  Confidence: {result.confidence:.2f}, severity={result.severity}")
    logger.info(f"  Time: {result.prediction_time_ms:.2f}ms")
    logger.info("✓ Predictor pipeline working")

    # ── Test 6: Threat Scorer
    logger.info("\n── Test 6: Composite Threat Scoring")
    from core.ml.threat_scorer import ThreatScorer

    scorer = ThreatScorer()

    # Score normal state
    normal_result = predictor.predict_features(normal_features)
    normal_score = scorer.score(normal_features, normal_result)
    logger.info(f"  Normal score: {normal_score.score:.1f}/100 ({normal_score.severity})")

    # Score threat state
    threat_result = predictor.predict_features(threat_features)
    threat_score = scorer.score(threat_features, threat_result)
    logger.info(f"  Threat score: {threat_score.score:.1f}/100 ({threat_score.severity})")
    logger.info(f"  Contributing factors:")
    for factor in threat_score.contributing_factors[:5]:
        logger.info(f"    • {factor}")
    logger.info(f"  Recommended actions:")
    for action in threat_score.recommended_actions[:3]:
        logger.info(f"    → {action}")

    assert threat_score.score > normal_score.score, "Threat should score higher than normal"
    logger.info("✓ Threat scoring working (threat > normal)")

    # ── Test 7: Model Persistence
    logger.info("\n── Test 7: Model Persistence")
    assert os.path.exists("/var/lib/veilcore/models/anomaly_detector.joblib"), "Anomaly model not saved"
    assert os.path.exists("/var/lib/veilcore/models/threat_classifier.joblib"), "Classifier not saved"
    logger.info("✓ Models saved to /var/lib/veilcore/models/")

    # ── Summary
    logger.info("\n" + "=" * 60)
    logger.info("  ✅ ALL ML TESTS PASSED")
    logger.info("=" * 60)
    logger.info("")
    logger.info("  Models trained and saved to /var/lib/veilcore/models/")
    logger.info("  Feature vector: 48 dimensions")
    logger.info(f"  Anomaly separation: {metrics['anomaly_detector']['separation']:.4f}")
    logger.info(f"  Classifier F1: {metrics['classifier']['cv_f1_mean']:.3f}")
    logger.info(f"  Threat classes: {len(classifier.classes)}")
    logger.info("")
    logger.info("  The predictive cortex is ready.")
    logger.info("  I stand between chaos and those I protect.")
    logger.info("")


if __name__ == "__main__":
    try:
        run_test()
    except AssertionError as e:
        logger.error(f"❌ TEST FAILED: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Test interrupted")
        sys.exit(0)
