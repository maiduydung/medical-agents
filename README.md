# MedTech Agent Monitor

Real-time vitals monitoring system with **multi-agent AI triage**.
Simulates a **smart ring** (like ITR's biosensor ring / cardiac monitor) sending health metrics through an event-driven pipeline where deterministic rules and LLM agents work together to detect anomalies, assess risk, escalate actions, and recommend next steps.

---

## System Architecture

```mermaid
flowchart TB
    subgraph Input["Data Ingestion"]
        Ring["🫀 Smart Ring<br/>(Simulator)"]
        SB["Azure Service Bus<br/>(vitals queue)"]
        Ring -->|"JSON vitals every 1s"| SB
    end

    subgraph Pipeline["Processing Pipeline"]
        Consumer["Consumer<br/>(dequeue)"]
        Triage["⚡ Deterministic Triage<br/>(rule-based engine)"]
        SB --> Consumer --> Triage

        Triage -->|"NORMAL"| Skip["✅ Skip Agent<br/>$0 cost"]
        Triage -->|"WARNING / CRITICAL / EMERGENCY"| Action

        Action["Escalation Action<br/>(deterministic)"]
        Action -->|"📱 notify patient"| Router
        Action -->|"👩‍⚕️ page nurse"| Router
        Action -->|"🚨 call 911"| Router

        Router["🔀 Supervisor Router<br/>(reads triage flags)"]
        Router -->|"heart_rate flags"| Cardiac["❤️ Cardiac Agent"]
        Router -->|"spo2 / resp flags"| Respiratory["🫁 Respiratory Agent"]
        Router -->|"temp / bp / multi"| General["🩺 General Health Agent"]
    end

    subgraph Tools["Agent Tools (skills.md governed)"]
        RAG["📚 retrieve_docs<br/>(Chroma Cloud)"]
        FDADevice["🏛️ openFDA Device API<br/>adverse events + recalls"]
        FDADrug["💊 openFDA Drug API<br/>drug interactions"]
        Web["🔍 Tavily Web Search<br/>clinical guidelines"]

        Cardiac --> RAG & FDADevice & Web
        Respiratory --> RAG & FDADevice & Web
        General --> RAG & FDADrug & Web
    end

    subgraph Storage["Storage Layer"]
        Parquet["💾 Parquet + DuckDB<br/>(vitals + decisions + actions)"]
        Chroma["🧠 Chroma Cloud<br/>(self-improving knowledge base)"]

        Skip --> Parquet
        Cardiac & Respiratory & General --> Parquet
        Web -->|"auto-ingest"| Chroma
        FDADevice -->|"auto-ingest"| Chroma
        FDADrug -->|"auto-ingest"| Chroma
        RAG -.->|"reads"| Chroma
        Parquet -.->|"SQL queries"| DuckDB["DuckDB"]
    end

    subgraph UI["Presentation"]
        API["FastAPI Server<br/>(REST + SSE)"]
        Dashboard["Streamlit Dashboard<br/>(live monitor + analytics)"]
        API --> Dashboard
        DuckDB --> Dashboard
    end

    style Ring fill:#e8f5e9
    style Triage fill:#fff3e0
    style Action fill:#fff3e0
    style Cardiac fill:#ffebee
    style Respiratory fill:#e3f2fd
    style General fill:#f3e5f5
    style Chroma fill:#e8eaf6
    style Parquet fill:#e8eaf6
    style FDADevice fill:#ffebee
    style FDADrug fill:#fce4ec
```

## Agent Decision Flow

```mermaid
flowchart LR
    V["Vitals In"] --> T{"⚡ Deterministic<br/>Triage"}
    T -->|"All normal"| N["✅ NORMAL<br/>Store & skip<br/>$0 cost"]
    T -->|"Anomaly"| S{"Severity?"}

    S -->|"WARNING"| W["📱 Notify Patient"]
    S -->|"CRITICAL"| C["👩‍⚕️ Page Nurse"]
    S -->|"EMERGENCY"| E["🚨 Call 911 +<br/>Page Nurse"]

    W --> R["🔀 Route to<br/>Specialist"]
    C --> R
    E --> R

    R --> Agent["LangGraph Agent<br/>(tool loop)"]
    Agent -->|"needs data"| Tools["Tools<br/>RAG / FDA / Web"]
    Tools -->|"auto-ingest<br/>to Chroma"| Agent
    Agent --> Out["Assessment +<br/>Action Taken"]
    Out --> Store["💾 Parquet"]

    style N fill:#c8e6c9
    style W fill:#fff9c4
    style C fill:#ffe0b2
    style E fill:#ffcdd2
    style Agent fill:#bbdefb
```

## LangGraph Agent Loop (per specialist)

```mermaid
stateDiagram-v2
    [*] --> agent: HumanMessage (vitals + triage + action taken)
    agent --> tools: has tool_calls
    agent --> [*]: no tool_calls (final assessment)
    tools --> agent: tool results

    state agent {
        [*] --> LLM: SystemPrompt + messages
        LLM --> Decision: response
    }

    state tools {
        [*] --> ToolNode: execute tool calls
        ToolNode --> [*]: return results
    }
```

## openFDA Tool Architecture

```mermaid
flowchart LR
    subgraph openFDA["openFDA API (free, no key)"]
        DeviceDB[("/device/event<br/>/device/recall")]
        DrugDB[("/drug/event")]
    end

    AE["🏛️ fda_adverse_events<br/>HARDWARE: device malfunctions"] --> DeviceDB
    DR["🏛️ fda_device_recall<br/>HARDWARE: safety recalls"] --> DeviceDB
    DI["💊 fda_drug_interactions<br/>MEDICATION: side effects"] --> DrugDB

    DeviceDB & DrugDB -->|"auto-ingest"| Chroma["🧠 Chroma Cloud"]

    style AE fill:#ffebee
    style DR fill:#ffebee
    style DI fill:#fce4ec
    style Chroma fill:#e8eaf6
```

---

## Project Structure & Call Graph

```
medical-agents/
├── producer.py              # CLI: simulate ring → send to Service Bus
│   └── calls: simulator.generate_vitals() → event_bus.send_vitals()
│
├── consumer.py              # CLI: dequeue from Service Bus → run pipeline
│   └── calls: event_bus.receive_vitals() → supervisor.process_vitals() → storage.store_result()
│
├── app/
│   ├── main.py              # FastAPI server (REST + SSE endpoints)
│   │   ├── POST /process         → supervisor.process_vitals() → storage.store_result()
│   │   ├── POST /process/stream  → same, with SSE log streaming
│   │   └── GET  /health
│   │
│   ├── supervisor.py        # Orchestrator — the brain
│   │   └── process_vitals(vitals)
│   │       ├── 1. triage.triage_vitals()           # deterministic rules
│   │       ├── 2. ESCALATION_ACTIONS[severity]     # deterministic action (notify/page/call)
│   │       ├── 3. if NORMAL → return early          # no LLM cost
│   │       └── 4. if anomaly → route to agent:
│   │           ├── cardiac_agent.ainvoke()
│   │           ├── respiratory_agent.ainvoke()
│   │           └── general_health_agent.ainvoke()
│   │
│   ├── simulator.py         # Generates realistic vitals (normal + anomaly scenarios)
│   │   └── generate_vitals(anomaly_chance) → dict
│   │
│   ├── event_bus.py         # Azure Service Bus producer/consumer
│   │   ├── send_vitals(vitals)       # sync, used by producer
│   │   ├── send_vitals_batch(list)   # sync batch send
│   │   └── receive_vitals()          # async, used by consumer
│   │
│   ├── storage.py           # Parquet writer for DuckDB analytics
│   │   └── store_result(result) → appends row to data/vitals_history.parquet
│   │
│   ├── enrichment.py        # Chroma Cloud ingestion (chunk → embed → store)
│   │   ├── chunk_text(text)
│   │   └── ingest_to_chroma(text, category) → int (chunks stored)
│   │
│   ├── retriever.py         # Chroma Cloud similarity search
│   │   └── retrieve_docs(query, category) → list[dict]
│   │
│   ├── agents/              # LangGraph specialist agents
│   │   ├── __init__.py      # Shared AgentState TypedDict
│   │   ├── cardiac.py       # Heart rate anomalies, arrhythmia
│   │   │   └── tools: retrieve_docs, fda_adverse_events, web_search, web_extract
│   │   ├── respiratory.py   # SpO2 drops, breathing rate
│   │   │   └── tools: retrieve_docs, fda_adverse_events, web_search
│   │   └── general_health.py # Temperature, BP, multi-metric
│   │       └── tools: retrieve_docs, fda_drug_interactions, web_search, web_research
│   │
│   └── tools/               # Tool definitions (LangChain @tool decorated)
│       ├── triage.py        # Rule-based vital sign classification (NO LLM)
│       │   ├── triage_vitals(vitals) → {severity, flags, recommended_agent}
│       │   └── VITAL_RULES dict (clinical thresholds per metric)
│       ├── fda_tools.py     # openFDA API (free, no key needed) — TWO databases:
│       │   ├── fda_adverse_events(device_name)  # /device/event — HARDWARE malfunctions
│       │   ├── fda_device_recall(device_name)   # /device/recall — HARDWARE recalls
│       │   └── fda_drug_interactions(drug_name) # /drug/event — MEDICATION side effects
│       │   └── all results auto-ingest into Chroma
│       ├── research_tools.py # Tavily web search + auto-ingest
│       │   ├── web_search(query)    # quick search, auto-stores to Chroma
│       │   ├── web_extract(url)     # full page read, auto-stores
│       │   └── web_research(query)  # deep multi-source research
│       └── rag_tools.py     # Vector DB retrieval
│           └── retrieve_docs(query, category) # Chroma similarity search
│
├── config/
│   └── settings.py          # All env vars (OpenAI, Chroma, Tavily, Service Bus)
│
├── skills/
│   └── skills.md            # Tool governance manifest — which agent gets which tools
│
├── ui/
│   └── streamlit_app.py     # Dashboard: live monitor + DuckDB analytics + architecture
│
├── data/                    # Generated at runtime (gitignored)
│   └── vitals_history.parquet
│
├── requirements.txt
├── .env / .env.example
└── README.md
```

### Call Flow: End-to-End

```
producer.py                          consumer.py / FastAPI
    │                                     │
    ▼                                     ▼
generate_vitals()                    receive_vitals() / HTTP request
    │                                     │
    ▼                                     ▼
send_vitals()  ──── Service Bus ────  process_vitals()
                                          │
                                          ├─► triage_vitals()           [deterministic, <1ms]
                                          │
                                          ├─► ESCALATION_ACTIONS        [deterministic]
                                          │       ├─ WARNING   → 📱 notify patient
                                          │       ├─ CRITICAL  → 👩‍⚕️ page nurse
                                          │       └─ EMERGENCY → 🚨 call 911
                                          │
                                          ├─► NORMAL? → skip agent      [no LLM, $0]
                                          │
                                          ├─► cardiac_agent    ─┐
                                          ├─► respiratory_agent ─┼──► LangGraph loop
                                          └─► general_agent    ─┘     │
                                                                      ├─► retrieve_docs()      [Chroma]
                                                                      ├─► fda_adverse_events()  [openFDA → auto-ingest]
                                                                      ├─► fda_drug_interactions()[openFDA → auto-ingest]
                                                                      ├─► web_search()          [Tavily → auto-ingest]
                                                                      └─► assessment
                                                                              │
                                                                              ▼
                                                                        store_result()  → Parquet
                                                                              │
                                                                              ▼
                                                                        DuckDB queries ← Streamlit
```

---

## Key Design Patterns

### 1. Deterministic Triage Before LLM
The triage engine (`app/tools/triage.py`) uses pure rule-based logic with clinical thresholds.
No LLM, no API call, sub-millisecond. Normal readings (majority of traffic) never touch OpenAI.
This is how production medical systems work — you don't burn $0.01/call on normal heartbeats.

### 2. Action Escalation Matrix
Before the LLM even starts thinking, the system fires a deterministic action based on severity:
WARNING → push notification to patient, CRITICAL → page on-call nurse, EMERGENCY → contact emergency services.
Actions are instant and rule-based. The LLM assessment arrives after and provides clinical context.

### 3. Multi-Agent with Deterministic Routing
The supervisor (`app/supervisor.py`) doesn't use an LLM to decide which agent to call.
It reads the triage flags and routes deterministically: cardiac flags → cardiac agent, SpO2 flags → respiratory agent.
This is a **deterministic workflow wrapping non-deterministic tools** — the routing is guaranteed, the analysis is flexible.

### 4. Skills Manifest (`skills/skills.md`)
Each agent's available tools are defined in a manifest file. This is the governance layer —
it documents what each agent can and cannot do, enforcing the principle of least privilege.
The manifest also includes usage guidelines (cost awareness, escalation rules, audit requirements).

### 5. Self-Improving Knowledge Base
ALL external data tools auto-ingest results into Chroma Cloud:
- `web_search` / `web_extract` / `web_research` → Tavily results → Chroma
- `fda_adverse_events` / `fda_device_recall` → openFDA device data → Chroma
- `fda_drug_interactions` → openFDA drug data → Chroma

Future queries benefit from previously accumulated knowledge. The system gets smarter with every anomaly it processes.

### 6. Event-Driven Decoupled Architecture
Producer → Azure Service Bus → Consumer. Data ingestion is fully decoupled from processing.
In production, these scale independently: burst 10,000 readings/sec into the queue, consume at agent capacity.

### 7. Columnar Analytics
Processed results (vitals + triage + action + assessment) are stored as Parquet. DuckDB reads Parquet
in-process with zero setup — no database server needed. Enables SQL analytics directly in the Streamlit dashboard.

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| LLM | OpenAI GPT-5.4 | Agent reasoning and assessment |
| Embeddings | text-embedding-3-small | Vector search for RAG |
| Agent Framework | LangGraph | State machine orchestration, tool routing |
| Vector DB | Chroma Cloud | Knowledge base for RAG (self-improving) |
| External API | openFDA (device + drug) | Adverse events, recalls, drug interactions (free) |
| Web Search | Tavily | Real-time medical research with auto-ingest |
| Event Queue | Azure Service Bus (Basic) | Decoupled vitals ingestion |
| Analytics | Parquet + DuckDB | Columnar storage + in-process SQL |
| API | FastAPI | REST + SSE streaming endpoints |
| Dashboard | Streamlit | Live monitoring + analytics UI |

---

## Quick Start

### 1. Install dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Set up environment
```bash
cp .env.example .env
# Fill in: OPENAI_API_KEY, CHROMA_*, TAVILY_API_KEY, SERVICEBUS_CONNECTION_STRING
```

### 3. Start the API server
```bash
uvicorn app.main:app --port 8000 --reload
```

### 4. Start the dashboard
```bash
streamlit run ui/streamlit_app.py
```

### 5. (Optional) Event-driven mode with Service Bus
```bash
# Terminal A: Simulate smart ring sending vitals to queue
python producer.py --count 20 --interval 1 --anomaly-chance 0.3

# Terminal B: Consume from queue and process through agent pipeline
python consumer.py
```

### 6. Quick test via curl
```bash
# Normal reading — instant response, no LLM call, action=none
curl -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{"heart_rate": 72, "systolic_bp": 118, "diastolic_bp": 76, "spo2": 98, "temperature": 36.6, "respiratory_rate": 16}'

# Tachycardia — triggers 🚨 call_emergency + Cardiac Agent
curl -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{"heart_rate": 165, "systolic_bp": 130, "diastolic_bp": 85, "spo2": 96, "temperature": 36.8, "respiratory_rate": 22}'
```

---

## Demo Scenarios

| Scenario | Vitals | Triage | Action | Agent | What happens |
|----------|--------|--------|--------|-------|-------------|
| Normal | HR=72, BP=118/76, SpO2=98 | NORMAL | none | — | Instant, $0, stored to parquet |
| Tachycardia | HR=165, BP=130/85 | EMERGENCY | 🚨 call 911 | Cardiac | Emergency paged, agent searches FDA + web |
| Low SpO2 | SpO2=86, RR=28 | CRITICAL | 👩‍⚕️ page nurse | Respiratory | Nurse paged, agent finds hypoxia guidelines |
| Fever + High BP | Temp=39.5, BP=170/105 | CRITICAL | 👩‍⚕️ page nurse | General | Multi-metric analysis, checks drug interactions |
| Bradycardia | HR=42, BP=90/60 | CRITICAL | 👩‍⚕️ page nurse | Cardiac | Agent investigates low HR causes |
| Multi-warning | HR=135, BP=165/105, SpO2=91 | CRITICAL | 👩‍⚕️ page nurse | Cardiac | Multiple flags, comprehensive assessment |

---

## Azure Resources

| Resource | Name | SKU | Cost |
|----------|------|-----|------|
| Service Bus Namespace | `medagentsbus` | Basic | ~$0.05/month |
| Queue | `vitals` | — | Included |
| Subscription | InterviewDemoSubscription | — | `7aec3ed0-...` |
