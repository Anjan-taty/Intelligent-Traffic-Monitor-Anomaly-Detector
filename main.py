import os
import time
import json
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from collections import deque

from fastapi import FastAPI, Request, Response, Depends, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from database import engine, SessionLocal, init_db, get_db
import models
import schemas
from rate_limiter import rate_limiter
from anomaly_detector import anomaly_detector
from traffic_simulator import run_simulation

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("traffic_monitor.main")

app = FastAPI(
    title="Intelligent Traffic Monitor & Anomaly Detector",
    description="Enterprise API Gateway with Atomic Redis Rate Limiting, Explainable Anomaly Detection, and Real-time Telemetry.",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory real-time sliding window buffer for rapid feature extraction and telemetry
# ip -> deque of {"timestamp": float, "endpoint": str, "method": str, "status_code": int, "response_time_ms": float}
IP_REQUEST_HISTORY: Dict[str, deque] = {}
RECENT_LATENCIES: deque = deque(maxlen=200)
TRAFFIC_COUNTER: deque = deque(maxlen=60) # timestamps for rolling RPS calculation
WEBSOCKET_CLIENTS: List[WebSocket] = []

# Ensure tables exist
init_db()

# Mount static directory for the SOC Dashboard
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Helper to extract real IP even behind proxies / load balancers
def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"

# Telemetry broadcast manager
async def broadcast_telemetry(event_type: str, data: Dict[str, Any]):
    """Pushes real-time events to all connected SOC dashboard clients."""
    if not WEBSOCKET_CLIENTS:
        return
    message = json.dumps({"event": event_type, "data": data, "timestamp": time.time()})
    disconnected = []
    for client in WEBSOCKET_CLIENTS:
        try:
            await client.send_text(message)
        except Exception:
            disconnected.append(client)
    for dead in disconnected:
        if dead in WEBSOCKET_CLIENTS:
            WEBSOCKET_CLIENTS.remove(dead)

# Asynchronous Background Processing
def process_request_telemetry(
    ip: str, 
    method: str, 
    endpoint: str, 
    status_code: int, 
    response_time: float, 
    user_agent: Optional[str],
    is_blocked: bool
):
    """
    Decoupled analytics pipeline:
    1. Ingests request log to DB without blocking client response.
    2. Updates rolling behavioral feature history.
    3. Triggers explainable anomaly detection and adaptive mitigation.
    """
    now_ts = time.time()
    
    # 1. Update In-Memory Rolling History (for fast feature extraction)
    if ip not in IP_REQUEST_HISTORY:
        IP_REQUEST_HISTORY[ip] = deque(maxlen=100)
    
    q = IP_REQUEST_HISTORY[ip]
    q.append({
        "timestamp": now_ts,
        "endpoint": endpoint,
        "method": method,
        "status_code": status_code,
        "response_time_ms": response_time
    })
    
    # Prune events older than 300 seconds
    clear_before = now_ts - 300
    while q and q[0]["timestamp"] < clear_before:
        q.popleft()

    # 2. Persist to Database
    db = SessionLocal()
    try:
        log_entry = models.RequestLog(
            ip_address=ip,
            method=method,
            endpoint=endpoint,
            status_code=status_code,
            response_time_ms=response_time,
            user_agent=user_agent[:255] if user_agent else None,
            is_blocked=is_blocked
        )
        db.add(log_entry)
        db.commit()

        # 3. Anomaly Detection & Adaptive Defense
        # Analyze IP history if sufficient sample size
        anomaly_report = anomaly_detector.analyze_ip_history(ip, list(q))
        if anomaly_report:
            threat_score = anomaly_report["threat_score"]
            anomaly_type = anomaly_report["anomaly_type"]
            reason = anomaly_report["reason"]
            features = anomaly_report["features"]

            # Adaptive Mitigation: Demote or Block
            if threat_score >= 0.85:
                mitigation = "Quarantined (Blocked)"
                rate_limiter.block_ip(ip, duration_seconds=180, reason=reason)
            else:
                mitigation = "Throttled (Restricted Tier)"
                rate_limiter.throttle_ip(ip, duration_seconds=120)

            # Record Alert in DB (prevent duplicate alerts within 60s)
            recent_alert = db.query(models.AnomalyAlert).filter(
                models.AnomalyAlert.ip_address == ip,
                models.AnomalyAlert.timestamp >= datetime.now(timezone.utc) - timedelta(seconds=60)
            ).first()

            if not recent_alert:
                alert = models.AnomalyAlert(
                    ip_address=ip,
                    threat_score=threat_score,
                    anomaly_type=anomaly_type,
                    reason=reason,
                    metrics_snapshot=json.dumps(features),
                    mitigation_status=mitigation
                )
                db.add(alert)
                db.commit()

                # Notify SOC Dashboard via event loop
                asyncio.run_coroutine_threadsafe(
                    broadcast_telemetry("anomaly_detected", {
                        "ip": ip,
                        "threat_score": threat_score,
                        "anomaly_type": anomaly_type,
                        "reason": reason,
                        "mitigation": mitigation,
                        "features": features
                    }),
                    loop=main_event_loop
                )
    except Exception as e:
        logger.error(f"Error in telemetry background task: {e}")
        db.rollback()
    finally:
        db.close()

# Keep reference to main loop for background threadsafe scheduling
main_event_loop = None

@app.on_event("startup")
async def startup_event():
    global main_event_loop
    main_event_loop = asyncio.get_running_loop()
    logger.info("Gateway & Anomaly Monitor starting up...")

# ==========================================
# REVERSE PROXY & RATE LIMITING MIDDLEWARE
# ==========================================
@app.middleware("http")
async def gateway_security_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    ip = get_client_ip(request)
    path = request.url.path
    method = request.method
    user_agent = request.headers.get("User-Agent", "")

    # Exclude static assets and SOC dashboard from rate limits
    if path.startswith("/static") or path == "/" or path.startswith("/ws"):
        return await call_next(request)

    # 1. Rate Limit Enforcement (Sub-millisecond fast path)
    allowed, remaining, retry_after = rate_limiter.check_rate_limit(ip)

    if not allowed:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        
        # Async background log
        asyncio.get_running_loop().run_in_executor(
            None, process_request_telemetry, ip, method, path, 429, duration_ms, user_agent, True
        )
        
        return JSONResponse(
            status_code=429,
            content={
                "error": "Too Many Requests",
                "message": "Gateway rate limit exceeded or IP is under adaptive security throttle.",
                "retry_after_seconds": retry_after
            },
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Remaining": "0"
            }
        )

    # 2. Forward request to route handler
    try:
        response: Response = await call_next(request)
        status_code = response.status_code
    except Exception as exc:
        status_code = 500
        response = JSONResponse(status_code=500, content={"error": "Internal Gateway Error"})

    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
    RECENT_LATENCIES.append(duration_ms)
    TRAFFIC_COUNTER.append(time.time())

    # Add security & rate limit headers
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-Response-Time"] = f"{duration_ms}ms"

    # 3. Offload logging and ML analysis to background executor (Zero latency addition)
    asyncio.get_running_loop().run_in_executor(
        None, process_request_telemetry, ip, method, path, status_code, duration_ms, user_agent, False
    )

    return response

