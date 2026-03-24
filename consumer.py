"""Vitals consumer — dequeues from Azure Service Bus and runs through the agent pipeline.

Usage:
    python consumer.py              # Process continuously
    python consumer.py --once       # Process one batch and exit
"""

import argparse
import asyncio
import json
import logging
from app.event_bus import receive_vitals
from app.supervisor import process_vitals
from app.storage import store_result

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)


async def consume_once(max_messages: int = 5):
    """Receive and process one batch of messages."""
    logger.info("Waiting for messages...")
    vitals_list = await receive_vitals(max_messages=max_messages, max_wait_time=10)

    if not vitals_list:
        logger.info("No messages in queue")
        return 0

    logger.info("Received %d messages from queue", len(vitals_list))

    for i, vitals in enumerate(vitals_list):
        logger.info("[%d/%d] Processing: HR=%s SpO2=%s",
                    i + 1, len(vitals_list), vitals.get("heart_rate"), vitals.get("spo2"))
        result = await process_vitals(vitals)
        store_result(result)

        severity = result["triage"]["severity"]
        agent = result.get("agent_used", "none")
        logger.info("[%d/%d] Result: %s (agent: %s)", i + 1, len(vitals_list), severity, agent)

        if result.get("assessment"):
            logger.info("Assessment: %s", result["assessment"][:200])

    return len(vitals_list)


async def consume_loop():
    """Continuously consume and process messages."""
    logger.info("Starting continuous consumer...")
    total = 0
    while True:
        try:
            count = await consume_once(max_messages=5)
            total += count
            if count == 0:
                await asyncio.sleep(2)
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error("Consumer error: %s", e)
            await asyncio.sleep(5)

    logger.info("Consumer stopped — processed %d total messages", total)


def main():
    parser = argparse.ArgumentParser(description="Consume vitals from Service Bus and run agent pipeline")
    parser.add_argument("--once", action="store_true", help="Process one batch and exit")
    args = parser.parse_args()

    if args.once:
        asyncio.run(consume_once())
    else:
        asyncio.run(consume_loop())


if __name__ == "__main__":
    main()
