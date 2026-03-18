# 🛡️ Intelligent Traffic Monitor & Anomaly Detector

A high-performance **reverse proxy gateway** built in Python that:

- 🌐 Intercepts all incoming HTTP traffic  
- 📊 Logs request metadata to PostgreSQL  
- ⚡ Enforces per-IP rate limiting using Redis  
- 🧠 Detects anomalies using Isolation Forest (ML)  

Inspired by systems like **Cloudflare, Akamai, and AWS WAF**, this project acts as a **smart gatekeeper** between users and your server.

---

## 🎯 Problem Statement

Modern web servers face three major threats:

| Threat | Description |
|------|------------|
| 🤖 Bot Attacks | Automated scripts brute-forcing endpoints |
| 🕵️ Scrapers | Repeated requests to extract data |
| 📈 Traffic Spikes | Sudden load overwhelming servers |

👉 This system detects and mitigates all three **automatically**.

---

## ⚙️ System Flow

```
Incoming Request
      ↓
🧠 FastAPI Middleware
      ↓
⚡ Redis Rate Limit Check
   ├── ❌ Block → 429 Too Many Requests
   └── ✅ Allow
      ↓
📦 Route Handler
      ↓
🗄️ PostgreSQL Logging
      ↓
📤 Response to Client

⏱️ Background Job (Hourly):
Logs → Feature Extraction → Isolation Forest → Flag Suspicious IPs
```

---

## 🌟 Key Features

- 📊 **Request Logging**
  - IP, endpoint, method, status, response time, timestamp

- ⚡ **Rate Limiting**
  - Token Bucket (burst-friendly)
  - Sliding Window (strict control)

- 🧠 **ML Anomaly Detection**
  - Isolation Forest (unsupervised)
  - Detects bots without labeled data

- 📡 **Live Dashboard**
  - WebSocket-based real-time visualization

- 🐳 **Dockerized**
  - One-command full system setup

---

## 🧱 Architecture

```
traffic_monitor/
│
├── main.py           # 🚀 FastAPI app (middleware + routes)
├── database.py       # 🗄️ PostgreSQL connection
├── models.py         # 📦 Database tables
├── schemas.py        # 🔄 API schemas
├── rate_limiter.py   # ⚡ Redis rate limiting
├── anomaly.py        # 🧠 ML model logic
├── dashboard/
│   └── index.html    # 📊 Live dashboard (Chart.js)
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| 🚀 API | FastAPI | Async, high performance |
| 🗄️ Database | PostgreSQL | Structured logs |
| ⚡ Cache | Redis | Fast rate limiting |
| 🧠 ML | Isolation Forest | Anomaly detection |
| 🐳 DevOps | Docker | Easy deployment |
| ⏱️ Scheduler | APScheduler | Periodic retraining |
| 📊 Dashboard | Chart.js + WebSocket | Real-time analytics |

---

## 🧠 ML Model Overview

### 📊 Features Used Per IP

| Feature | Meaning |
|--------|--------|
| request_count | Total requests |
| requests_per_minute | Traffic intensity |
| unique_endpoints | Diversity of access |
| error_rate | % of failed requests |
| rate_limit_hit_rate | Abuse indicator |
| time_variance | Request timing irregularity |
| top_endpoint_concentration | Focused scraping behavior |

---

### 📉 Anomaly Detection Logic

```
Normal Traffic      → Dense cluster
Bot / Scraper       → Sparse / isolated points
```

👉 Isolation Forest isolates anomalies faster → flagged as suspicious

---

### 📊 Behavior Pattern (Conceptual)

```
Normal User:
|----|   |----|     |----|

Bot:
|||||||||||||||||||||||||
```

---

## ⚡ Rate Limiting Strategies

### 🟢 Token Bucket

```
[ Tokens: ●●●●● ]
Request → consume ●
Refill over time
```

✔ Allows bursts  
✔ User-friendly  

---

### 🔴 Sliding Window

```
|----Window----|
||||||||||||||| → limit exceeded ❌
```

✔ Strict enforcement  
✔ Prevents abuse  

---

## ⚙️ Installation

### 1️⃣ Clone Repo

```bash
git clone https://github.com/Anjan-taty/Intelligent-Traffic-Monitor-Anomaly-Detector.git
cd traffic_monitor
```

---

### 2️⃣ Local Setup

```bash
python -m venv venv
venv\Scripts\activate   # Windows
source venv/bin/activate # Linux/Mac

pip install -r requirements.txt
```

---

### 3️⃣ Environment Variables

```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/traffic_db
REDIS_URL=redis://localhost:6379
```

---

### 4️⃣ Run App

```bash
uvicorn main:app --reload
```

---

## 🐳 Docker Setup (Recommended)

```bash
docker-compose up --build
```

### Services:

- 🚀 FastAPI → `:8000`
- 🗄️ PostgreSQL → `:5432`
- ⚡ Redis → `:6379`

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Health check |
| GET | `/stats` | Traffic stats |
| GET | `/logs` | Logs |
| GET | `/flagged-ips` | Suspicious IPs |
| GET | `/rate-limit-violations` | Violations |
| WS | `/ws/live-traffic` | Live stream |

---

## 📊 Example Output

```
Request logged:
{
  "ip": "127.0.0.1",
  "endpoint": "/products",
  "response_time": 12ms
}

Rate limit:
HTTP 429 Too Many Requests

Anomaly detected:
IP: 192.168.1.100
Score: -0.43
Reason: High request frequency
```

---

## 🧠 Design Decisions

### Why Redis?
- ⚡ In-memory → ultra-fast  
- Perfect for per-request checks  

### Why Isolation Forest?
- No labeled data needed  
- Detects unusual patterns automatically  

### Why Middleware?
- Centralized logic  
- No duplication  

---

## 📈 Industry Comparison

| Feature | This Project | Real Systems |
|---|---|---|
| Rate Limiting | Redis | Distributed Redis |
| ML Detection | Isolation Forest | Real-time ML pipelines |
| Logs | PostgreSQL | Data warehouses |
| Gateway | Single node | Global CDN |

---

## 🚀 Future Improvements

- Kafka for streaming logs  
- Kubernetes deployment  
- IP geolocation analysis  
- Alerting system (Slack / Email)  
- HTTPS termination  

---

## 🎯 Use Case

- 🛡️ API protection  
- 🤖 Bot detection  
- 📊 Traffic analytics  
- ⚡ Backend performance monitoring  

---

## 👨‍💻 Author

Developed by **Anjan (Taty)**  
Building real-world AI + backend systems 🚀  

---

## ⭐ Support

If you like this project, give it a ⭐ — it helps!
