"""Tests for the deterministic triage engine — the core routing logic."""

import pytest
from app.tools.triage import _classify_vital, triage_vitals, VITAL_RULES, SEVERITY_ORDER


class TestClassifyVital:
    """Unit tests for _classify_vital()."""

    def test_normal_heart_rate(self):
        severity, desc = _classify_vital("heart_rate", 75)
        assert severity == "NORMAL"
        assert "normal" in desc

    def test_warning_heart_rate_high(self):
        severity, _ = _classify_vital("heart_rate", 115)
        assert severity == "WARNING"

    def test_warning_heart_rate_low(self):
        severity, _ = _classify_vital("heart_rate", 55)
        assert severity == "WARNING"

    def test_critical_heart_rate(self):
        severity, _ = _classify_vital("heart_rate", 145)
        assert severity == "CRITICAL"

    def test_emergency_heart_rate(self):
        severity, _ = _classify_vital("heart_rate", 160)
        assert severity == "EMERGENCY"

    def test_normal_spo2(self):
        severity, _ = _classify_vital("spo2", 98)
        assert severity == "NORMAL"

    def test_warning_spo2(self):
        severity, _ = _classify_vital("spo2", 92)
        assert severity == "WARNING"

    def test_critical_spo2(self):
        severity, _ = _classify_vital("spo2", 87)
        assert severity == "CRITICAL"

    def test_emergency_spo2(self):
        severity, _ = _classify_vital("spo2", 80)
        assert severity == "EMERGENCY"

    def test_normal_temperature(self):
        severity, _ = _classify_vital("temperature", 36.5)
        assert severity == "NORMAL"

    def test_fever_warning(self):
        severity, _ = _classify_vital("temperature", 37.8)
        assert severity == "WARNING"

    def test_fever_critical(self):
        severity, _ = _classify_vital("temperature", 39.0)
        assert severity == "CRITICAL"

    def test_fever_emergency(self):
        severity, _ = _classify_vital("temperature", 41.0)
        assert severity == "EMERGENCY"

    def test_unknown_vital_returns_normal(self):
        severity, desc = _classify_vital("unknown_metric", 42)
        assert severity == "NORMAL"
        assert "no rules defined" in desc

    def test_boundary_normal_low(self):
        """Exact lower boundary of normal range should be NORMAL."""
        severity, _ = _classify_vital("heart_rate", 60)
        assert severity == "NORMAL"

    def test_boundary_normal_high(self):
        """Exact upper boundary of normal range should be NORMAL."""
        severity, _ = _classify_vital("heart_rate", 100)
        assert severity == "NORMAL"


class TestTriageVitals:
    """Integration tests for triage_vitals()."""

    def test_all_normal(self):
        vitals = {
            "heart_rate": 75,
            "systolic_bp": 120,
            "diastolic_bp": 80,
            "spo2": 98,
            "temperature": 36.6,
            "respiratory_rate": 16,
        }
        result = triage_vitals(vitals)
        assert result["severity"] == "NORMAL"
        assert result["requires_agent"] is False
        assert result["recommended_agent"] is None
        assert "normal" in result["summary"].lower()

    def test_cardiac_routing_tachycardia(self):
        vitals = {
            "heart_rate": 155,
            "systolic_bp": 120,
            "diastolic_bp": 80,
            "spo2": 98,
            "temperature": 36.6,
            "respiratory_rate": 16,
        }
        result = triage_vitals(vitals)
        assert result["severity"] == "EMERGENCY"
        assert result["requires_agent"] is True
        assert result["recommended_agent"] == "cardiac"

    def test_respiratory_routing_low_spo2(self):
        vitals = {
            "heart_rate": 80,
            "systolic_bp": 120,
            "diastolic_bp": 80,
            "spo2": 83,
            "temperature": 36.6,
            "respiratory_rate": 16,
        }
        result = triage_vitals(vitals)
        assert result["requires_agent"] is True
        assert result["recommended_agent"] == "respiratory"

    def test_respiratory_routing_high_rr(self):
        vitals = {
            "heart_rate": 80,
            "systolic_bp": 120,
            "diastolic_bp": 80,
            "spo2": 98,
            "temperature": 36.6,
            "respiratory_rate": 35,
        }
        result = triage_vitals(vitals)
        assert result["requires_agent"] is True
        assert result["recommended_agent"] == "respiratory"

    def test_general_health_routing_hypertension(self):
        vitals = {
            "heart_rate": 80,
            "systolic_bp": 190,
            "diastolic_bp": 80,
            "spo2": 98,
            "temperature": 36.6,
            "respiratory_rate": 16,
        }
        result = triage_vitals(vitals)
        assert result["requires_agent"] is True
        assert result["recommended_agent"] == "general_health"

    def test_general_health_routing_fever(self):
        vitals = {
            "heart_rate": 80,
            "systolic_bp": 120,
            "diastolic_bp": 80,
            "spo2": 98,
            "temperature": 40.0,
            "respiratory_rate": 16,
        }
        result = triage_vitals(vitals)
        assert result["requires_agent"] is True
        assert result["recommended_agent"] == "general_health"

    def test_skips_non_vital_fields(self):
        vitals = {
            "timestamp": "2024-01-01T00:00:00Z",
            "device_id": "ring-001",
            "patient_id": "patient-demo",
            "heart_rate": 75,
        }
        result = triage_vitals(vitals)
        assert result["severity"] == "NORMAL"
        assert len(result["flags"]) == 1

    def test_skips_non_numeric_values(self):
        vitals = {"heart_rate": 75, "notes": "feeling fine"}
        result = triage_vitals(vitals)
        assert len(result["flags"]) == 1

    def test_max_severity_wins(self):
        """When multiple vitals are abnormal, the worst severity wins."""
        vitals = {
            "heart_rate": 115,       # WARNING
            "spo2": 83,              # EMERGENCY
            "temperature": 36.6,     # NORMAL
        }
        result = triage_vitals(vitals)
        assert result["severity"] == "EMERGENCY"

    def test_flags_contain_all_vitals(self):
        vitals = {
            "heart_rate": 75,
            "spo2": 98,
            "temperature": 36.6,
        }
        result = triage_vitals(vitals)
        vital_names = {f["vital"] for f in result["flags"]}
        assert vital_names == {"heart_rate", "spo2", "temperature"}


class TestTriageConstants:
    """Verify triage rules are internally consistent."""

    def test_severity_order_is_ascending(self):
        assert SEVERITY_ORDER == ["NORMAL", "WARNING", "CRITICAL", "EMERGENCY"]

    @pytest.mark.parametrize("vital_name", VITAL_RULES.keys())
    def test_ranges_are_nested(self, vital_name):
        """Normal range must be inside warning, which is inside critical."""
        rules = VITAL_RULES[vital_name]
        assert rules["critical"][0] <= rules["warning"][0] <= rules["normal"][0]
        assert rules["normal"][1] <= rules["warning"][1] <= rules["critical"][1]

    @pytest.mark.parametrize("vital_name", VITAL_RULES.keys())
    def test_all_rules_have_unit(self, vital_name):
        assert "unit" in VITAL_RULES[vital_name]
