import time
from fastapi.testclient import TestClient
from main import app, IP_REQUEST_HISTORY
from database import Base, engine, SessionLocal
import models
from rate_limiter import InMemorySlidingWindow, rate_limiter
from anomaly_detector import BehavioralFeatureExtractor, ExplainableAnomalyDetector

client = TestClient(app)

def test_database_tables_exist():
    """Verify tables can be queried without error."""
    db = SessionLocal()
    try:
        count = db.query(models.RequestLog).count()
        assert count >= 0
    finally:
        db.close()

def test_sliding_window_rate_limiter():
    """Verify that requests exceeding window limit trigger 429 block."""
    limiter = InMemorySlidingWindow()
    test_ip = "192.168.99.1"
    limit = 5
    window = 10.0

    # First 5 should succeed
    for i in range(limit):
        allowed, remaining, retry = limiter.check(test_ip, limit=limit, window_seconds=window)
        assert allowed is True
        assert remaining == limit - (i + 1)

    # 6th request should fail
    allowed, remaining, retry = limiter.check(test_ip, limit=limit, window_seconds=window)
    assert allowed is False
    assert remaining == 0
    assert retry > 0

def test_feature_extractor_metrics():
    """Verify entropy and jitter calculation."""
    # Test high entropy (varied paths)
    varied_endpoints = [f"/path/{i}" for i in range(10)]
    entropy_high = BehavioralFeatureExtractor.calculate_entropy(varied_endpoints)
    assert entropy_high > 2.0

    # Test zero entropy (same path)
    single_endpoint = ["/path/1"] * 10
    entropy_zero = BehavioralFeatureExtractor.calculate_entropy(single_endpoint)
    assert entropy_zero == 0.0

    # Test timing jitter
    requests = [
        {"timestamp": 100.0 + (i * 0.02), "endpoint": f"/p/{i}", "status_code": 200, "method": "GET", "response_time_ms": 10.0}
        for i in range(10)
    ]
    features = BehavioralFeatureExtractor.extract_features(requests)
    assert features["timing_jitter"] < 0.05  # Near zero jitter = robotic
    assert features["requests_per_sec"] > 10.0

def test_anomaly_detector_scoring():
    """Verify explainable anomaly detector identifies scraper / robotic pattern."""
    detector = ExplainableAnomalyDetector()

    # Simulate scraper pattern: fixed 0.01s delays, varied paths
    requests = [
        {"timestamp": 100.0 + (i * 0.01), "endpoint": f"/catalog/item/{i}", "status_code": 200, "method": "GET", "response_time_ms": 5.0}
        for i in range(25)
    ]
    report = detector.analyze_ip_history("10.0.0.99", requests)
    assert report is not None
    assert report["threat_score"] >= 0.70
    assert "reason" in report
    assert len(report["reason"]) > 5

def test_gateway_health_endpoint():
    """Verify public health endpoint returns 200."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_gateway_product_endpoints():
    """Verify mock product endpoints return expected schema."""
    response = client.get("/api/products")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) > 0

if __name__ == "__main__":
    print("Running system sanity checks...")
    test_database_tables_exist()
    print("  [PASS] Database tables OK")
    test_sliding_window_rate_limiter()
    print("  [PASS] Sliding Window Rate Limiter OK")
    test_feature_extractor_metrics()
    print("  [PASS] Behavioral Feature Extractor OK")
    test_anomaly_detector_scoring()
    print("  [PASS] Explainable Anomaly Detector OK")
    test_gateway_health_endpoint()
    print("  [PASS] Gateway Health Endpoint OK")
    test_gateway_product_endpoints()
    print("  [PASS] Gateway Product Endpoints OK")
    print("\nALL SANITY TESTS PASSED SUCCESSFULLY!")
