# Intelligent Traffic Monitor & Anomaly Detector

A reverse proxy gateway built in Python that intercepts all incoming HTTP traffic, logs request metadata to PostgreSQL, enforces per-IP rate limiting using Redis, and detects abnormal traffic patterns using an Isolation Forest machine learning model.

The system is inspired by how companies like Akamai protect web servers from bots, scrapers, and DDoS attacks — by sitting between the internet and the origin server and acting as a smart gatekeeper.

---

## What Problem Does This Solve

When a web server is exposed to the internet, three threats are common:

- **Bot attacks** — scripts sending thousands of requests to brute-force login endpoints
- **Scrapers** — automated programs stealing data by visiting every page repeatedly
- **Traffic spikes** — sudden surges overwhelming the server

This gateway detects and blocks all three automatically.

---

## How It Works

```
Incoming Request
      ↓
FastAPI Middleware intercepts it
      ↓
Redis Check → Has this IP exceeded rate limit?
      ├── YES → Return 429 Too Many Requests
      └── NO  → Continue
      ↓
Forward to route handler
      ↓
Log to PostgreSQL (ip, endpoint, method, status, response_time)
      ↓
Return response to user

Every Hour (Background):
PostgreSQL logs → Feature extraction → Isolation Forest → Flag suspicious IPs
```

---

## Features

- **Request Logging** — Every request is logged with IP address, endpoint, HTTP method, status code, response time in milliseconds, and timestamp
- **Rate Limiting** — Two algorithms implemented: Token Bucket (allows short bursts) and Sliding Window (strict rolling window) — both stored in Redis for sub-millisecond checks
- **ML Anomaly Detection** — Isolation Forest model trained on behavioral features per IP — flags bots and scrapers automatically without labeled data
- **Live Dashboard** — Real-time traffic visualization over WebSocket showing request rates, top IPs, and flagged suspicious activity
- **Dockerized** — Entire stack runs with one command using Docker Compose

---

## Architecture

```
traffic_monitor/
│
├── main.py           # FastAPI app — routes, middleware, WebSocket
├── database.py       # PostgreSQL connection — engine, session, Base
├── models.py         # SQLAlchemy table definitions
├── schemas.py        # Pydantic models for API input/output
├── rate_limiter.py   # Token Bucket + Sliding Window (Redis)
├── anomaly.py        # Isolation Forest training and scoring
├── dashboard/
│   └── index.html    # Live traffic dashboard (Chart.js + WebSocket)
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## Technologies Used

| Layer | Technology | Why |
|---|---|---|
| API Framework | FastAPI | Async-first, automatic OpenAPI docs |
| Database | PostgreSQL | Structured logs, indexed queries |
| Cache / Rate Limiter | Redis | In-memory, sub-millisecond per-request checks |
| ML Model | Scikit-learn IsolationForest | Unsupervised anomaly detection, no labeled data needed |
| Containerization | Docker + Docker Compose | One command setup, consistent across environments |
| Scheduling | APScheduler | Background model retraining every hour |
| Dashboard | HTML + Chart.js + WebSocket | Real-time traffic visualization |

---

## Design Decisions

**Why Redis for rate limiting and not PostgreSQL?**
Rate limit checks happen on every single request. PostgreSQL reads from disk — too slow at scale. Redis stores counters in RAM giving sub-millisecond response time. The tradeoff is data loss on restart, which is acceptable for rate limit counters since they reset naturally.

**Why Isolation Forest for anomaly detection?**
There is no labeled dataset saying "this IP is a bot." Isolation Forest is unsupervised — it finds outliers purely from behavioral patterns without needing labeled examples. It works by randomly partitioning data — points that get isolated quickly (bots with extreme request rates) are flagged as anomalies.

**Why index on ip_address column?**
The most frequent query pattern is filtering logs by IP — for rate limiting, anomaly scoring, and dashboard display. Without an index PostgreSQL scans every row. With an index it jumps directly to matching rows — critical as the logs table grows to millions of rows.

**Why middleware for logging?**
Writing logging code in every route would repeat the same logic across every endpoint. Middleware runs automatically on every request regardless of which route is called — single responsibility, no repetition.

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Anjan-taty/Intelligent-Traffic-Monitor-Anomaly-Detector.git
cd traffic_monitor
```

---

### 2. Without Docker (Local Setup)

