"""RAG tools — vector database retrieval."""

import logging
from langchain_core.tools import tool
from app.retriever import retrieve_docs as _retrieve

logger = logging.getLogger(__name__)


@tool
def retrieve_docs(query: str, category: str | None = None) -> str:
    """Retrieve relevant medical documents from the knowledge base (vector DB).

    Search for clinical guidelines, device info, drug interactions, past research.
    This is free and fast — always try this before web search.

    Args:
        query: What information you need, e.g. "tachycardia treatment protocol"
        category: Optional filter — "cardiac", "respiratory", "general", etc.
    """
    logger.info("📚 [RAG] Searching knowledge base — query='%s', category=%s", query, category)
    docs = _retrieve(query, category=category, n_results=5)
    if not docs:
        logger.info("📚 [RAG] No documents found in knowledge base")
        return "No relevant documents found in the knowledge base."
    logger.info("📚 [RAG] Retrieved %d documents (top distance=%.3f)", len(docs), docs[0]["distance"])
    parts = []
    for doc in docs:
        meta = doc["metadata"]
        parts.append(f"[{meta.get('category', '?')} | {meta.get('source_type', '?')}]\n{doc['text']}")
    return "\n\n---\n\n".join(parts)
