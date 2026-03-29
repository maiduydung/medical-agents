"""Azure Service Bus integration — producer and consumer for vitals events."""

import json
import logging
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from azure.servicebus.aio import ServiceBusClient as AsyncServiceBusClient
from config.settings import SERVICEBUS_CONNECTION_STRING, SERVICEBUS_QUEUE_NAME

logger = logging.getLogger(__name__)


def send_vitals(vitals: dict):
    """Send a vitals reading to the Service Bus queue (synchronous — used by simulator)."""
    with ServiceBusClient.from_connection_string(SERVICEBUS_CONNECTION_STRING) as client:
        with client.get_queue_sender(SERVICEBUS_QUEUE_NAME) as sender:
            message = ServiceBusMessage(json.dumps(vitals))
            sender.send_messages(message)
            logger.info("Sent vitals to queue: HR=%s, SpO2=%s", vitals.get("heart_rate"), vitals.get("spo2"))


def send_vitals_batch(vitals_list: list[dict]):
    """Send a batch of vitals readings to the queue."""
    with ServiceBusClient.from_connection_string(SERVICEBUS_CONNECTION_STRING) as client:
        with client.get_queue_sender(SERVICEBUS_QUEUE_NAME) as sender:
            messages = [ServiceBusMessage(json.dumps(v)) for v in vitals_list]
            sender.send_messages(messages)
            logger.info("Sent %d vitals to queue", len(vitals_list))


async def receive_vitals(max_messages: int = 1, max_wait_time: int = 5) -> list[dict]:
    """Receive vitals readings from the queue (async — used by consumer)."""
    async with AsyncServiceBusClient.from_connection_string(SERVICEBUS_CONNECTION_STRING) as client:
        receiver = client.get_queue_receiver(SERVICEBUS_QUEUE_NAME, max_wait_time=max_wait_time)
        async with receiver:
            messages = await receiver.receive_messages(max_message_count=max_messages, max_wait_time=max_wait_time)
            results = []
            for msg in messages:
                body = json.loads(str(msg))
                results.append(body)
                await receiver.complete_message(msg)
            return results
