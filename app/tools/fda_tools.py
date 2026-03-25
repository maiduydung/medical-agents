"""openFDA API tools — free, no key required.

Two different openFDA databases:
- /device/event & /device/recall → HARDWARE (medical device malfunctions, recalls)
- /drug/event → MEDICATION (drug side effects, interactions)

All results auto-ingest into Chroma for future RAG queries.
"""

import logging
import httpx
from langchain_core.tools import tool
from config.settings import OPENFDA_BASE_URL
from app.enrichment import ingest_to_chroma

logger = logging.getLogger(__name__)


def _auto_ingest(text: str, category: str, source: str):
    """Auto-ingest FDA results into Chroma knowledge base."""
    if not text or len(text) < 50:
        return
    try:
        n = ingest_to_chroma(text, category, source_type=source)
        logger.info("🧠 [SELF-IMPROVE] Auto-ingested %d chunks from %s into knowledge base", n, source)
    except Exception as e:
        logger.warning("⚠️  [SELF-IMPROVE] Auto-ingest from %s failed (non-blocking): %s", source, e)


@tool
def fda_adverse_events(device_name: str, limit: int = 5) -> str:
    """Search FDA DEVICE adverse event reports (MAUDE database) for medical hardware.

    Queries the openFDA /device/event endpoint. Use this for HARDWARE issues:
    cardiac monitors, pulse oximeters, blood pressure cuffs, wearable sensors, etc.

    Results are auto-stored in the knowledge base for future queries.

    Args:
        device_name: Device type to search for (e.g. "cardiac monitor", "pulse oximeter").
        limit: Number of results to return (default 5).
    """
    logger.info("🏛️  [FDA-DEVICE] Querying adverse events for: '%s'", device_name)
    url = f"{OPENFDA_BASE_URL}/device/event.json"
    params = {
        "search": f'device.generic_name:"{device_name}"',
        "limit": limit,
    }

    try:
        resp = httpx.get(url, params=params, timeout=15)
        if resp.status_code != 200:
            return f"No adverse event data found for '{device_name}'."

        data = resp.json()
        results = data.get("results", [])
        if not results:
            return f"No adverse events reported for '{device_name}'."

        parts = []
        for r in results:
            event_type = r.get("event_type", "unknown")
            date = r.get("date_received", "unknown")
            description = ""
            for text_entry in r.get("mdr_text", []):
                description = text_entry.get("text", "")[:300]
                break
            device_info = r.get("device", [{}])[0] if r.get("device") else {}
            brand = device_info.get("brand_name", "unknown")
            parts.append(f"[{date}] {brand} — {event_type}\n{description}")

        output = f"FDA Device Adverse Events for '{device_name}':\n\n" + "\n\n---\n\n".join(parts)
        logger.info("🏛️  [FDA-DEVICE] Found %d adverse events for '%s'", len(results), device_name)

        _auto_ingest(output, "device_safety", "fda_device_adverse_events")
        return output

    except Exception as e:
        logger.warning("🏛️  [FDA-DEVICE] Query failed: %s", e)
        return f"Failed to query FDA device adverse events: {e}"


@tool
def fda_device_recall(device_name: str, limit: int = 5) -> str:
    """Search FDA DEVICE recall database for medical hardware recalls.

    Queries the openFDA /device/recall endpoint. Use this to check if a device
    type has active recalls (e.g. faulty sensors, firmware bugs, safety defects).

    Results are auto-stored in the knowledge base for future queries.

    Args:
        device_name: Device type to search (e.g. "blood pressure monitor").
        limit: Number of results to return.
    """
    logger.info("🏛️  [FDA-DEVICE] Querying recalls for: '%s'", device_name)
    url = f"{OPENFDA_BASE_URL}/device/recall.json"
    params = {
        "search": f'product_description:"{device_name}"',
        "limit": limit,
    }

    try:
        resp = httpx.get(url, params=params, timeout=15)
        if resp.status_code != 200:
            return f"No recall data found for '{device_name}'."

        data = resp.json()
        results = data.get("results", [])
        if not results:
            return f"No active recalls for '{device_name}'."

        parts = []
        for r in results:
            firm = r.get("recalling_firm", "unknown")
            reason = r.get("reason_for_recall", "unknown")[:200]
            product = r.get("product_description", "")[:150]
            parts.append(f"Firm: {firm}\nProduct: {product}\nReason: {reason}")

        output = f"FDA Device Recalls for '{device_name}':\n\n" + "\n\n---\n\n".join(parts)
        logger.info("🏛️  [FDA-DEVICE] Found %d recalls for '%s'", len(results), device_name)

        _auto_ingest(output, "device_safety", "fda_device_recalls")
        return output

    except Exception as e:
        logger.warning("🏛️  [FDA-DEVICE] Recall query failed: %s", e)
        return f"Failed to query FDA device recalls: {e}"


@tool
def fda_drug_interactions(drug_name: str, limit: int = 5) -> str:
    """Search FDA DRUG adverse event database for medication side effects and interactions.

    Queries the openFDA /drug/event endpoint. This is a DIFFERENT database from device tools.
    Use this for MEDICATION issues: drug side effects, contraindications, interaction reports.

    Results are auto-stored in the knowledge base for future queries.

    Args:
        drug_name: Drug name (generic or brand, e.g. "metoprolol", "aspirin").
        limit: Number of results.
    """
    logger.info("💊 [FDA-DRUG] Querying drug events for: '%s'", drug_name)
    url = f"{OPENFDA_BASE_URL}/drug/event.json"
    params = {
        "search": f'patient.drug.medicinalproduct:"{drug_name}"',
        "limit": limit,
    }

    try:
        resp = httpx.get(url, params=params, timeout=15)
        if resp.status_code != 200:
            return f"No drug event data found for '{drug_name}'."

        data = resp.json()
        results = data.get("results", [])
        if not results:
            return f"No adverse events found for '{drug_name}'."

        parts = []
        for r in results:
            reactions = [rx.get("reactionmeddrapt", "") for rx in r.get("patient", {}).get("reaction", [])]
            serious = r.get("serious", 0)
            parts.append(f"Reactions: {', '.join(reactions[:5])}\nSerious: {'Yes' if serious else 'No'}")

        output = f"FDA Drug Adverse Events for '{drug_name}':\n\n" + "\n\n---\n\n".join(parts)
        logger.info("💊 [FDA-DRUG] Found %d drug events for '%s'", len(results), drug_name)

        _auto_ingest(output, "drug_safety", "fda_drug_events")
        return output

    except Exception as e:
        logger.warning("💊 [FDA-DRUG] Drug query failed: %s", e)
        return f"Failed to query FDA drug events: {e}"
