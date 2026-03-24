"""Vitals producer — simulates a smart ring sending readings to Azure Service Bus.

Usage:
    python producer.py              # Send 10 readings, 1 per second
    python producer.py --count 50   # Send 50 readings
    python producer.py --interval 2 # 2 seconds between readings
"""

import argparse
import time
import logging
from app.simulator import generate_vitals
from app.event_bus import send_vitals

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Simulate a smart ring sending vitals to Service Bus")
    parser.add_argument("--count", type=int, default=10, help="Number of readings to send")
    parser.add_argument("--interval", type=float, default=1.0, help="Seconds between readings")
    parser.add_argument("--anomaly-chance", type=float, default=0.3, help="Probability of anomaly (0-1)")
    args = parser.parse_args()

    logger.info("Starting vitals producer — %d readings, %.1fs interval, %.0f%% anomaly chance",
                args.count, args.interval, args.anomaly_chance * 100)

    for i in range(args.count):
        vitals = generate_vitals(anomaly_chance=args.anomaly_chance)
        send_vitals(vitals)
        logger.info("[%d/%d] Sent: HR=%s BP=%s/%s SpO2=%s Temp=%s",
                    i + 1, args.count,
                    vitals["heart_rate"], vitals["systolic_bp"], vitals["diastolic_bp"],
                    vitals["spo2"], vitals["temperature"])
        if i < args.count - 1:
            time.sleep(args.interval)

    logger.info("Producer finished — sent %d readings", args.count)


if __name__ == "__main__":
    main()