# ==========================================
# DASHBOARD & WEBSOCKET ENDPOINTS
# ==========================================
@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Serves the Cyber SOC Command Center UI."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h2>SOC Dashboard initializing... Please refresh shortly.</h2>")

@app.websocket("/ws/telemetry")
async def websocket_telemetry_feed(websocket: WebSocket):
    """Streams live RPS, latency, and telemetry updates to dashboard clients."""
    await websocket.accept()
    WEBSOCKET_CLIENTS.append(websocket)
    try:
        while True:
            # Send periodic pulse every second
            now = time.time()
            one_sec_ago = now - 1.0
            rps = sum(1 for ts in TRAFFIC_COUNTER if ts >= one_sec_ago)
            avg_latency = float(np.mean(RECENT_LATENCIES)) if RECENT_LATENCIES else 0.0
            p95_latency = float(np.percentile(RECENT_LATENCIES, 95)) if RECENT_LATENCIES else 0.0

            pulse = {
                "rps": rps,
                "avg_latency": round(avg_latency, 2),
                "p95_latency": round(p95_latency, 2),
                "active_connections": len(WEBSOCKET_CLIENTS)
            }
            await websocket.send_text(json.dumps({"event": "telemetry_pulse", "data": pulse}))
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        if websocket in WEBSOCKET_CLIENTS:
            WEBSOCKET_CLIENTS.remove(websocket)
    except Exception:
        if websocket in WEBSOCKET_CLIENTS:
            WEBSOCKET_CLIENTS.remove(websocket)

