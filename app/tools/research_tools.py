"""Web research tools — Tavily search + auto-ingest to knowledge base."""

import logging
from langchain_core.tools import tool
from app.enrichment import ingest_to_chroma

logger = logging.getLogger(__name__)


def _get_tavily_client():
    from tavily import TavilyClient
    from config.settings import TAVILY_API_KEY
    if not TAVILY_API_KEY:
        raise ValueError("TAVILY_API_KEY not set")
    return TavilyClient(api_key=TAVILY_API_KEY)


@tool
def web_search(query: str, category: str = "general") -> str:
    """Search the web for medical information using Tavily. Fast and cheap.

    Use for: clinical guidelines, device specifications, recent medical news,
    drug information, treatment protocols.

    Results are automatically stored in the knowledge base for future queries.

    Args:
        query: Search query, e.g. "tachycardia treatment guidelines 2025"
        category: Category for storage (e.g. "cardiac", "respiratory", "general").
    """
    logger.info("Web search: %s (category=%s)", query, category)
    client = _get_tavily_client()
    response = client.search(query=query, max_results=5, include_answer=True)

    parts = []
    if response.get("answer"):
        parts.append(f"Summary: {response['answer']}")
    for r in response.get("results", []):
        parts.append(f"[{r.get('title', '')}]({r.get('url', '')})\n{r.get('content', '')}")

    extracted = "\n\n---\n\n".join(parts)
    logger.info("Tavily returned %d results (%d chars)", len(response.get("results", [])), len(extracted))

    if not extracted or len(extracted) < 20:
        return f"No web results found for '{query}'."

    # Self-improving: auto-ingest into knowledge base
    try:
        n_chunks = ingest_to_chroma(extracted, category, source_type="web_search")
        logger.info("Auto-ingested %d chunks into knowledge base", n_chunks)
    except Exception as e:
        logger.warning("Auto-ingest failed (non-blocking): %s", e)

    return extracted


@tool
def web_extract(url: str, category: str = "general") -> str:
    """Extract and read the full content of a specific URL.

    Use when you have a specific URL (article, clinical guideline, FDA page)
    and want to read its full content.

    Args:
        url: The URL to extract content from.
        category: Category for storage.
    """
    logger.info("Extracting URL: %s", url)
    client = _get_tavily_client()
    response = client.extract(url)

    parts = []
    for r in response.get("results", []):
        parts.append(r.get("raw_content", "") or r.get("content", ""))

    extracted = "\n\n".join(parts)
    logger.info("Extracted %d chars from %s", len(extracted), url)

    if not extracted or len(extracted) < 20:
        return f"Could not extract content from {url}."

    try:
        n_chunks = ingest_to_chroma(extracted, category, source_type="web_extract")
        logger.info("Auto-ingested %d chunks from URL", n_chunks)
    except Exception as e:
        logger.warning("Auto-ingest failed (non-blocking): %s", e)

    return extracted[:3000] + ("..." if len(extracted) > 3000 else "")


@tool
def web_research(query: str, category: str = "general") -> str:
    """Deep multi-source web research. Use for complex medical questions
    that need multiple sources synthesized.

    This is slower and more expensive — only use when a simple search isn't enough.

    Args:
        query: Research question, e.g. "What are the latest FDA guidelines for wearable cardiac monitors?"
        category: Category for storage.
    """
    logger.info("Deep research: %s", query)
    client = _get_tavily_client()
    response = client.search(query=query, max_results=10, include_answer=True, search_depth="advanced")

    parts = []
    if response.get("answer"):
        parts.append(f"Research Summary: {response['answer']}")
    for r in response.get("results", []):
        parts.append(f"[{r.get('title', '')}]({r.get('url', '')})\n{r.get('content', '')}")

    extracted = "\n\n---\n\n".join(parts)
    logger.info("Deep research returned %d chars", len(extracted))

    if not extracted or len(extracted) < 20:
        return f"No research results for '{query}'."

    try:
        n_chunks = ingest_to_chroma(extracted, category, source_type="web_research")
        logger.info("Auto-ingested %d chunks from research", n_chunks)
    except Exception as e:
        logger.warning("Auto-ingest failed (non-blocking): %s", e)

    return extracted[:5000] + ("..." if len(extracted) > 5000 else "")
