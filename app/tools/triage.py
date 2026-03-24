"""Deterministic triage engine — rule-based vital sign checks. No LLM needed."""

import logging

logger = logging.getLogger(__name__)


# Clinical thresholds (simplified for demo — real systems use age/context-adjusted ranges)
VITAL_RULES = {
    "heart_rate": {
        "unit": "bpm",
        "normal": (60, 100),
        "warning": (50, 120),
        "critical": (40, 150),
        # Outside critical → EMERGENCY
    },
    "systolic_bp": {
        "unit": "mmHg",
        "normal": (90, 140),
        "warning": (80, 160),
        "critical": (70, 180),
    },
    "diastolic_bp": {
        "unit": "mmHg",
        "normal": (60, 90),
        "warning": (50, 100),
        "critical": (40, 110),
    },
    "spo2": {
        "unit": "%",
        "normal": (95, 100),
        "warning": (90, 101),
        "critical": (85, 101),
    },
    "temperature": {
        "unit": "°C",
        "normal": (36.1, 37.2),
        "warning": (35.5, 38.0),
        "critical": (35.0, 39.5),
    },
    "respiratory_rate": {
        "unit": "breaths/min",
        "normal": (12, 20),
        "warning": (10, 25),
        "critical": (8, 30),
    },
}

SEVERITY_ORDER = ["NORMAL", "WARNING", "CRITICAL", "EMERGENCY"]


def _classify_vital(name: str, value: float) -> tuple[str, str]:
    """Classify a single vital sign. Returns (severity, description)."""
    rules = VITAL_RULES.get(name)
    if not rules:
        return "NORMAL", f"{name}={value} (no rules defined)"

    unit = rules["unit"]

    if rules["normal"][0] <= value <= rules["normal"][1]:
        return "NORMAL", f"{name}: {value}{unit} (normal)"
    elif rules["warning"][0] <= value <= rules["warning"][1]:
        return "WARNING", f"{name}: {value}{unit} (outside normal range {rules['normal'][0]}-{rules['normal'][1]}{unit})"
    elif rules["critical"][0] <= value <= rules["critical"][1]:
        return "CRITICAL", f"{name}: {value}{unit} (critical — needs attention)"
    else:
        return "EMERGENCY", f"{name}: {value}{unit} (EMERGENCY — outside safe range)"


def triage_vitals(vitals: dict) -> dict:
    """Run deterministic triage on a vitals reading.

    Args:
        vitals: dict with keys like heart_rate, systolic_bp, spo2, etc.

    Returns:
        {
            "severity": "NORMAL" | "WARNING" | "CRITICAL" | "EMERGENCY",
            "flags": [{"vital": str, "severity": str, "description": str}, ...],
            "summary": str,
            "requires_agent": bool,
            "recommended_agent": str | None,
        }
    """
    flags = []
    max_severity = "NORMAL"

    for vital_name, value in vitals.items():
        if vital_name in ("timestamp", "device_id", "patient_id"):
            continue
        if not isinstance(value, (int, float)):
            continue

        severity, description = _classify_vital(vital_name, value)
        flags.append({"vital": vital_name, "severity": severity, "description": description})

        if SEVERITY_ORDER.index(severity) > SEVERITY_ORDER.index(max_severity):
            max_severity = severity

    # Determine which agent should handle this (if any)
    recommended_agent = None
    requires_agent = max_severity in ("WARNING", "CRITICAL", "EMERGENCY")

    if requires_agent:
        # Route based on which vitals are flagged
        flagged_vitals = {f["vital"] for f in flags if f["severity"] != "NORMAL"}
        cardiac_vitals = {"heart_rate"}
        respiratory_vitals = {"spo2", "respiratory_rate"}

        if flagged_vitals & cardiac_vitals:
            recommended_agent = "cardiac"
        elif flagged_vitals & respiratory_vitals:
            recommended_agent = "respiratory"
        else:
            recommended_agent = "general_health"

    abnormal_flags = [f for f in flags if f["severity"] != "NORMAL"]
    if abnormal_flags:
        summary = f"[{max_severity}] " + "; ".join(f["description"] for f in abnormal_flags)
    else:
        summary = "[NORMAL] All vitals within normal range."

    logger.info("Triage result: %s (flags: %d abnormal)", max_severity, len(abnormal_flags))

    return {
        "severity": max_severity,
        "flags": flags,
        "summary": summary,
        "requires_agent": requires_agent,
        "recommended_agent": recommended_agent,
    }