# ==========================================
# MANAGEMENT & TELEMETRY REST APIS
# ==========================================
@app.get("/api/stats", response_model=schemas.SystemStats)
def get_system_stats(db: Session = Depends(get_db)):
    """Aggregates real-time system performance and security metrics."""
    total_reqs = db.query(func.count(models.RequestLog.id)).scalar() or 0
    blocked_reqs = db.query(func.count(models.RequestLog.id)).filter(models.RequestLog.is_blocked == True).scalar() or 0
    active_threats = db.query(func.count(models.AnomalyAlert.id)).scalar() or 0

    avg_lat = float(np.mean(RECENT_LATENCIES)) if RECENT_LATENCIES else 0.0
    p95_lat = float(np.percentile(RECENT_LATENCIES, 95)) if RECENT_LATENCIES else 0.0

    now = time.time()
    current_rps = float(sum(1 for ts in TRAFFIC_COUNTER if ts >= now - 1.0))

    # Status distribution
    status_counts = db.query(models.RequestLog.status_code, func.count(models.RequestLog.id)).group_by(models.RequestLog.status_code).all()
    status_dist = {str(code): count for code, count in status_counts}

    # Top endpoints
    top_paths = db.query(models.RequestLog.endpoint, func.count(models.RequestLog.id).label("cnt")).group_by(models.RequestLog.endpoint).order_by(desc("cnt")).limit(5).all()
    top_endpoints = [{"endpoint": ep, "count": cnt} for ep, cnt in top_paths]

    # Recent alerts
    recent_alerts = db.query(models.AnomalyAlert).order_by(desc(models.AnomalyAlert.timestamp)).limit(10).all()

    return schemas.SystemStats(
        total_requests=total_reqs,
        total_blocked=blocked_reqs,
        active_threats=active_threats,
        avg_response_time_ms=round(avg_lat, 2),
        p95_response_time_ms=round(p95_lat, 2),
        current_rps=round(current_rps, 1),
        status_code_distribution=status_dist,
        top_endpoints=top_endpoints,
        recent_alerts=recent_alerts
    )

@app.get("/api/alerts", response_model=List[schemas.AnomalyAlertResponse])
def get_alerts(limit: int = 20, db: Session = Depends(get_db)):
    return db.query(models.AnomalyAlert).order_by(desc(models.AnomalyAlert.timestamp)).limit(limit).all()

@app.get("/api/logs", response_model=List[schemas.RequestLogResponse])
def get_logs(limit: int = 30, db: Session = Depends(get_db)):
    return db.query(models.RequestLog).order_by(desc(models.RequestLog.timestamp)).limit(limit).all()

@app.post("/api/simulate", response_model=schemas.SimulationResponse)
def trigger_simulation(payload: schemas.SimulationRequest, background_tasks: BackgroundTasks):
    """Triggers realistic traffic simulations (human, scraper, ddos, bruteforce) for demonstration."""
    res = run_simulation(payload.scenario, count=payload.requests_count, concurrency=payload.concurrency)
    return schemas.SimulationResponse(
        status="completed",
        scenario=res["scenario"],
        total_sent=res["total"],
        successful=res["success"],
        blocked=res["blocked"],
        duration_seconds=res["duration"]
    )

# ==========================================
# MOCK APPLICATION TARGET ENDPOINTS
# ==========================================
@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "Intelligent Traffic Monitor", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.get("/api/products")
def list_products():
    return [
        {"id": i, "name": f"Enterprise Cloud Node {i}", "price": 199.99 * i, "status": "active"}
        for i in range(1, 11)
    ]

@app.get("/api/products/{item_id}")
def get_product(item_id: int):
    if item_id > 100:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"id": item_id, "name": f"Enterprise Cloud Node {item_id}", "price": 299.00, "in_stock": True}

@app.get("/api/search")
def search_catalog(q: str = ""):
    return {"query": q, "results": [f"Result item matching '{q}' #{i}" for i in range(1, 4)]}

@app.get("/api/cart")
def view_cart():
    return {"items": [{"item_id": 1, "qty": 2}], "subtotal": 399.98}

@app.post("/api/cart")
def add_to_cart(data: Dict[str, Any]):
    return {"message": "Item added to cart", "cart_id": "c-98213", "data": data}

@app.post("/api/login")
def mock_login(credentials: Dict[str, str]):
    """Simulated login endpoint. Fails on incorrect credentials to allow brute-force detection."""
    user = credentials.get("username")
    pwd = credentials.get("password")
    if user == "admin" and pwd == "supersecret2026!":
        return {"status": "authenticated", "token": "jwt-token-xyz-123"}
    raise HTTPException(status_code=401, detail="Invalid username or password")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
