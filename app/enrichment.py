"""Enrichment service — chunks, embeds, and stores text in Chroma Cloud."""

import logging
import uuid
import chromadb
from openai import OpenAI
from config.settings import (
    OPENAI_API_KEY, EMBEDDING_MODEL,
    CHROMA_API_KEY, CHROMA_TENANT, CHROMA_DATABASE, CHROMA_COLLECTION,
)

logger = logging.getLogger(__name__)

CHUNK_SIZE = 500


def _get_chroma_collection():
    client = chromadb.CloudClient(
        tenant=CHROMA_TENANT,
        database=CHROMA_DATABASE,
        api_key=CHROMA_API_KEY,
    )
    return client.get_or_create_collection(name=CHROMA_COLLECTION)


def _embed_texts(texts: list[str]) -> list[list[float]]:
    client = OpenAI(api_key=OPENAI_API_KEY)
    all_embeddings = []
    for i in range(0, len(texts), 100):
        batch = texts[i : i + 100]
        response = client.embeddings.create(input=batch, model=EMBEDDING_MODEL)
        all_embeddings.extend([item.embedding for item in response.data])
    return all_embeddings


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE) -> list[str]:
    if len(text) <= chunk_size:
        return [text]
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]


def ingest_to_chroma(text: str, category: str, source_type: str = "web") -> int:
    """Chunk text, embed, and store in Chroma Cloud. Returns chunks stored."""
    chunks = chunk_text(text)
    if not chunks:
        return 0

    metadata = {
        "category": category,
        "source_type": source_type,
        "date": "current",
    }

    ids = [str(uuid.uuid4()) for _ in chunks]
    metadatas = [metadata.copy() for _ in chunks]

    logger.info("🧠 [CHROMA] Embedding %d chunks (category=%s, source=%s)", len(chunks), category, source_type)
    embeddings = _embed_texts(chunks)

    collection = _get_chroma_collection()
    collection.add(ids=ids, documents=chunks, embeddings=embeddings, metadatas=metadatas)

    logger.info("🧠 [CHROMA] Stored %d chunks in vector DB", len(chunks))
    return len(chunks)
