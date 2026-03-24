"""General health agent — handles temperature, blood pressure, multi-metric concerns."""

import logging
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from app.agents import AgentState
from app.tools.rag_tools import retrieve_docs
from app.tools.fda_tools import fda_drug_interactions
from app.tools.research_tools import web_search, web_research
from config.settings import OPENAI_API_KEY, OPENAI_MODEL

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a General Health Agent in a medical device monitoring system.
You handle vital sign anomalies that don't fall strictly into cardiac or respiratory categories:
temperature spikes, blood pressure concerns, or multi-metric patterns.

Your job:
1. Analyze the vitals data and triage flags.
2. Check the knowledge base for relevant health protocols.
3. Check for drug interactions if relevant.
4. Search for clinical guidelines if needed.
5. Provide assessment with recommended actions.

Always recommend consulting a healthcare professional. Be concise and actionable."""

tools = [retrieve_docs, fda_drug_interactions, web_search, web_research]


def _get_llm():
    return ChatOpenAI(
        model=OPENAI_MODEL, api_key=OPENAI_API_KEY, temperature=0,
    ).bind_tools(tools)


def agent_node(state: AgentState):
    llm = _get_llm()
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm.invoke(messages)
    logger.info("🩺 [GENERAL] Thinking...")
    if hasattr(response, "tool_calls") and response.tool_calls:
        logger.info("🩺 [GENERAL] Calling tools: %s", [tc["name"] for tc in response.tool_calls])
    else:
        logger.info("🩺 [GENERAL] Producing final assessment")
    return {"messages": [response]}


def should_continue(state: AgentState):
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return END


def build_general_agent():
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(tools))
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    return graph.compile()


general_health_agent = build_general_agent()
