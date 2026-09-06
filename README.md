# 🛡️ AegisGuard: Intelligent Traffic Monitor & Anomaly Detector

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Redis](https://img.shields.io/badge/Redis-7.0%2B-dc382d.svg?logo=redis&logoColor=white)](https://redis.io)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![Scikit-Learn](https://img.shields.io/badge/Scikit--Learn-Isolation%20Forest-F7931E.svg?logo=scikit-learn&logoColor=white)](https://scikit-learn.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg?logo=docker&logoColor=white)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An enterprise-grade, self-defending API Gateway and Network Traffic Behavioral Telemetry Engine. Engineered to mitigate Layer-7 volumetric floods, aggressive scrapers, and credential brute-forcing in real time using **Atomic Redis Sliding-Window Rate Limiting** and **Explainable Unsupervised Machine Learning (Isolation Forest + XAI)**.

---

## 📌 Problem Statement

Modern microservices face sophisticated threats that bypass traditional static rate limiters:
- **Low-and-Slow Scrapers**: Automated crawlers traversing product catalogs with randomized or sequential delays that evade simple fixed counters.
- **Distributed L7 DDoS / Volumetric Floods**: Sudden request surges that exhaust database connection pools and backend CPU threads.
- **Credential Stuffing & Endpoint Enumeration**: Automated bots firing rapid authentication probes that generate 401/403/404 clusters.

**AegisGuard solves this through a Decoupled Zero-Latency Architecture**:
1. **Synchronous Fast Path (Data Plane)**: Sub-millisecond rate checking via atomic Redis Lua scripts with zero blocking.
2. **Asynchronous Stream Analytics (Control Plane)**: Behavioral feature extraction (timing jitter, route traversal entropy, error velocity) fed into an Explainable Isolation Forest engine with automated adaptive mitigation.

---

## 🧱 Architecture Overview

```
                                    +------------------------------------------+
                                    |         Incoming HTTP Requests           |
                                    +------------------------------------------+
                                                         |
                                                         v
                                    +------------------------------------------+
                                    |     FastAPI Smart Reverse Gateway        |
                                    +------------------------------------------+
                                                         |
                   +-------------------------------------+------------------------------------+
                   |                                                                          |
                   v [Synchronous Fast Path: < 2ms]                                           v [Async Queue: Non-blocking]
+------------------------------------+                                     +------------------------------------+
|         Redis Policy Engine        |                                     |    Background Telemetry Worker     |
| - Atomic Sliding Window (Lua)      |                                     | - Ingest to PostgreSQL Logs        |
| - Dynamic Threat Tier Lookup       |                                     | - Sliding Window State Cache       |
+------------------------------------+                                     +------------------------------------+
       |                     |                                                                |
 [Exceeded Limit]      [Within Limit]                                                         v
       |                     |                                             +------------------------------------+
       v                     v                                             |    Feature Engineering Pipeline    |
HTTP 429 Block       Proxy to Target API                                   | - Inter-arrival Timing Jitter      |
                             |                                             | - Endpoint Traversal Entropy       |
                             v                                             | - Error Velocity & Status Ratios   |
                      HTTP 200/400/500                                     +------------------------------------+
                             |                                                                |
                             +----------------------------------------------------------------+
                                                              |
                                                              v
                                           +------------------------------------+
                                           |     Dual-Tier Anomaly Engine       |
                                           | Tier 1: Real-time Dynamic Z-Score  |
                                           | Tier 2: Isolation Forest + XAI     |
                                           +------------------------------------+
                                                              |
                                                    [Threat Score > Threshold]
                                                              |
                                                              v
                                           +------------------------------------+
                                           |     Adaptive Mitigation Loop       |
                                           | - Write ban/throttle key to Redis  |
                                           | - Push Alert via WebSocket         |
                                           +------------------------------------+
                                                              |
                                                              v
                                           +------------------------------------+
                                           |      Live SOC Dashboard (WS)       |
                                           +------------------------------------+
```

---

## 🌟 Key Engineering Features

### 1. Atomic Redis Sliding-Window Rate Limiter
- **Eliminates Race Conditions**: Executes custom Redis Lua scripts directly on the Redis server engine, ensuring sliding-window log cleanup and token checks execute atomically in $O(1)$.
- **Dynamic Tiering**:
  - `TIER_NORMAL`: Standard rate allowance (60 req/min).
  - `TIER_THROTTLED`: Penalized tier (10 req/min) automatically applied to suspicious actors.
  - `TIER_BLOCKED`: Instant 429 rejection with adaptive `Retry-After` calculation.
- **Resilient Fallback**: Automatically switches to an in-memory thread-safe sliding window if Redis is temporarily offline.

### 2. Deep Behavioral Feature Extraction
Beyond naive request counters, AegisGuard extracts rich behavioral fingerprints across rolling time windows:
- **Inter-arrival Timing Jitter ($\sigma_{\Delta t}$)**: Standard deviation between consecutive requests. Humans exhibit Poisson think-time delays ($\sigma > 1.0\text{s}$); automated scripts exhibit robotic cadences ($\sigma < 0.05\text{s}$).
- **Endpoint Traversal Entropy ($H$)**: Shannon entropy over accessed URLs:
  $$H = -\sum_{i=1}^n p_i \log_2(p_i)$$
  Scrapers crawling large catalogs display high entropy; human users display cohesive, low-entropy journeys.
- **Error Velocity & Post Ratio**: Tracks concentrated 401/403/404 clusters characteristic of credential brute-forcing and vulnerability scanning.

### 3. Explainable Anomaly Detection (XAI)
- **Unsupervised Isolation Forest**: Isolates anomalies without requiring labeled training datasets, ideal for zero-day attack patterns.
- **Root-Cause Attribution**: Every alert includes human-readable diagnostic drivers (e.g., *"Flagged: Robotic Cadence (jitter: 0.02s) & High Route Dispersion (entropy: 3.41)"*) aligning with enterprise governance.

### 4. Interactive SOC Command Center & Attack Simulator
- **Live Dark-Mode Dashboard**: Real-time throughput graph (RPS), p50/p95 latency meters, status code donuts, and live security incident streams connected via WebSockets.
- **Built-in Attack Simulator**: One-click generation of 4 realistic workloads:
  - 👤 **Human User**: Natural pacing, browsing journey.
  - 🕷️ **Catalog Web Scraper**: Sub-20ms bursts, systematic URL enumeration.
  - ⚡ **Volumetric L7 DDoS**: Multi-threaded flood triggering rate limits.
  - 🔐 **Credential Brute-Force**: High-speed POST `/api/login` cluster causing 401 errors.

---

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.10+ (or Docker)
- Optional: Redis & PostgreSQL (AegisGuard includes automatic SQLite & in-memory fallback for immediate zero-dependency evaluation)

### Option A: Local Development (Instant Run)

```bash
# 1. Clone repository
git clone https://github.com/Anjan-taty/Intelligent-Traffic-Monitor-Anomaly-Detector.git
cd Intelligent-Traffic-Monitor-Anomaly-Detector

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate     # Windows
# source venv/bin/activate # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch Gateway & Dashboard
python main.py
```
Open your browser at **`http://localhost:8000`** to access the live SOC Command Center!

---

### Option B: Docker Compose (Full Production Stack)

```bash
docker-compose up --build
```
This orchestrates:
- 🚀 **FastAPI Gateway & SOC Dashboard** (`:8000`)
- ⚡ **Redis 7 In-Memory Store** (`:6379`)
- 🗄️ **PostgreSQL 15 Database** (`:5432`)

---

## 🎯 Testing & Attack Simulation

Run the automated test suite:
```bash
python test_system.py
```

Simulate attacks directly from the command line:
```bash
# Simulate aggressive web scraper
python traffic_simulator.py --scenario scraper --count 40

# Simulate volumetric Layer-7 DDoS flood
python traffic_simulator.py --scenario ddos --count 80 --concurrency 8

# Simulate credential brute-forcing
python traffic_simulator.py --scenario bruteforce --count 25

# Simulate regular human browsing
python traffic_simulator.py --scenario human --count 15
```
*(You can also trigger these scenarios directly using the interactive buttons on the web dashboard!)*

---

## 📡 API Reference

| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Cyber SOC Command Center UI |
| `WS` | `/ws/telemetry` | Real-time WebSocket telemetry & alert stream |
| `GET` | `/api/stats` | System KPI summary (RPS, latencies, status distribution) |
| `GET` | `/api/alerts` | Recent security anomaly alerts with XAI reasons |
| `GET` | `/api/logs` | Intercepted request log audit trail |
| `POST` | `/api/simulate` | Trigger attack vector simulation programmatically |
| `GET` | `/api/health` | Gateway health check |
| `GET` | `/api/products` | Mock protected target service endpoints |
| `POST` | `/api/login` | Mock authentication service (evaluates brute force) |

---

## 🎓 IBM Interview Masterclass: Architecture, Design Decisions & Trade-Offs

When discussing this project during technical interviews at **IBM**, here are the key talking points:

### 1. System Design & Concurrency
* **Q: Why Redis instead of handling rate limits in PostgreSQL?**
  * *Talking Point*: PostgreSQL writes to disk with ACID transaction overhead. In a gateway handling 10,000+ RPS, querying SQL on every incoming request introduces severe I/O bottlenecks. Redis is an in-memory data store with sub-millisecond response times. By using Redis Lua scripts, we execute sliding-window log calculations atomically on Redis's single-threaded event loop, avoiding distributed concurrency race conditions.
* **Q: How did you ensure zero added latency for legitimate client requests?**
  * *Talking Point*: We decoupled the **data plane** from the **control plane**. The gateway checks rate limits synchronously in $< 2\text{ms}$. Logging, telemetry aggregation, and Isolation Forest ML inference execute asynchronously in background executor threads, ensuring the client receives their HTTP response immediately.

### 2. Machine Learning & Cyber Defense
* **Q: Why Isolation Forest over supervised models (like Random Forest or XGBoost)?**
  * *Talking Point*: Supervised models require labeled training datasets and fail on zero-day attack vectors. Cybersecurity attacks evolve constantly. Isolation Forest is an unsupervised algorithm based on the concept that anomalous behaviors are 'few and different,' requiring fewer random tree partitions to isolate. It scales linearly with $O(n \log n)$, making it ideal for real-time telemetry.
* **Q: What is Explainable AI (XAI) and why does it matter here?**
  * *Talking Point*: Enterprise security teams cannot trust a 'black-box' model that arbitrarily blocks IP addresses without explanation. Our XAI layer computes feature deviation Z-scores against the baseline population, generating actionable root-cause diagnostics (e.g., *'Inter-arrival jitter < 0.05s indicates robotic cadence'*).

### 3. Enterprise Alignment with IBM Product Ecosystem
* **IBM API Connect**: Mirrors enterprise API Gateway policies, quota management, and rate limiting.
* **IBM QRadar (SIEM)**: Mirrors how QRadar ingests network flow logs, extracts telemetry signals, and flags anomalous user/entity behaviors (UEBA).
* **IBM Instana**: Demonstrates Application Performance Monitoring (APM), tracking Golden Signals (latency percentiles p50/p95/p99, traffic volume, errors, saturation).
* **IBM Watsonx Governance**: Embodies Trustworthy and Explainable AI (XAI) principles.

---

## 👨‍💻 Author
**Anjan Reddy**  
*Building Enterprise-Grade Resilient Systems & Machine Learning Infrastructure.*
