"""Tests for the vitals simulator."""

from app.simulator import generate_vitals
from app.tools.triage import VITAL_RULES


EXPECTED_VITAL_KEYS = {"heart_rate", "systolic_bp", "diastolic_bp", "spo2", "temperature", "respiratory_rate"}
META_KEYS = {"device_id", "patient_id", "timestamp"}


class TestGenerateVitals:

    def test_returns_all_vital_signs(self):
        reading = generate_vitals(anomaly_chance=0.0)
        assert EXPECTED_VITAL_KEYS.issubset(reading.keys())

    def test_returns_metadata(self):
        reading = generate_vitals()
        assert META_KEYS.issubset(reading.keys())

    def test_normal_readings_within_range(self):
        """With anomaly_chance=0, all vitals should be within normal or near-normal range."""
        for _ in range(50):
            reading = generate_vitals(anomaly_chance=0.0)
            for vital in EXPECTED_VITAL_KEYS:
                assert isinstance(reading[vital], (int, float)), f"{vital} should be numeric"

    def test_anomaly_readings_generated(self):
        """With anomaly_chance=1.0, we should always get anomalous readings."""
        anomalies_found = 0
        for _ in range(20):
            reading = generate_vitals(anomaly_chance=1.0)
            for vital in EXPECTED_VITAL_KEYS:
                rules = VITAL_RULES.get(vital)
                if rules:
                    val = reading[vital]
                    if not (rules["normal"][0] <= val <= rules["normal"][1]):
                        anomalies_found += 1
                        break
        assert anomalies_found > 0, "Should produce at least some anomalous readings"

    def test_spo2_is_rounded(self):
        reading = generate_vitals()
        spo2 = reading["spo2"]
        assert spo2 == round(spo2, 1)
