"""Web entry point for chat jobs and the built frontend."""
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from kombu.exceptions import OperationalError
from pydantic import BaseModel, Field
from redis.exceptions import RedisError

from .tasks import celery_app, chat_analysis_task

app = FastAPI(title="Financial Harness")
QUEUE_ERRORS = (OperationalError, RedisError, OSError)


class Question(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    symbol: Literal["IBM", "AAPL", "MSFT"] = "IBM"


def job_response(job_id, status, progress=0, result=None, error=None):
    return {"job_id": job_id, "status": status, "progress": progress, "result": result, "error": error}


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/jobs", status_code=202)
def submit(question: Question):
    message = question.question.strip()
    if not message:
        raise HTTPException(422, "Enter a stock question.")
    job_id = str(uuid4())
    try:
        celery_app.backend.store_result(job_id, None, "QUEUED")
        chat_analysis_task.apply_async(args=(message, question.symbol), task_id=job_id)
    except QUEUE_ERRORS as exc:
        raise HTTPException(503, "The analysis queue is unavailable.") from exc
    return job_response(job_id, "queued")


@app.get("/api/jobs/{job_id}")
def status(job_id: UUID):
    key = str(job_id)
    try:
        metadata = celery_app.backend.get_task_meta(key)
    except QUEUE_ERRORS as exc:
        raise HTTPException(503, "Job status is unavailable.") from exc
    state = metadata["status"]
    if state == "PENDING":
        raise HTTPException(404, "Job not found or expired.")
    if state == "SUCCESS":
        return job_response(key, "completed", 100, result=metadata["result"])
    if state in {"FAILURE", "REVOKED"}:
        return job_response(key, "failed", error="Analysis failed. Please try again.")
    if state == "PROGRESS":
        return job_response(key, "running", metadata["result"]["progress"])
    if state == "STARTED":
        return job_response(key, "running")
    return job_response(key, "queued")


static = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if static.is_dir():
    app.mount("/", StaticFiles(directory=static, html=True), name="frontend")
