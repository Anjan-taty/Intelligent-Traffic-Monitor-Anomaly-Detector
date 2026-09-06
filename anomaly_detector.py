import math
import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter
import numpy as np

logger = logging.getLogger("traffic_monitor.anomaly")

class BehavioralFeatureExtractor:
    """
    Extracts deep behavioral fingerprints from raw request sequences.
    Distinguishes sophisticated bots, scrapers, and volumetric attackers from human users.
    """
    @staticmethod
    def calculate_entropy(elements: List[str]) -> float:
        """Computes Shannon entropy: higher values mean high route dispersion (crawling/scraping)."""
        if not elements:
            return 0.0
        counts = Counter(elements)
        total = len(elements)
        entropy = 0.0
        for count in counts.values():
            p = count / total
            if p > 0:
                entropy -= p * math.log2(p)
        return round(entropy, 3)

    @staticmethod
    def extract_features(requests: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Calculates feature vector for a single IP from its recent request history.
        Each request item must contain: timestamp, endpoint, status_code, method, response_time_ms.
        """
        if not requests:
            return {
                "request_count": 0.0,
                "requests_per_sec": 0.0,
                "timing_jitter": 0.0,
                "endpoint_entropy": 0.0,
                "error_ratio": 0.0,
                "rate_limit_ratio": 0.0,
                "post_ratio": 0.0,
                "avg_latency": 0.0
            }

        count = len(requests)
        timestamps = sorted([r["timestamp"] for r in requests])
        duration = max(0.1, timestamps[-1] - timestamps[0]) if count > 1 else 1.0
        rps = count / duration

        # Inter-arrival times and jitter (standard deviation of deltas)
        if count > 1:
            intervals = [timestamps[i] - timestamps[i-1] for i in range(1, count)]
            timing_jitter = float(np.std(intervals))
        else:
            timing_jitter = 1.0  # single request has neutral jitter

        endpoints = [r["endpoint"] for r in requests]
        endpoint_entropy = BehavioralFeatureExtractor.calculate_entropy(endpoints)

        error_count = sum(1 for r in requests if r.get("status_code", 200) >= 400 and r.get("status_code", 200) != 429)
        rate_limit_count = sum(1 for r in requests if r.get("status_code", 200) == 429)
        post_count = sum(1 for r in requests if r.get("method", "GET").upper() in ["POST", "PUT", "DELETE"])
        avg_latency = float(np.mean([r.get("response_time_ms", 10.0) for r in requests]))

        return {
            "request_count": float(count),
            "requests_per_sec": round(rps, 2),
            "timing_jitter": round(timing_jitter, 3),
            "endpoint_entropy": round(endpoint_entropy, 3),
            "error_ratio": round(error_count / count, 3),
            "rate_limit_ratio": round(rate_limit_count / count, 3),
            "post_ratio": round(post_count / count, 3),
            "avg_latency": round(avg_latency, 2)
        }

class ExplainableAnomalyDetector:
    """
    Unsupervised Anomaly Detection utilizing Isolation Forest
    augmented with an Explainable AI (XAI) feature attribution layer.
    """
    FEATURE_NAMES = [
        "request_count",
        "requests_per_sec",
        "timing_jitter",
        "endpoint_entropy",
        "error_ratio",
        "rate_limit_ratio",
        "post_ratio"
    ]

    # Baseline human behavioral statistics for comparative XAI attribution
    BASELINE_STATS = {
        "requests_per_sec": {"mean": 0.4, "std": 0.3},
        "timing_jitter": {"mean": 2.5, "std": 1.2},
        "endpoint_entropy": {"mean": 0.6, "std": 0.4},
        "error_ratio": {"mean": 0.02, "std": 0.05},
        "rate_limit_ratio": {"mean": 0.0, "std": 0.01},
        "post_ratio": {"mean": 0.1, "std": 0.15}
    }

    def __init__(self):
        self.model = None
        self._init_model()

    def _init_model(self):
        """Initializes and pre-trains Isolation Forest with synthetic normal traffic baseline."""
        try:
            from sklearn.ensemble import IsolationForest

            # Generate synthetic normal baseline: ~500 typical user sessions
            np.random.seed(42)
            n_samples = 500
            normal_data = np.zeros((n_samples, len(self.FEATURE_NAMES)))
            
            # request_count: 5 to 30
            normal_data[:, 0] = np.random.uniform(5, 30, n_samples)
            # requests_per_sec: 0.1 to 1.5
            normal_data[:, 1] = np.random.exponential(scale=0.5, size=n_samples)
            # timing_jitter: 0.8 to 4.0 (human pauses)
            normal_data[:, 2] = np.random.normal(loc=2.5, scale=0.8, size=n_samples).clip(0.5, 6.0)
            # endpoint_entropy: 0.2 to 1.5 (visiting home, product, cart)
            normal_data[:, 3] = np.random.normal(loc=0.8, scale=0.4, size=n_samples).clip(0.1, 2.0)
            # error_ratio: low (< 5%)
            normal_data[:, 4] = np.random.exponential(scale=0.02, size=n_samples).clip(0.0, 0.15)
            # rate_limit_ratio: 0
            normal_data[:, 5] = 0.0
            # post_ratio: 0.0 to 0.2
            normal_data[:, 6] = np.random.beta(a=1, b=5, size=n_samples)

            self.model = IsolationForest(
                n_estimators=100,
                contamination=0.05,
                max_samples=256,
                random_state=42
            )
            self.model.fit(normal_data)
            logger.info("Isolation Forest anomaly detection model successfully initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize Isolation Forest: {e}")
            self.model = None

    def analyze_ip_history(self, ip: str, requests: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Evaluates an IP's recent request sequence.
        Returns None if normal, or an Anomaly Report dict if suspicious.
        """
        if len(requests) < 5:
            # Need minimum sample size to draw statistical significance
            return None

        features = BehavioralFeatureExtractor.extract_features(requests)
        
        # 1. Tier-1 Fast Heuristic Rules (Instant high-severity triggers)
        heuristic_anomaly = self._check_heuristic_rules(features)
        if heuristic_anomaly:
            return heuristic_anomaly

        # 2. Tier-2 Isolation Forest Machine Learning
        if self.model:
            vector = np.array([[features[name] for name in self.FEATURE_NAMES]])
            # decision_function gives negative score for anomalies, positive for normal
            decision_score = float(self.model.decision_function(vector)[0])
            
            # Map score to 0.0 (benign) - 1.0 (critical threat)
            threat_score = round(min(1.0, max(0.0, 0.5 - (decision_score * 2.2))), 3)

            if threat_score >= 0.65:
                # Flagged as anomaly: determine root cause and explainability
                anomaly_type, reason = self._explain_anomaly(features, threat_score)
                return {
                    "ip_address": ip,
                    "threat_score": threat_score,
                    "anomaly_type": anomaly_type,
                    "reason": reason,
                    "features": features
                }

        return None

    def _check_heuristic_rules(self, f: Dict[str, float]) -> Optional[Dict[str, Any]]:
        """Rule-based safety net for unambiguous attack patterns."""
        # Pattern A: Credential Brute-Forcing or Path Scanning
        if f["error_ratio"] >= 0.70 and f["request_count"] >= 10:
            return {
                "threat_score": 0.95,
                "anomaly_type": "Credential Brute-Force / Scan",
                "reason": f"High error failure rate ({int(f['error_ratio']*100)}%) across {int(f['request_count'])} requests.",
                "features": f
            }

        # Pattern B: Volumetric L7 DDoS
        if f["requests_per_sec"] >= 25.0:
            return {
                "threat_score": 0.98,
                "anomaly_type": "Volumetric Flood (L7 DDoS)",
                "reason": f"Extreme request velocity ({f['requests_per_sec']} RPS) exceeding gateway capacity.",
                "features": f
            }

        # Pattern C: Aggressive Catalog Scraper
        if f["endpoint_entropy"] >= 2.8 and f["timing_jitter"] <= 0.08 and f["request_count"] >= 15:
            return {
                "threat_score": 0.91,
                "anomaly_type": "Automated Web Scraper",
                "reason": f"Robotic cadence (jitter: {f['timing_jitter']}s) + high route dispersion (entropy: {f['endpoint_entropy']}).",
                "features": f
            }

        return None

    def _explain_anomaly(self, f: Dict[str, float], threat_score: float) -> Tuple[str, str]:
        """
        Explainable AI (XAI): Computes Z-score deviations against baseline to
        generate human-readable root-cause explanations for cybersecurity analysts.
        """
        deviations = []
        for feat, stats in self.BASELINE_STATS.items():
            val = f.get(feat, 0.0)
            z_score = (val - stats["mean"]) / (stats["std"] or 1.0)
            deviations.append((feat, val, z_score))

        # Sort by most unusual features (highest absolute Z-score)
        deviations.sort(key=lambda x: abs(x[2]), reverse=True)
        top_driver = deviations[0]

        anomaly_type = "Behavioral Anomaly"
        reasons = []

        if f["timing_jitter"] < 0.15 and f["request_count"] >= 10:
            reasons.append(f"Robotic cadence (jitter: {f['timing_jitter']}s)")
            anomaly_type = "Automated Bot"
        
        if f["endpoint_entropy"] > 2.2:
            reasons.append(f"High endpoint dispersion ({f['endpoint_entropy']} bits)")
            anomaly_type = "Web Scraper / Enumeration"

        if f["requests_per_sec"] > 5.0:
            reasons.append(f"Unusual velocity ({f['requests_per_sec']} RPS)")

        if f["error_ratio"] > 0.4:
            reasons.append(f"Elevated error rate ({int(f['error_ratio']*100)}%)")
            anomaly_type = "Brute-Force / Probe"

        if not reasons:
            reasons.append(f"Unusual deviation in {top_driver[0]} (val: {top_driver[1]})")

        explanation = " & ".join(reasons)
        return anomaly_type, explanation

# Singleton instance
anomaly_detector = ExplainableAnomalyDetector()
