"""Streamlit Dashboard — real-time vitals monitoring + agent decision log + DuckDB analytics."""

import json
import os
import sys
import time

# Add project root to path so we can import app.simulator
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import httpx

API_URL = "http://localhost:8000"
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
VITALS_FILE = os.path.join(DATA_DIR, "vitals_history.parquet")

st.set_page_config(page_title="MedTech Agent Monitor", page_icon="🫀", layout="wide")

# --- Header ---
st.title("🫀 MedTech Agent Monitor")
st.caption("Real-time vitals monitoring with multi-agent AI triage — Smart Ring Demo")

# --- Tabs ---
tab_live, tab_history, tab_architecture = st.tabs(["Live Monitor", "Analytics (DuckDB)", "Architecture"])

# ============================================================
# TAB 1: Live Monitor — send vitals, see agent work in real-time
# ============================================================
with tab_live:
    col_input, col_output = st.columns([1, 2])

    with col_input:
        st.subheader("Simulate Vitals")

        mode = st.radio("Mode", ["Random (auto-generate)", "Manual (set values)"], horizontal=True)

        if mode == "Manual (set values)":
            heart_rate = st.slider("Heart Rate (bpm)", 30, 200, 75)
            systolic_bp = st.slider("Systolic BP (mmHg)", 50, 220, 120)
            diastolic_bp = st.slider("Diastolic BP (mmHg)", 30, 130, 80)
            spo2 = st.slider("SpO2 (%)", 70, 100, 97)
            temperature = st.slider("Temperature (°C)", 34.0, 42.0, 36.6, 0.1)
            respiratory_rate = st.slider("Respiratory Rate (breaths/min)", 5, 40, 16)

            vitals_payload = {
                "heart_rate": heart_rate,
                "systolic_bp": systolic_bp,
                "diastolic_bp": diastolic_bp,
                "spo2": spo2,
                "temperature": temperature,
                "respiratory_rate": respiratory_rate,
            }
        else:
            anomaly = st.checkbox("Force anomaly", value=True)
            # Generate random vitals client-side for display
            from app.simulator import generate_vitals
            if st.button("🎲 Generate New Reading", use_container_width=True):
                st.session_state["last_random"] = generate_vitals(anomaly_chance=1.0 if anomaly else 0.0)

            vitals_payload = st.session_state.get("last_random", generate_vitals(anomaly_chance=0.5))
            st.json(vitals_payload)

        send = st.button("🚀 Send to Agent Pipeline", type="primary", use_container_width=True)

    with col_output:
        st.subheader("Agent Pipeline Output")

        if send:
            log_container = st.status("Processing vitals through pipeline...", expanded=True)
            result_placeholder = st.empty()

            try:
                with httpx.stream(
                    "POST",
                    f"{API_URL}/process/stream",
                    json=vitals_payload,
                    timeout=120,
                ) as resp:
                    result_data = None
                    for line in resp.iter_lines():
                        if not line.startswith("data: "):
                            continue
                        payload = json.loads(line[6:])
                        if payload["type"] == "log":
                            log_container.write(payload["message"])
                        elif payload["type"] == "result":
                            result_data = payload["data"]

                log_container.update(label="Pipeline complete", state="complete", expanded=False)

                if result_data:
                    # Save to session for history
                    if "results" not in st.session_state:
                        st.session_state["results"] = []
                    st.session_state["results"].append(result_data)

                    # Display result
                    triage = result_data.get("triage", {})
                    severity = triage.get("severity", "UNKNOWN")

                    severity_colors = {
                        "NORMAL": "green", "WARNING": "orange",
                        "CRITICAL": "red", "EMERGENCY": "red",
                    }
                    color = severity_colors.get(severity, "gray")
                    st.markdown(f"### Triage: :{color}[{severity}]")
                    st.markdown(f"**Agent used:** `{result_data.get('agent_used', 'none')}`")

                    if result_data.get("assessment"):
                        st.markdown("---")
                        st.markdown("**Assessment:**")
                        st.markdown(result_data["assessment"])
                else:
                    st.error("No result returned from pipeline.")

            except httpx.ConnectError:
                st.error("Cannot connect to API. Run: `uvicorn app.main:app --port 8000`")

        # Show recent results
        if st.session_state.get("results"):
            st.markdown("---")
            st.subheader("Recent Alerts")
            for r in reversed(st.session_state["results"][-10:]):
                triage = r.get("triage", {})
                severity = triage.get("severity", "?")
                if severity == "NORMAL":
                    continue
                agent = r.get("agent_used", "none")
                ts = r.get("timestamp", "")[:19]
                st.markdown(f"**{ts}** — `{severity}` → `{agent}` agent")

