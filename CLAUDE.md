# CLAUDE.md -- LLM Context for MedTech Agent Monitor

## What is this project?

A multi-agent AI triage system for real-time vitals monitoring. Simulates a smart ring (wearable biosensor) sending health metrics through an event-driven pipeline where **deterministic rules and LLM agents work together** to detect anomalies, assess risk, escalate actions, and recommend next steps.

This is an interview demo project that showcases AI agent architecture, not a production medical system.

## Tech stack

| Layer | Technology |
|-------|-----------|
| Agent framework | LangGraph (state machine orchestration, tool routing) |
| LLM | OpenAI GPT (via langchain-openai) |
| Embeddings | text-embedding-3-small |
| Vector DB | Chroma Cloud (self-improving knowledge base via RAG) |
| External APIs | openFDA device/drug databases (free, no key), Tavily web search |
| Event queue | Azure Service Bus (decoupled vitals ingestion) |
| Analytics | Parquet + DuckDB (columnar storage + in-process SQL) |
| API server | FastAPI (REST + SSE streaming) |
| Dashboard | Streamlit (live monitor + analytics) |
| Language | Python 3.12+ |

## Key files

| File | Purpose |
|------|---------|
| `app/supervisor.py` | Orchestrator -- triage, escalation, agent routing. The brain of the system. |
| `app/tools/triage.py` | Deterministic rule-based vital sign classification. No LLM, sub-millisecond. |
| `app/agents/cardiac.py` | LangGraph agent for heart rate anomalies (tachycardia, bradycardia, arrhythmia) |
| `app/agents/respiratory.py` | LangGraph agent for SpO2 drops and breathing rate anomalies |
| `app/agents/general_health.py` | LangGraph agent for temperature, blood pressure, multi-metric concerns |
| `app/agents/__init__.py` | Shared `AgentState` TypedDict used by all agents |
| `app/tools/fda_tools.py` | openFDA API tools -- device adverse events, recalls, drug interactions |
| `app/tools/research_tools.py` | Tavily web search + extract + deep research, all with auto-ingest to Chroma |
| `app/tools/rag_tools.py` | Vector DB retrieval tool (Chroma similarity search) |
| `app/enrichment.py` | Chunk, embed, and store text in Chroma Cloud |
| `app/retriever.py` | Chroma Cloud similarity search |
| `app/event_bus.py` | Azure Service Bus producer/consumer |
| `app/simulator.py` | Generates realistic vitals (normal + 7 anomaly scenarios) |
| `app/storage.py` | Parquet writer for DuckDB analytics |
| `app/main.py` | FastAPI server (REST + SSE endpoints) |
| `producer.py` | CLI: simulate smart ring sending vitals to Service Bus |
| `consumer.py` | CLI: dequeue from Service Bus, run through agent pipeline |
| `config/settings.py` | All environment variables loaded from .env |
| `skills/skills.md` | Tool governance manifest -- which agent gets which tools |
| `ui/streamlit_app.py` | Dashboard: live monitor + DuckDB analytics |

## Architecture overview

```
Smart Ring (simulator)
    |
    v
Azure Service Bus queue  -or-  FastAPI POST /process
    |
    v
Deterministic Triage (rule engine, <1ms, $0)
    |
    +-- NORMAL --> store to Parquet, skip LLM ($0)
    |
    +-- ANOMALY --> Escalation Action (notify/page nurse/call 911)
                        |
                        v
                    Supervisor Router (deterministic, reads triage flags)
                        |
                        +-- cardiac flags  --> Cardiac Agent (LangGraph)
                        +-- SpO2 flags     --> Respiratory Agent (LangGraph)
                        +-- temp/BP/multi  --> General Health Agent (LangGraph)
                                                    |
                                                    v
                                               Tool Loop:
                                               - retrieve_docs (Chroma RAG)
                                               - fda_adverse_events / fda_drug_interactions
                                               - web_search / web_extract / web_research
                                               (all auto-ingest results back to Chroma)
                                                    |
                                                    v
                                               Assessment --> Parquet --> DuckDB --> Streamlit
```

## How to run locally

```bash
# 1. Install dependencies
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Fill in: OPENAI_API_KEY, CHROMA_*, TAVILY_API_KEY, SERVICEBUS_CONNECTION_STRING

# 3. Start API server
uvicorn app.main:app --port 8000 --reload

# 4. Start dashboard (separate terminal)
streamlit run ui/streamlit_app.py

# 5. (Optional) Event-driven mode
python producer.py --count 20 --anomaly-chance 0.3   # Terminal A
python consumer.py                                    # Terminal B

# 6. Quick test
curl -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{"heart_rate": 165, "systolic_bp": 130, "diastolic_bp": 85, "spo2": 96, "temperature": 36.8, "respiratory_rate": 22}'
```

## Important patterns

- **Deterministic triage before LLM**: Normal readings (majority of traffic) never touch OpenAI. Triage is pure rules with clinical thresholds.
- **Deterministic routing**: The supervisor reads triage flags and routes to the correct specialist agent. No LLM decides which agent to call.
- **Escalation matrix**: Actions (notify patient, page nurse, call 911) fire deterministically based on severity BEFORE the LLM starts thinking.
- **Self-improving knowledge base**: All external tool results (web search, FDA queries) auto-ingest into Chroma. Future queries benefit from accumulated knowledge.
- **LangGraph agent loop**: Each specialist uses the standard `agent -> should_continue -> tools -> agent` loop pattern with `ToolNode`.
- **Skills manifest**: `skills/skills.md` defines which tools each agent can use (principle of least privilege).
- **Event-driven decoupling**: Producer -> Service Bus -> Consumer. Data ingestion scales independently from processing.

## Environment variables

All defined in `config/settings.py`, loaded from `.env`:
- `OPENAI_API_KEY` / `OPENAI_MODEL` / `EMBEDDING_MODEL` -- LLM and embeddings
- `CHROMA_API_KEY` / `CHROMA_TENANT` / `CHROMA_DATABASE` / `CHROMA_COLLECTION` -- vector DB
- `TAVILY_API_KEY` -- web search
- `SERVICEBUS_CONNECTION_STRING` / `SERVICEBUS_QUEUE_NAME` -- Azure Service Bus
- openFDA requires no API key (free public API)
