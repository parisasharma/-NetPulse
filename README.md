# 📡 NetPulse — Real-Time Network Health Monitor

A production-grade network monitoring tool built with **Python (FastAPI)**, **PostgreSQL**, and **Streamlit**.  
Monitors device latency and packet loss via ICMP ping, detects anomalies, and sends email alerts on status changes.

---

## 🖥️ Demo

> Dashboard screenshot / live link goes here after deploy

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     NetPulse System                     │
│                                                         │
│  ┌────────────┐    REST API    ┌─────────────────────┐  │
│  │ Streamlit  │◄──────────────►│   FastAPI Backend   │  │
│  │ Dashboard  │                │   (app/main.py)     │  │
│  └────────────┘                └──────────┬──────────┘  │
│                                           │             │
│                          ┌────────────────┼──────────┐  │
│                          │                │          │  │
│                   ┌──────▼──────┐  ┌──────▼──────┐  │  │
│                   │  PostgreSQL  │  │ APScheduler │  │  │
│                   │  Database   │  │ (pings/30s) │  │  │
│                   └─────────────┘  └──────┬──────┘  │  │
│                                           │          │  │
│                                    ┌──────▼──────┐   │  │
│                                    │ Ping Worker │   │  │
│                                    │ (ICMP/ping) │   │  │
│                                    └──────┬──────┘   │  │
│                                           │           │  │
│                              ┌────────────▼─────────┐ │  │
│                              │  Network Devices      │ │  │
│                              │  (routers, servers..) │ │  │
│                              └──────────────────────┘ │  │
│                                                        │  │
└────────────────────────────────────────────────────────┘
```

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔄 Live Pinging | ICMP ping every 30s per device, stores latency + packet loss + jitter |
| 🟢🟡🔴 Status Detection | Auto-classifies: `up`, `degraded` (high latency), `down` (3 consecutive failures) |
| 📊 Live Dashboard | Streamlit dashboard with latency charts, status table, uptime %, alert panel |
| 🚨 Email Alerts | Sends HTML email on device down, degraded, or recovered events |
| 🔌 REST API | Full CRUD for devices, history queries, stats endpoint, alert management |
| 🐳 Docker | One-command deploy with `docker-compose up` |
| 📈 Analytics | 24h uptime %, avg/min/max latency, packet loss trends per device |

---

## 📁 Project Structure

```
netpulse/
├── app/
│   ├── main.py          # FastAPI app, startup/shutdown lifecycle
│   ├── models.py        # SQLAlchemy ORM models (Device, PingResult, Alert)
│   ├── schemas.py       # Pydantic request/response validation
│   ├── database.py      # DB engine, session, Base
│   ├── ping_worker.py   # Core ICMP ping logic + anomaly detection
│   ├── scheduler.py     # APScheduler — background ping jobs
│   ├── alerts.py        # Gmail SMTP email alerts
│   └── routers/
│       ├── devices.py   # /devices endpoints
│       └── alerts.py    # /alerts endpoints
├── dashboard/
│   └── app.py           # Streamlit dashboard
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🚀 Quick Start (Local — SQLite, no Docker needed)

### 1. Clone and install
```bash
git clone https://github.com/YOUR_USERNAME/netpulse.git
cd netpulse
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set up environment
```bash
cp .env.example .env
# Edit .env — for local dev, the default SQLite config works as-is
```

### 3. Run the API
```bash
uvicorn app.main:app --reload
```
API running at: **http://localhost:8000**  
Interactive docs: **http://localhost:8000/docs**

### 4. Run the dashboard (new terminal)
```bash
streamlit run dashboard/app.py
```
Dashboard at: **http://localhost:8501**

### 5. Add your first device (via /docs or curl)
```bash
curl -X POST http://localhost:8000/devices \
  -H "Content-Type: application/json" \
  -d '{"name": "Google DNS", "ip_address": "8.8.8.8", "latency_threshold_ms": 100}'
```

---

## 🐳 Docker Deploy

```bash
# Build and start all services (API + DB + Dashboard)
docker-compose up --build

# API:       http://localhost:8000
# Dashboard: http://localhost:8501
# API Docs:  http://localhost:8000/docs
```

---

## ☁️ Deploy on Railway (free, live URL)

1. Push this repo to GitHub
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Add a **PostgreSQL** plugin
4. Set env variable: `DATABASE_URL` (Railway provides this automatically)
5. Set `ALERT_EMAIL_FROM`, `ALERT_EMAIL_PASSWORD`, `ALERT_EMAIL_TO` for email alerts
6. Generate a public domain → your live URL

---

## 📡 API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/devices` | List all devices |
| POST | `/devices` | Add a new device |
| GET | `/devices/{id}` | Get device details |
| PUT | `/devices/{id}` | Update device |
| DELETE | `/devices/{id}` | Delete device |
| GET | `/devices/{id}/status` | Latest ping result |
| GET | `/devices/{id}/history` | Ping history (filter by hours) |
| GET | `/devices/{id}/stats` | Uptime %, avg latency, etc. |
| GET | `/summary` | Overview of all devices |
| GET | `/alerts` | List active alerts |
| PUT | `/alerts/{id}/resolve` | Resolve an alert |

Full interactive docs at `/docs` (auto-generated by FastAPI).

---

## 📧 Email Alerts Setup

1. Enable 2-Factor Authentication on your Gmail account
2. Go to: `myaccount.google.com/apppasswords`
3. Create a new App Password (select "Mail")
4. Copy the 16-character password
5. Add to `.env`:
```
ALERT_EMAIL_FROM=your@gmail.com
ALERT_EMAIL_PASSWORD=xxxx xxxx xxxx xxxx
ALERT_EMAIL_TO=alerts@youremail.com
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI, Uvicorn |
| Database | PostgreSQL (prod) / SQLite (local dev) |
| ORM | SQLAlchemy 2.0 |
| Validation | Pydantic v2 |
| Scheduler | APScheduler |
| Ping | subprocess (cross-platform ICMP) |
| Dashboard | Streamlit, Plotly, Pandas |
| Email | smtplib (Gmail SMTP) |
| Infra | Docker, docker-compose |
| Deploy | Railway.app |

---

## 🔮 What I'd Add Next (Scale to 10,000 devices)

- Replace APScheduler with **Celery + Redis** for distributed ping workers
- Switch to **TimescaleDB** or **InfluxDB** for time-series data at scale
- Add **WebSocket** endpoint for real-time dashboard updates without polling
- Add **MQTT** support for IoT device telemetry
- Add **Grafana** integration for enterprise dashboards
- Multi-user auth with **JWT tokens**

---

## 👩‍💻 Built By

**Parisa Sharma** — ECE, Thapar Institute of Engineering & Technology (2027)  
Network monitoring tool inspired by real-world observations during internship at Aerial Telecom Solutions.

---

## 📄 License

MIT
