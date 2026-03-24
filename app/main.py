"""FastAPI server — exposes endpoints for the vitals processing pipeline."""

import asyncio
import json
import logging
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.supervisor import process_vitals
from app.storage import store_result

app = FastAPI(title="MedTech Agent Pipeline", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")


class VitalsRequest(BaseModel):
    heart_rate: float | None = None
    systolic_bp: float | None = None
    diastolic_bp: float | None = None
    spo2: float | None = None
    temperature: float | None = None
    respiratory_rate: float | None = None
    device_id: str = "ring-001"
    patient_id: str = "patient-demo"


class _LogCapture(logging.Handler):
    """Captures log records into an asyncio queue for SSE streaming."""
    def __init__(self, queue: asyncio.Queue):
        super().__init__()
        self.queue = queue

    def emit(self, record: logging.LogRecord):
        try:
            self.queue.put_nowait(record.getMessage())
        except asyncio.QueueFull:
            pass


@app.post("/process")
async def process(request: VitalsRequest):
    """Process a single vitals reading through the full pipeline (triage → agent → store)."""
    vitals = request.model_dump(exclude_none=True)
    result = await process_vitals(vitals)
    store_result(result)
    return result


@app.post("/process/stream")
async def process_stream(request: VitalsRequest):
    """SSE endpoint — streams agent logs while processing, then sends the final result."""
    log_queue: asyncio.Queue = asyncio.Queue(maxsize=200)
    handler = _LogCapture(log_queue)
    handler.setLevel(logging.INFO)

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)

    vitals = request.model_dump(exclude_none=True)
    task = asyncio.create_task(process_vitals(vitals))

    async def event_generator():
        try:
            while not task.done():
                try:
                    msg = await asyncio.wait_for(log_queue.get(), timeout=0.3)
                    yield f"data: {json.dumps({'type': 'log', 'message': msg})}\n\n"
                except asyncio.TimeoutError:
                    continue

            # Drain remaining logs
            while not log_queue.empty():
                msg = log_queue.get_nowait()
                yield f"data: {json.dumps({'type': 'log', 'message': msg})}\n\n"

            result = await task
            store_result(result)
            yield f"data: {json.dumps({'type': 'result', 'data': result})}\n\n"
        finally:
            root_logger.removeHandler(handler)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/health")
async def health():
    return {"status": "ok"}
