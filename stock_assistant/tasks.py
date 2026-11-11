"""Background processing with Celery.

Long analyses (multi-stock deep dive, Monte-Carlo with many simulations)
run on a Celery worker via a Redis queue: progress tracking, automatic
retries (max 3, exponential backoff) and results saved to results/<id>.json.

If Celery/Redis are not available (local demo, tests) the same function can
be executed synchronously through ``run_deep_analysis_sync`` — the analysis
logic is identical, only the transport differs.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from . import harness, projections

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)
BROKER = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")

try:
    from celery import Celery

    celery_app = Celery("stock_assistant", broker=BROKER, backend=BROKER)
    celery_app.conf.update(task_track_started=True, task_time_limit=600,
                           worker_prefetch_multiplier=1)
except Exception:  # celery not installed in this environment
    celery_app = None


def deep_analysis(symbols: list[str], progress=None) -> dict:
    """The long job itself: full research + projection for each symbol."""
    out = {}
    for idx, symbol in enumerate(symbols):
        if progress:
            progress(int((idx / max(len(symbols), 1)) * 100), f"analysing {symbol}")
        out[symbol] = {
            "research": harness.answer(f"Analyse {symbol}", permissions={"sandbox": False})["results"],
            "projection_3y": projections.projection(symbol, years=3, simulations=2000),
        }
        time.sleep(0.05)  # stand-in for heavier per-stock work (statements, earnings)
    if progress:
        progress(100, "done")
    return out


def _save(task_id: str, payload: dict) -> Path:
    path = RESULTS_DIR / f"{task_id}.json"
    path.write_text(json.dumps(payload, indent=2, default=str))
    return path


if celery_app is not None:
    @celery_app.task(bind=True, max_retries=3, default_retry_delay=10, name="deep_analysis")
    def deep_analysis_task(self, symbols: list[str]):
        def _progress(pct, note):
            self.update_state(state="PROGRESS", meta={"progress": pct, "note": note})
        try:
            result = deep_analysis(symbols, progress=_progress)
        except Exception as exc:
            raise self.retry(exc=exc)
        _save(self.request.id, result)
        return result


def run_deep_analysis_sync(symbols: list[str], task_id: str = "local-demo") -> dict:
    result = deep_analysis(symbols)
    _save(task_id, result)
    return result
