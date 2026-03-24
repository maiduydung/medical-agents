"""Supervisor agent — orchestrates the full pipeline.

Flow:
1. Vitals come in from the event queue
2. Deterministic triage runs FIRST (no LLM, pure rules)
3. If anomaly detected → route to specialist agent
4. Specialist analyzes with tools (RAG, FDA, web search)
5. Return decision + assessment
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


async def process_vitals(vitals: dict) -> dict:
    """Process a single vitals reading through the full pipeline.

    Args:
        vitals: Dict with heart_rate, systolic_bp, diastolic_bp, spo2, temperature, respiratory_rate, etc.

    Returns:
        {
            "timestamp": str,
            "vitals": dict,
            "triage": dict,
            "agent_used": str | None,
            "assessment": str | None,
        }
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    logger.info("Processing vitals at %s", timestamp)

    # Step 1: Deterministic triage (fast, free, always runs)
    triage = triage_vitals(vitals)
    logger.info("Triage: %s — %s", triage["severity"], triage["summary"])

    result = {
        "timestamp": timestamp,
        "vitals": vitals,
        "triage": triage,
        "agent_used": None,
        "assessment": None,
    }

    # Step 2: If normal, skip agent (saves cost + latency)
    if not triage["requires_agent"]:
        logger.info("All vitals normal — no agent needed")
        result["assessment"] = "All vitals within normal range. No action required."
        return result

    # Step 3: Route to specialist agent
    agent_name = triage["recommended_agent"]
    agent = AGENT_MAP.get(agent_name)
    if not agent:
        logger.warning("Unknown agent: %s, falling back to general_health", agent_name)
        agent = general_health_agent
        agent_name = "general_health"

    result["agent_used"] = agent_name
    logger.info("Routing to %s agent", agent_name)

    # Build the message for the specialist
    prompt = (
        f"Incoming vitals reading from a wearable medical device (smart ring):\n\n"
        f"Vitals: {vitals}\n\n"
        f"Triage Result: {triage['summary']}\n"
        f"Severity: {triage['severity']}\n"
        f"Flagged vitals: {[f['description'] for f in triage['flags'] if f['severity'] != 'NORMAL']}\n\n"
        f"Please analyze these readings and provide your assessment."
    )

    # Step 4: Run specialist agent
    try:
        agent_result = await agent.ainvoke({
            "messages": [HumanMessage(content=prompt)]
        })
        assessment = agent_result["messages"][-1].content
        result["assessment"] = assessment
        logger.info("%s agent completed — %d char assessment", agent_name, len(assessment))
    except Exception as e:
        logger.error("Agent %s failed: %s", agent_name, e)
        result["assessment"] = f"Agent analysis failed: {e}. Based on triage: {triage['summary']}"

    return result
