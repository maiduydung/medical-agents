# MedTech Agent Skills Manifest

This file defines the tools available to each agent in the system.
The supervisor reads this manifest at startup to enforce tool governance —
agents can ONLY use tools listed under their role.

---

## Triage Engine (Deterministic — no LLM)

| Tool | Description |
|------|-------------|
| `check_vitals_rules` | Rule-based vital sign triage (heart rate, BP, SpO2, temp). Returns severity level: NORMAL / WARNING / CRITICAL / EMERGENCY. |
| `check_cardiac_rules` | Cardiac-specific rule checks (arrhythmia flags, bradycardia, tachycardia). |

**When to use:** ALWAYS runs first on every incoming vitals event. Fast, deterministic, zero cost.
**When NOT to use:** Never skip this step — even if LLM is available.

---

## Cardiac Agent

| Tool | Description |
|------|-------------|
| `retrieve_docs` | Search medical knowledge base (Chroma) for cardiac conditions, protocols, drug interactions. |
| `fda_adverse_events` | Query openFDA for device adverse events related to cardiac monitors, pacemakers, wearables. |
| `web_search` | Search web for recent cardiac research, guidelines, drug recalls. Auto-ingests results to knowledge base. |
| `web_extract` | Extract full content from a specific URL. Auto-ingests to knowledge base. |

**When to use:** Heart rate anomalies, arrhythmia patterns, cardiac-related alerts.
**Escalation:** If severity is EMERGENCY, recommend immediate medical attention BEFORE analysis.

---

## Respiratory Agent

| Tool | Description |
|------|-------------|
| `retrieve_docs` | Search medical knowledge base for respiratory conditions (SpO2, breathing rate). |
| `fda_adverse_events` | Query openFDA for adverse events related to pulse oximeters, respiratory devices. |
| `web_search` | Search for respiratory guidelines and protocols. |

**When to use:** SpO2 drops, abnormal respiratory rate.
**Escalation:** SpO2 < 90% is a medical emergency.

---

## General Health Agent

| Tool | Description |
|------|-------------|
| `retrieve_docs` | Search knowledge base for general health conditions. |
| `fda_drug_interactions` | Check openFDA for drug-related adverse events and interactions. |
| `web_search` | General medical research. |
| `web_research` | Deep multi-source research for complex or multi-symptom presentations. |

**When to use:** Temperature anomalies, multi-metric concerns, general health questions.

---

## Tool Governance Rules

1. **Deterministic first**: Rule-based triage ALWAYS runs before any LLM agent.
2. **Cost awareness**: Prefer `retrieve_docs` (free) → `web_search` (cheap) → `web_research` (expensive).
3. **Auto-enrichment**: All web results are automatically stored in the knowledge base.
4. **Emergency protocol**: CRITICAL/EMERGENCY severity bypasses deep analysis — immediate alert.
5. **Audit trail**: Every tool call is logged with timestamp, agent, input, and output.
