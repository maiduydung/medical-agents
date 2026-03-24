# MedTech Agent Monitor

Real-time vitals monitoring system with multi-agent AI triage.
Simulates a **smart ring** (like ITR's biosensor ring) sending health metrics through an event-driven pipeline.

## Architecture

```
Smart Ring          Azure Service Bus       Consumer           Agent Pipeline
(Simulator) ──────▶ (vitals queue) ──────▶ (dequeue) ──────▶ (LangGraph)
                                                                  │
                                                    ┌─────────────┤
                                                    ▼             ▼
                                              Deterministic    LLM Agents
                                              Triage Engine    (if anomaly)
                                              (rule-based)         │
                                                    │    ┌────────┼────────┐
                                                    │    ▼        ▼        ▼
                                                    │  Cardiac  Resp.   General
                                                    │  Agent    Agent   Agent
                                                    │    │        │        │
                                                    ▼    ▼        ▼        ▼
                                              ┌──────────────────────────────┐
                                              │  Storage                      │
                                              │  • Parquet → DuckDB (vitals)  │
                                              │  • Chroma Cloud (RAG/KB)      │
                                              └──────────────┬───────────────┘
                                                             ▼
                                                    Streamlit Dashboard
```

## Key Patterns

| Pattern | Implementation |
|---------|---------------|
| **Multi-agent system** | Supervisor routes to Cardiac / Respiratory / General Health agents |
| **Deterministic + LLM** | Rule-based triage runs FIRST; LLM only on anomalies (cost-efficient) |
| **Skills manifest** | `skills/skills.md` defines which tools each agent can access |
| **Self-improving RAG** | Web search results auto-ingest into Chroma knowledge base |
| **Event-driven** | Producer → Azure Service Bus → Consumer (decoupled, scalable) |
| **Analytics** | Parquet storage + DuckDB for historical queries in dashboard |

## Tech Stack

- **LangGraph** — agent orchestration (state machines, tool routing)
- **OpenAI** — LLM (GPT-4.1) + embeddings
- **Chroma Cloud** — vector database for RAG
- **openFDA API** — real FDA adverse events, recalls, drug interactions (free)
- **Tavily** — web search with auto-ingest
- **Azure Service Bus** — event queue (Basic tier)
- **Parquet + DuckDB** — columnar analytics
- **FastAPI** — REST API with SSE streaming
- **Streamlit** — real-time monitoring dashboard

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set up .env
```bash
cp .env.example .env
# Fill in your API keys
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
# Terminal 1: Send vitals to queue
python producer.py --count 20 --interval 1

# Terminal 2: Consume and process
python consumer.py
```

## Demo Scenarios

**Normal reading** → Triage says NORMAL, no agent called, stored to parquet
**Tachycardia (HR=160)** → Triage flags CRITICAL, routes to Cardiac Agent, agent searches FDA + knowledge base
**Low SpO2 (88%)** → Triage flags EMERGENCY, routes to Respiratory Agent, immediate alert
**Fever + High BP** → Multiple flags, routes to General Health Agent for multi-metric analysis
