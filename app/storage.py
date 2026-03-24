"""Storage layer — writes processed vitals + agent decisions to Parquet for DuckDB analytics."""

import logging
import os
import json
from datetime import datetime
import pyarrow as pa
import pyarrow.parquet as pq

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
VITALS_FILE = os.path.join(DATA_DIR, "vitals_history.parquet")

SCHEMA = pa.schema([
    ("timestamp", pa.string()),
    ("device_id", pa.string()),
    ("patient_id", pa.string()),
    ("heart_rate", pa.float64()),
    ("systolic_bp", pa.float64()),
    ("diastolic_bp", pa.float64()),
    ("spo2", pa.float64()),
    ("temperature", pa.float64()),
    ("respiratory_rate", pa.float64()),
    ("triage_severity", pa.string()),
    ("triage_summary", pa.string()),
    ("agent_used", pa.string()),
    ("assessment", pa.string()),
])


def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def store_result(result: dict):
    """Append a processed vitals result to the Parquet file."""
    _ensure_data_dir()

    vitals = result.get("vitals", {})
    triage = result.get("triage", {})

    row = {
        "timestamp": result.get("timestamp", ""),
        "device_id": vitals.get("device_id", ""),
        "patient_id": vitals.get("patient_id", ""),
        "heart_rate": float(vitals.get("heart_rate", 0)),
        "systolic_bp": float(vitals.get("systolic_bp", 0)),
        "diastolic_bp": float(vitals.get("diastolic_bp", 0)),
        "spo2": float(vitals.get("spo2", 0)),
        "temperature": float(vitals.get("temperature", 0)),
        "respiratory_rate": float(vitals.get("respiratory_rate", 0)),
        "triage_severity": triage.get("severity", ""),
        "triage_summary": triage.get("summary", ""),
        "agent_used": result.get("agent_used", "") or "",
        "assessment": result.get("assessment", "") or "",
    }

    # Build a single-row table
    arrays = [pa.array([row[field.name]], type=field.type) for field in SCHEMA]
    new_table = pa.table(arrays, schema=SCHEMA)

    if os.path.exists(VITALS_FILE):
        existing = pq.read_table(VITALS_FILE, schema=SCHEMA)
        combined = pa.concat_tables([existing, new_table])
    else:
        combined = new_table

    pq.write_table(combined, VITALS_FILE)
    logger.info("Stored result to parquet (%d total rows)", combined.num_rows)


def get_history_path() -> str:
    """Return the path to the vitals parquet file."""
    return VITALS_FILE
