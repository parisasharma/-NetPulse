 NetPulse — Real-Time Network Health Monitor

A production-grade network monitoring tool built with Python (FastAPI), PostgreSQL, and Streamlit.  
Monitors device latency and packet loss via ICMP ping, detects anomalies, and sends email alerts on status changes.

Architecture

┌─────────────────────────────────────────────────────────┐
│                     NetPulse System                     │
│                                                         │
│  ┌────────────┐    REST API    ┌─────────────────────┐  │
│  │ Streamlit  │◄──────────────►│   FastAPI Backend   │  │
│  │ Dashboard  │                │   (app/main.py)     │  │
│  └────────────┘                └──────────┬──────────┘  │
│                                           │             │
│                          ┌────────────────┼──────────┐  │
│                          │                │             │  
│                   ┌──────▼──────┐  ┌──────▼──────┐      │  
│                   │  PostgreSQL  │  │ APScheduler │     │  
│                   │  Database   │  │ (pings/30s) │      │  
│                   └─────────────┘  └──────┬──────┘      │  
│                                           │             │  
│                                    ┌──────▼──────┐      │  
│                                    │ Ping Worker │      │  
│                                    │ (ICMP/ping) │      │  
│                                    └──────┬──────┘      │  
│                                           │             │  
│                              ┌────────────▼─────────┐   │  
│                              │  Network Devices      │  │  
│                              │  (routers, servers..)  │ │  
│                              └──────────────────────┘   │  
│                                                         │  
└────────────────────────────────────────────────────────┘




 Features

Live Pinging - ICMP ping every 30s per device, stores latency + packet loss + jitter 
Status Detection - Auto-classifies: `up`, `degraded` (high latency), `down` (3 consecutive failures) |
Live Dashboard | Streamlit dashboard with latency charts, status table, uptime %, alert panel |
Email Alerts | Sends HTML email on device down, degraded, or recovered events |
 REST API | Full CRUD for devices, history queries, stats endpoint, alert management |
 Docker | One-command deploy with `docker-compose up` |
 Analytics | 24h uptime %, avg/min/max latency, packet loss trends per device |



Project Structure


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

LIVE DEMO
<https://graceful-celebration-production-f259.up.railway.app/>
DASHBOARD IMAGE- <img width="953" height="476" alt="image" src="https://github.com/user-attachments/assets/ec2ed858-d90f-4e1f-8f66-9001f682007c" />



 








 Built By
PARISA SHARMA — ECE, Thapar Institute of Engineering & Technology (2027)  
Network monitoring tool inspired by real-world observations during internship at Aerial Telecom Solutions.


