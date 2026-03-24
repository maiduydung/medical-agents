"""openFDA API tools — free, no key required."""

import logging
import httpx
from langchain_core.tools import tool
from config.settings import OPENFDA_BASE_URL

logger = logging.getLogger(__name__)


@tool
def fda_adverse_events(device_name: str, limit: int = 5) -> str:
    """Search FDA adverse event reports (MAUDE) for a medical device.

    Use this to check if there are known safety issues with a device type
    (e.g. cardiac monitor, pulse oximeter, blood pressure cuff).

    Args:
        device_name: Device type to search for (e.g. "cardiac monitor", "pulse oximeter").
        limit: Number of results to return (default 5).
    """
    logger.info("Querying openFDA adverse events for: %s", device_name)
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

        logger.info("Found %d adverse events for %s", len(results), device_name)
        return f"FDA Adverse Events for '{device_name}':\n\n" + "\n\n---\n\n".join(parts)

    except Exception as e:
        logger.warning("openFDA query failed: %s", e)
        return f"Failed to query FDA adverse events: {e}"


@tool
def fda_device_recall(device_name: str, limit: int = 5) -> str:
    """Search FDA device recalls for a medical device type.

    Use this to check if there are active recalls for a device category.

    Args:
        device_name: Device type to search (e.g. "blood pressure monitor").
        limit: Number of results to return.
    """
    logger.info("Querying openFDA recalls for: %s", device_name)
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
            status = r.get("res_event_number", "N/A")
            product = r.get("product_description", "")[:150]
            parts.append(f"Firm: {firm}\nProduct: {product}\nReason: {reason}")

        logger.info("Found %d recalls for %s", len(results), device_name)
        return f"FDA Device Recalls for '{device_name}':\n\n" + "\n\n---\n\n".join(parts)

    except Exception as e:
        logger.warning("openFDA recall query failed: %s", e)
        return f"Failed to query FDA recalls: {e}"


@tool
def fda_drug_interactions(drug_name: str, limit: int = 5) -> str:
    """Search FDA drug adverse events to check for known interactions or side effects.

    Args:
        drug_name: Drug name (generic or brand, e.g. "metoprolol", "aspirin").
        limit: Number of results.
    """
    logger.info("Querying openFDA drug events for: %s", drug_name)
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

        logger.info("Found %d drug events for %s", len(results), drug_name)
        return f"FDA Drug Adverse Events for '{drug_name}':\n\n" + "\n\n---\n\n".join(parts)

    except Exception as e:
        logger.warning("openFDA drug query failed: %s", e)
        return f"Failed to query FDA drug events: {e}"