# ============================================================
# TAB 2: DuckDB Analytics on Parquet history
# ============================================================
with tab_history:
    st.subheader("Historical Vitals Analytics (DuckDB)")

    if not os.path.exists(VITALS_FILE):
        st.info("No data yet. Send some vitals through the pipeline first.")
    else:
        try:
            import duckdb

            con = duckdb.connect()
            con.execute(f"CREATE OR REPLACE VIEW vitals AS SELECT * FROM read_parquet('{VITALS_FILE}')")

            # Summary stats
            col1, col2, col3, col4 = st.columns(4)
            total = con.execute("SELECT COUNT(*) FROM vitals").fetchone()[0]
            anomalies = con.execute("SELECT COUNT(*) FROM vitals WHERE triage_severity != 'NORMAL'").fetchone()[0]
            agents_used = con.execute("SELECT COUNT(*) FROM vitals WHERE agent_used != ''").fetchone()[0]

            col1.metric("Total Readings", total)
            col2.metric("Anomalies", anomalies)
            col3.metric("Agent Calls", agents_used)
            col4.metric("Anomaly Rate", f"{anomalies/max(total,1)*100:.0f}%")

            # Severity breakdown
            st.markdown("#### Severity Distribution")
            severity_df = con.execute("""
                SELECT triage_severity as Severity, COUNT(*) as Count
                FROM vitals GROUP BY triage_severity ORDER BY Count DESC
            """).fetchdf()
            st.bar_chart(severity_df.set_index("Severity"))

            # Vitals over time
            st.markdown("#### Heart Rate Over Time")
            hr_df = con.execute("""
                SELECT timestamp, heart_rate, triage_severity
                FROM vitals ORDER BY timestamp
            """).fetchdf()
            st.line_chart(hr_df.set_index("timestamp")["heart_rate"])

            # Custom query
            st.markdown("#### Custom DuckDB Query")
            query = st.text_area("SQL", value="SELECT * FROM vitals ORDER BY timestamp DESC LIMIT 20")
            if st.button("Run Query"):
                try:
                    result_df = con.execute(query).fetchdf()
                    st.dataframe(result_df, use_container_width=True)
                except Exception as e:
                    st.error(f"Query error: {e}")

            con.close()
        except ImportError:
            st.warning("Install duckdb: `pip install duckdb`")

# ============================================================
# TAB 3: Architecture explanation
# ============================================================
with tab_architecture:
    st.subheader("System Architecture")
    st.markdown("""
```
┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
│  Smart Ring   │────▶│  Azure Service   │────▶│  Consumer    │
│  (Simulator)  │     │  Bus Queue       │     │  (Dequeue)   │
└──────────────┘     └──────────────────┘     └──────┬───────┘
                                                      │
                                          ┌───────────▼────────────┐
                                          │  Deterministic Triage   │
                                          │  (Rule-based engine)    │
                                          │  ALWAYS runs first      │
                                          └───────────┬────────────┘
                                                      │
                                    ┌─────────────────┼─────────────────┐
                                    │ NORMAL          │ ANOMALY         │
                                    │ → Skip agent    │ → Route to      │
                                    │ → Store only    │   specialist    │
                                    │                 │                 │
                              ┌─────▼──────┐   ┌─────▼──────┐   ┌─────▼──────┐
                              │  Cardiac    │   │ Respiratory │   │  General   │
                              │  Agent      │   │  Agent      │   │  Health    │
                              └─────┬──────┘   └─────┬──────┘   └─────┬──────┘
                                    │                 │                 │
                              Tools: RAG,       Tools: RAG,      Tools: RAG,
                              FDA adverse       FDA adverse      FDA drugs,
                              events,           events,          web search,
                              web search        web search       web research
                                    │                 │                 │
                                    └─────────────────┼─────────────────┘
                                                      │
                                          ┌───────────▼────────────┐
                                          │  Storage Layer          │
                                          │  • Parquet → DuckDB    │
                                          │  • Chroma (RAG/KB)     │
                                          └───────────┬────────────┘
                                                      │
                                          ┌───────────▼────────────┐
                                          │  Streamlit Dashboard    │
                                          │  • Live monitor         │
                                          │  • DuckDB analytics     │
                                          └────────────────────────┘
```

### Key Design Decisions

**1. Deterministic First, LLM Second**
The triage engine uses pure rule-based logic — no LLM, no cost, sub-millisecond.
LLM agents only activate when anomalies are detected. This is how production medical
systems work: you don't burn API calls on normal readings.

**2. Multi-Agent Routing**
The supervisor doesn't use an LLM to route — it reads the triage flags and routes
deterministically. Cardiac flags → cardiac agent. SpO2 flags → respiratory agent.
This is a *deterministic workflow for non-deterministic tools*.

**3. Self-Improving Knowledge Base**
When agents use web_search or web_extract, results are automatically chunked, embedded,
and stored in Chroma. Future queries benefit from accumulated knowledge.

**4. Skills Manifest (skills.md)**
Each agent's available tools are defined in `skills/skills.md`. This is the governance
layer — an agent can only use tools listed under its role.

**5. Event-Driven Architecture**
Producer → Service Bus → Consumer pipeline decouples data ingestion from processing.
In production, this scales independently and handles burst traffic.
    """)
