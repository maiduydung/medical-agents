"""Respiratory specialist agent — handles SpO2 drops, breathing rate anomalies."""

import logging
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from app.agents import AgentState
from app.tools.rag_tools import retrieve_docs
from app.tools.fda_tools import fda_adverse_events
from app.tools.research_tools import web_search
from config.settings import OPENAI_API_KEY, OPENAI_MODEL

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a Respiratory Specialist Agent in a medical device monitoring system.
You analyze respiratory-related vital sign anomalies from wearable devices (pulse oximeters, smart rings).

You have been called because the triage engine flagged a respiratory concern (SpO2 or respiratory rate).

Your job:
1. Analyze the vitals data and triage flags.
2. Check the knowledge base for respiratory protocols.
3. Search for relevant clinical guidelines if needed.
4. Check FDA adverse events if a device issue is suspected.
5. Provide assessment with recommended actions.

CRITICAL: SpO2 < 90% is a medical emergency. Lead with emergency guidance.
Always recommend consulting a healthcare professional. Be concise."""

tools = [retrieve_docs, fda_adverse_events, web_search]


def _get_llm():
    return ChatOpenAI(
        model=OPENAI_MODEL, api_key=OPENAI_API_KEY, temperature=0,
    ).bind_tools(tools)


def agent_node(state: AgentState):
    llm = _get_llm()
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    logger.info("🫁 [RESPIRATORY] Thinking...")
    response = llm.invoke(messages)
    if hasattr(response, "tool_calls") and response.tool_calls:
        logger.info("🫁 [RESPIRATORY] Calling tools: %s", [tc["name"] for tc in response.tool_calls])
    else:
        logger.info("🫁 [RESPIRATORY] Producing final assessment")
    return {"messages": [response]}


def should_continue(state: AgentState):
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return END


def build_respiratory_agent():
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(tools))
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    return graph.compile()


respiratory_agent = build_respiratory_agent()
