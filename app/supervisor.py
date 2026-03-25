"""Supervisor agent — orchestrates the full pipeline.

Flow:
1. Vitals come in from the event queue
2. Deterministic triage runs FIRST (no LLM, pure rules)
3. If anomaly detected → route to specialist agent
4. Specialist analyzes with tools (RAG, FDA, web search)
5. Action layer: escalate based on severity (notify, page nurse, call 911)
6. Return decision + assessment + action taken
"""

import logging
from datetime import datetime, timezone
from langchain_core.messages import HumanMessage
from app.tools.triage import triage_vitals
from app.agents.cardiac import cardiac_agent
from app.agents.respiratory import respiratory_agent
from app.agents.general_health import general_health_agent

logger = logging.getLogger(__name__)

AGENT_MAP = {
    "cardiac": cardiac_agent,
    "respiratory": respiratory_agent,
    "general_health": general_health_agent,
}

# Action escalation matrix — deterministic, no LLM needed
ESCALATION_ACTIONS = {
    "NORMAL": {
        "action": "none",
        "description": "No action required. Vitals within normal range.",
    },
    "WARNING": {
        "action": "notify_patient",
        "description": "Push notification sent to patient. Suggest monitoring and rest.",
    },
    "CRITICAL": {
        "action": "page_nurse",
        "description": "Nurse paged via on-call system. Patient flagged for priority review.",
    },
    "EMERGENCY": {
        "action": "call_emergency",
        "description": "Emergency services contacted. Nurse paged. Patient alerted with emergency instructions.",
    },
}


async def process_vitals(vitals: dict) -> dict:
    """Process a single vitals reading through the full pipeline.

    Returns:
        {
            "timestamp": str,
            "vitals": dict,
            "triage": dict,
            "agent_used": str | None,
            "assessment": str | None,
            "action": dict,
        }
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    hr = vitals.get("heart_rate", "?")
    bp_s = vitals.get("systolic_bp", "?")
    bp_d = vitals.get("diastolic_bp", "?")
    spo2 = vitals.get("spo2", "?")
    temp = vitals.get("temperature", "?")
    rr = vitals.get("respiratory_rate", "?")
    logger.info("📥 [PIPELINE] New vitals received — HR=%s  BP=%s/%s  SpO2=%s  Temp=%s  RR=%s",
                hr, bp_s, bp_d, spo2, temp, rr)

    # Step 1: Deterministic triage (fast, free, always runs)
    logger.info("⚡ [TRIAGE] Running deterministic rule engine...")
    triage = triage_vitals(vitals)
    severity = triage["severity"]
    abnormal = [f for f in triage["flags"] if f["severity"] != "NORMAL"]
    logger.info("⚡ [TRIAGE] Result: %s — %d abnormal flags", severity, len(abnormal))
    for f in abnormal:
        logger.info("⚡ [TRIAGE]   └─ %s", f["description"])

    # Step 2: Determine escalation action (deterministic — always runs)
    action = ESCALATION_ACTIONS[severity].copy()
    action_emoji = {
        "none": "✅", "notify_patient": "📱",
        "page_nurse": "👩‍⚕️", "call_emergency": "🚨",
    }.get(action["action"], "❓")
    logger.info("%s [ACTION] %s — %s", action_emoji, action["action"].upper(), action["description"])

    result = {
        "timestamp": timestamp,
        "vitals": vitals,
        "triage": triage,
        "agent_used": None,
        "assessment": None,
        "action": action,
    }

    # Step 3: If normal, skip agent (saves cost + latency)
    if not triage["requires_agent"]:
        logger.info("✅ [PIPELINE] All vitals normal — skipping LLM agent ($0 cost)")
        result["assessment"] = "All vitals within normal range. No action required."
        return result

    # Step 4: Route to specialist agent
    agent_name = triage["recommended_agent"]
    agent = AGENT_MAP.get(agent_name)
    if not agent:
        logger.warning("⚠️ [PIPELINE] Unknown agent '%s' — falling back to general_health", agent_name)
        agent = general_health_agent
        agent_name = "general_health"

    result["agent_used"] = agent_name
    agent_emoji = {"cardiac": "❤️", "respiratory": "🫁", "general_health": "🩺"}.get(agent_name, "🤖")
    logger.info("🔀 [ROUTER] Severity=%s → routing to %s %s agent", severity, agent_emoji, agent_name.upper())

    # Build the message for the specialist
    prompt = (
        f"Incoming vitals reading from a wearable medical device (smart ring):\n\n"
        f"Vitals: {vitals}\n\n"
        f"Triage Result: {triage['summary']}\n"
        f"Severity: {triage['severity']}\n"
        f"Flagged vitals: {[f['description'] for f in triage['flags'] if f['severity'] != 'NORMAL']}\n\n"
        f"Action taken: {action['description']}\n\n"
        f"Please analyze these readings and provide your assessment."
    )

    # Step 5: Run specialist agent
    logger.info("%s [%s] Agent starting LangGraph loop...", agent_emoji, agent_name.upper())
    try:
        agent_result = await agent.ainvoke({
            "messages": [HumanMessage(content=prompt)]
        })
        assessment = agent_result["messages"][-1].content
        result["assessment"] = assessment
        logger.info("%s [%s] Agent complete — %d char assessment", agent_emoji, agent_name.upper(), len(assessment))
    except Exception as e:
        logger.error("💥 [%s] Agent failed: %s", agent_name.upper(), e)
        result["assessment"] = f"Agent analysis failed: {e}. Based on triage: {triage['summary']}"

    logger.info("📦 [PIPELINE] Done — severity=%s, agent=%s, action=%s", severity, agent_name, action["action"])
    return result
