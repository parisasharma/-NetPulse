"""
dashboard/app.py
────────────────
NetPulse Streamlit Dashboard.
Calls the FastAPI backend and shows:
  - Summary cards (total devices, up/degraded/down, active alerts)
  - Device status table with colour coding
  - Live latency chart per device
  - Active alerts panel
  - Add / delete device forms

Run:
    streamlit run dashboard/app.py
"""

import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import time
import os

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")
REFRESH_SECONDS = 30

st.set_page_config(
    page_title="NetPulse",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .metric-card {
        background: #1e1e2e;
        border-radius: 10px;
        padding: 16px 20px;
        text-align: center;
    }
    .status-up    { color: #1D9E75; font-weight: 600; }
    .status-down  { color: #E24B4A; font-weight: 600; }
    .status-deg   { color: #BA7517; font-weight: 600; }
    .status-unk   { color: #888;    font-weight: 600; }
    h1 { font-size: 1.8rem !important; }
</style>
""", unsafe_allow_html=True)


# ── API helpers ───────────────────────────────────────────────────────────────
def api_get(path: str):
    try:
        r = requests.get(f"{API_BASE}{path}", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error ({path}): {e}")
        return None


def api_post(path: str, data: dict):
    try:
        r = requests.post(f"{API_BASE}{path}", json=data, timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error: {e}")
        return None


def api_delete(path: str):
    try:
        r = requests.delete(f"{API_BASE}{path}", timeout=5)
        r.raise_for_status()
        return True
    except Exception as e:
        st.error(f"API error: {e}")
        return False


def status_badge(status: str) -> str:
    icons = {"up": "🟢", "degraded": "🟡", "down": "🔴"}
    return f"{icons.get(status, '⚪')} {status.upper()}"


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📡 NetPulse")
    st.caption("Real-time Network Monitor")
    st.divider()

    # Add device form
    st.subheader("➕ Add Device")
    with st.form("add_device_form", clear_on_submit=True):
        d_name = st.text_input("Name", placeholder="e.g. Office Router")
        d_ip = st.text_input("IP Address", placeholder="e.g. 192.168.1.1")
        d_desc = st.text_input("Description (optional)")
        d_threshold = st.number_input("Latency threshold (ms)", value=200, min_value=10, max_value=5000)
        submitted = st.form_submit_button("Add Device", use_container_width=True)
        if submitted and d_name and d_ip:
            result = api_post("/devices", {
                "name": d_name,
                "ip_address": d_ip,
                "description": d_desc or None,
                "latency_threshold_ms": float(d_threshold),
            })
            if result:
                st.success(f"✅ Added {d_name}")
                st.rerun()

    st.divider()
    auto_refresh = st.checkbox("Auto-refresh (30s)", value=True)
    history_hours = st.slider("Chart history (hours)", 1, 24, 1)
    st.caption(f"API: `{API_BASE}`")


# ── Main content ──────────────────────────────────────────────────────────────
st.title("📡 NetPulse — Network Health Monitor")
st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}  ·  Pings every 30s")

summary = api_get("/summary")
devices = api_get("/devices?active_only=true")
alerts_data = api_get("/alerts")

# ── Summary cards ─────────────────────────────────────────────────────────────
if summary:
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Devices",  summary.get("total_devices", 0))
    c2.metric("🟢 Up",          summary.get("devices_up", 0))
    c3.metric("🟡 Degraded",    summary.get("devices_degraded", 0))
    c4.metric("🔴 Down",        summary.get("devices_down", 0))
    avg_lat = summary.get("average_latency_ms")
    c5.metric("Avg Latency",    f"{avg_lat:.1f} ms" if avg_lat else "—")

st.divider()

# ── Device table + charts ─────────────────────────────────────────────────────
if not devices:
    st.info("No devices monitored yet. Add a device from the sidebar.")
else:
    tab1, tab2, tab3 = st.tabs(["📊 Status Table", "📈 Latency Charts", "🚨 Alerts"])

    with tab1:
        st.subheader("Device Status")
        rows = []
        for device in devices:
            status_data = api_get(f"/devices/{device['id']}/status")
            stats_data = api_get(f"/devices/{device['id']}/stats?hours=24")
            rows.append({
                "Name": device["name"],
                "IP Address": device["ip_address"],
                "Status": status_badge(status_data["status"]) if status_data else "⚪ UNKNOWN",
                "Latency (ms)": f"{status_data['latency_ms']:.1f}" if status_data and status_data.get("latency_ms") else "—",
                "Packet Loss": f"{status_data['packet_loss']*100:.0f}%" if status_data else "—",
                "24h Uptime": f"{stats_data['uptime_percent']:.1f}%" if stats_data and 'uptime_percent' in stats_data else "—",
                "Description": device.get("description") or "—",
                "ID": device["id"],
            })

        df = pd.DataFrame(rows)
        st.dataframe(
            df.drop(columns=["ID"]),
            use_container_width=True,
            hide_index=True,
        )

        # Delete device
        st.subheader("🗑️ Remove Device")
        device_names = {d["name"]: d["id"] for d in devices}
        to_delete = st.selectbox("Select device to remove", list(device_names.keys()))
        if st.button("Delete Device", type="secondary"):
            if api_delete(f"/devices/{device_names[to_delete]}"):
                st.success(f"Deleted {to_delete}")
                st.rerun()

    with tab2:
        st.subheader(f"Latency — last {history_hours}h")
        selected = st.selectbox("Select device", [d["name"] for d in devices])
        selected_device = next((d for d in devices if d["name"] == selected), None)

        if selected_device:
            history = api_get(
                f"/devices/{selected_device['id']}/history"
                f"?limit=500&hours={history_hours}"
            )
            if history:
                df_h = pd.DataFrame(history)
                df_h["timestamp"] = pd.to_datetime(df_h["timestamp"])
                df_h = df_h.sort_values("timestamp")

                # Latency line chart
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=df_h["timestamp"],
                    y=df_h["latency_ms"],
                    mode="lines+markers",
                    name="Latency (ms)",
                    line=dict(color="#1D9E75", width=2),
                    marker=dict(size=4),
                ))
                # Threshold line
                threshold = selected_device.get("latency_threshold_ms", 200)
                fig.add_hline(
                    y=threshold,
                    line_dash="dash",
                    line_color="#E24B4A",
                    annotation_text=f"Threshold {threshold}ms",
                )
                fig.update_layout(
                    title=f"{selected} — Latency",
                    xaxis_title="Time",
                    yaxis_title="Latency (ms)",
                    template="plotly_dark",
                    height=350,
                    margin=dict(l=0, r=0, t=40, b=0),
                )
                st.plotly_chart(fig, use_container_width=True)

                # Packet loss chart
                fig2 = px.bar(
                    df_h, x="timestamp", y="packet_loss",
                    title=f"{selected} — Packet Loss",
                    color="packet_loss",
                    color_continuous_scale=["#1D9E75", "#BA7517", "#E24B4A"],
                    template="plotly_dark",
                    height=250,
                )
                fig2.update_layout(margin=dict(l=0, r=0, t=40, b=0))
                st.plotly_chart(fig2, use_container_width=True)

                # Status breakdown pie
                status_counts = df_h["status"].value_counts()
                fig3 = px.pie(
                    values=status_counts.values,
                    names=status_counts.index,
                    title="Status Distribution",
                    color=status_counts.index,
                    color_discrete_map={"up": "#1D9E75", "degraded": "#BA7517", "down": "#E24B4A"},
                    template="plotly_dark",
                    height=280,
                )
                st.plotly_chart(fig3, use_container_width=True)
            else:
                st.info("No history yet. Wait for the first ping cycle (~30s).")

    with tab3:
        st.subheader("🚨 Active Alerts")
        if not alerts_data:
            st.success("✅ No active alerts — all systems normal.")
        else:
            for alert in alerts_data:
                colour = {"down": "🔴", "degraded": "🟡", "recovered": "🟢"}.get(alert["alert_type"], "⚪")
                with st.expander(f"{colour} [{alert['alert_type'].upper()}] — {alert['message'][:60]}..."):
                    st.write(f"**Message:** {alert['message']}")
                    st.write(f"**Created:** {alert['created_at']}")
                    st.write(f"**Resolved:** {alert['is_resolved']}")
                    if not alert["is_resolved"]:
                        if st.button(f"Resolve alert #{alert['id']}", key=f"resolve_{alert['id']}"):
                            requests.put(f"{API_BASE}/alerts/{alert['id']}/resolve", timeout=5)
                            st.rerun()

# ── Auto refresh ──────────────────────────────────────────────────────────────
if auto_refresh:
    time.sleep(REFRESH_SECONDS)
    st.rerun()
