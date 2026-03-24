"""Cardiac specialist agent — handles heart rate anomalies, arrhythmia, cardiac concerns."""

import logging
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from app.agents import AgentState
from app.tools.rag_tools import retrieve_docs
from app.tools.fda_tools import fda_adverse_events
from app.tools.research_tools import web_search, web_extract
from config.settings import OPENAI_API_KEY, OPENAI_MODEL

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a Cardiac Specialist Agent in a medical device monitoring system.
You analyze cardiac-related vital sign anomalies detected by wearable devices (smart rings, ECG patches, etc.).

You have been called because the deterministic triage engine flagged a cardiac concern.

Your job:
1. Analyze the vitals data and triage flags provided.
2. Use retrieve_docs to check the knowledge base for relevant cardiac protocols.
3. If needed, use web_search for recent guidelines or clinical information.
4. Use fda_adverse_events if the concern might relate to a device malfunction.
5. Provide a clear assessment with:
   - What the readings suggest
   - Possible conditions to consider
   - Recommended actions (monitoring, seek care, emergency)

IMPORTANT:
- You are NOT a doctor. Always recommend consulting a healthcare professional.
- For EMERGENCY severity: lead with "SEEK IMMEDIATE MEDICAL ATTENTION" before analysis.
- Be concise and actionable.
- Cite which tools/sources informed your assessment."""

tools = [retrieve_docs, fda_adverse_events, web_search, web_extract]


def _get_llm():
    return ChatOpenAI(
        model=OPENAI_MODEL, api_key=OPENAI_API_KEY, temperature=0,
    ).bind_tools(tools)


def agent_node(state: AgentState):
    llm = _get_llm()
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    logger.info("❤️  [CARDIAC] Thinking...")
    response = llm.invoke(messages)
    if hasattr(response, "tool_calls") and response.tool_calls:
        tool_names = [tc["name"] for tc in response.tool_calls]
        logger.info("❤️  [CARDIAC] Calling tools: %s", tool_names)
    else:
        logger.info("❤️  [CARDIAC] Producing final assessment")
    return {"messages": [response]}


def should_continue(state: AgentState):
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return END


def build_cardiac_agent():
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(tools))
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    return graph.compile()


cardiac_agent = build_cardiac_agent()
