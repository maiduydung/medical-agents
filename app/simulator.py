"""Vitals simulator — generates realistic medical telemetry from a fake smart ring.

Produces a mix of normal readings with occasional anomalies to trigger agent analysis.
"""

import random
from datetime import datetime, timezone


def generate_vitals(anomaly_chance: float = 0.3) -> dict:
    """Generate a single vitals reading.

    Args:
        anomaly_chance: Probability of generating an anomalous reading (0.0 to 1.0).
    """
    reading = {
        "device_id": "ring-001",
        "patient_id": "patient-demo",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if random.random() < anomaly_chance:
        # Generate an anomalous reading — pick a random scenario
        scenario = random.choice([
            "tachycardia",
            "bradycardia",
            "hypertension",
            "hypotension",
            "low_spo2",
            "fever",
            "multi_warning",
        ])

        if scenario == "tachycardia":
            reading["heart_rate"] = random.randint(130, 180)
            reading["systolic_bp"] = random.randint(100, 145)
            reading["diastolic_bp"] = random.randint(65, 92)
            reading["spo2"] = random.uniform(94, 99)
            reading["temperature"] = round(random.uniform(36.2, 37.0), 1)
            reading["respiratory_rate"] = random.randint(18, 26)

        elif scenario == "bradycardia":
            reading["heart_rate"] = random.randint(35, 50)
            reading["systolic_bp"] = random.randint(85, 115)
            reading["diastolic_bp"] = random.randint(55, 75)
            reading["spo2"] = random.uniform(93, 98)
            reading["temperature"] = round(random.uniform(36.0, 36.8), 1)
            reading["respiratory_rate"] = random.randint(10, 16)

        elif scenario == "hypertension":
            reading["heart_rate"] = random.randint(75, 110)
            reading["systolic_bp"] = random.randint(160, 200)
            reading["diastolic_bp"] = random.randint(100, 120)
            reading["spo2"] = random.uniform(95, 99)
            reading["temperature"] = round(random.uniform(36.3, 37.1), 1)
            reading["respiratory_rate"] = random.randint(14, 22)

        elif scenario == "hypotension":
            reading["heart_rate"] = random.randint(90, 120)
            reading["systolic_bp"] = random.randint(60, 80)
            reading["diastolic_bp"] = random.randint(35, 50)
            reading["spo2"] = random.uniform(93, 97)
            reading["temperature"] = round(random.uniform(36.0, 36.6), 1)
            reading["respiratory_rate"] = random.randint(16, 24)

        elif scenario == "low_spo2":
            reading["heart_rate"] = random.randint(85, 115)
            reading["systolic_bp"] = random.randint(95, 140)
            reading["diastolic_bp"] = random.randint(60, 90)
            reading["spo2"] = random.uniform(82, 92)
            reading["temperature"] = round(random.uniform(36.5, 37.5), 1)
            reading["respiratory_rate"] = random.randint(22, 32)

        elif scenario == "fever":
            reading["heart_rate"] = random.randint(90, 120)
            reading["systolic_bp"] = random.randint(95, 135)
            reading["diastolic_bp"] = random.randint(60, 85)
            reading["spo2"] = random.uniform(94, 98)
            reading["temperature"] = round(random.uniform(38.5, 40.5), 1)
            reading["respiratory_rate"] = random.randint(18, 28)

        elif scenario == "multi_warning":
            reading["heart_rate"] = random.randint(110, 140)
            reading["systolic_bp"] = random.randint(150, 175)
            reading["diastolic_bp"] = random.randint(95, 108)
            reading["spo2"] = random.uniform(90, 94)
            reading["temperature"] = round(random.uniform(37.5, 38.5), 1)
            reading["respiratory_rate"] = random.randint(22, 28)
    else:
        # Normal reading
        reading["heart_rate"] = random.randint(62, 95)
        reading["systolic_bp"] = random.randint(95, 135)
        reading["diastolic_bp"] = random.randint(62, 88)
        reading["spo2"] = round(random.uniform(96, 99.5), 1)
        reading["temperature"] = round(random.uniform(36.2, 37.1), 1)
        reading["respiratory_rate"] = random.randint(13, 19)

    # Round spo2
    reading["spo2"] = round(reading["spo2"], 1)

    return reading