**Create virtual environment**

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / Mac / WSL
python -m venv venv
source venv/bin/activate
```

**Install dependencies**

```bash
pip install -r requirements.txt
```

**Set up environment variables**

Create a `.env` file in the root directory:

```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/traffic_db
REDIS_URL=redis://localhost:6379
```

**Create the database**

```bash
psql -U postgres
CREATE DATABASE traffic_db;
\q
```

**Start Redis (WSL / Linux)**

```bash
sudo service redis-server start
```

**Run the application**

```bash
uvicorn main:app --reload
```

---

### 3. With Docker (Recommended)

Make sure Docker Desktop is running, then:

```bash
docker-compose up --build
```

This starts three containers automatically:
- FastAPI application on port 8000
- PostgreSQL on port 5432
- Redis on port 6379

To stop:

```bash
docker-compose down
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Health check |
| GET | `/stats` | Total requests, unique IPs, recent logs |
| GET | `/logs` | All request logs (paginated) |
| GET | `/flagged-ips` | IPs flagged as suspicious by ML model |
| GET | `/rate-limit-violations` | IPs that exceeded rate limits |
| WebSocket | `/ws/live-traffic` | Real-time request stream |

---

## Requirements

```
fastapi
uvicorn
sqlalchemy
psycopg2-binary
redis
scikit-learn
pandas
numpy
apscheduler
python-dotenv
```

Install all with:

```bash
pip install -r requirements.txt
```

---

## ML Model Details

**Algorithm:** Isolation Forest (scikit-learn)

**Features per IP (calculated over last 1 hour):**

| Feature | Description |
|---|---|
| request_count | Total requests sent |
| requests_per_minute | Average request rate |
| unique_endpoints | Number of different URLs hit |
| error_rate | Percentage of 4xx responses |
| rate_limit_hit_rate | Percentage of requests that were rate limited |
| time_variance | Variance in seconds between requests |
| top_endpoint_concentration | % of requests to single most hit endpoint |

**How it works:**
- Model retrains every hour using the latest traffic data from PostgreSQL
- Each IP gets an anomaly score — negative score means suspicious
- Flagged IPs are written to the `anomalies` table

**Why unsupervised:**
No labeled dataset exists saying "this IP is a bot." Isolation Forest finds outliers purely from behavioral patterns — bots naturally cluster far from normal human traffic.

---

## Rate Limiting

Two algorithms are available, selectable via configuration:

**Token Bucket**
- Each IP gets a bucket with N tokens
- Each request uses one token
- Tokens refill at a fixed rate
- Allows short bursts of traffic
- Best for: APIs used by real users

**Sliding Window Counter**
- Counts requests in a rolling time window
- Strictly enforces maximum requests per window
- No bursts allowed
- Best for: strict API protection

Both are stored in Redis. Rate limit violations return HTTP 429 with a `Retry-After` header.

---

## Running Tests

```bash
pytest tests/
```

Key test cases:
- Rate limiter blocks after threshold
- Rate limiter is independent per IP
- Different IPs do not share counters
- Anomaly detector flags high-volume IPs

---

## Example Output

```
Request logged:
{
  "ip_address": "127.0.0.1",
  "method": "GET",
  "endpoint": "/products",
  "status_code": 200,
  "response_time_ms": 12.4,
  "timestamp": "2026-01-01T10:00:00"
}

Rate limit hit:
HTTP 429 Too Many Requests
Retry-After: 60

Flagged IP:
{
  "ip": "192.168.1.100",
  "anomaly_score": -0.43,
  "reason": "500 req/min to single endpoint, 0% endpoint variety"
}
```

---

## Future Improvements

- Add gRPC support for internal service communication
- Integrate Kafka message queue for guaranteed log delivery
- Add IP geolocation to detect requests from unusual locations
- Deploy on Kubernetes for auto-scaling
- Add HTTPS/TLS termination at the gateway level
- Build alerting system — email or Slack notification on anomaly detection
- Add support for whitelisting trusted IPs

---

## How This Relates to Industry Systems

This project implements a simplified version of what commercial products like Akamai, Cloudflare, and AWS WAF do at scale:

| Feature | This Project | Industry Scale |
|---|---|---|
| Rate Limiting | Redis per-IP counters | Distributed Redis clusters |
| Anomaly Detection | Isolation Forest hourly | Real-time ML inference pipelines |
| Request Logging | PostgreSQL | Petabyte-scale data warehouses |
| Gateway | Single FastAPI instance | Global edge network (CDN) |

---