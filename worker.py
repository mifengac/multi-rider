"""Standalone task worker process.

Polls the ``task_queue`` table and executes heavy workloads (training,
face-library rebuild/sync, auto-annotate) **outside** the Flask web process.

Start manually::

    python worker.py                 # consume all task types
    python worker.py --type train    # consume only training tasks

The worker runs **one task at a time** (CPU-bound workloads). For
concurrency, start multiple worker instances with different ``--type``
filters.
"""

from __future__ import annotations

import argparse
import signal
import sys
import time

# Ensure project root is on sys.path so shared/modules imports work.
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.config.config import logger
from shared.db.sqlite import init_db
from shared.task_queue import (
    claim_task,
    cleanup_old_tasks,
    complete_task,
    fail_task,
    reset_stale_running,
)

# ---------------------------------------------------------------------------
# Graceful shutdown
# ---------------------------------------------------------------------------

_shutdown = False


def _sig_handler(_signum, _frame):
    global _shutdown
    _shutdown = True
    logger.info("worker: shutdown signal received, finishing current task …")


signal.signal(signal.SIGINT, _sig_handler)
signal.signal(signal.SIGTERM, _sig_handler)


# ---------------------------------------------------------------------------
# Task dispatchers — import lazily to avoid loading heavy libs at startup
# ---------------------------------------------------------------------------


def _handle_train(payload: dict) -> dict:
    """Run a YOLO training task."""
    from modules.training.services.train_task_service import (
        _prepare_train_job,
        _run_train_job,
    )

    job = _prepare_train_job(payload)
    _run_train_job(job)
    return {"job_id": job.get("id"), "status": job.get("status")}


def _handle_auto_annotate(payload: dict) -> dict:
    """Run an auto-annotate task."""
    from modules.training.services.auto_annotate_task_service import (
        _run_auto_annotate_job,
    )

    job = payload.get("job", {})
    asset_ids = payload.get("asset_ids", [])
    _run_auto_annotate_job(job, asset_ids)
    return {"job_id": job.get("id"), "status": job.get("status")}


def _handle_face_library(payload: dict) -> dict:
    """Run a face library rebuild or sync."""
    action = payload.get("action", "rebuild")
    if action == "sync":
        from modules.face.services.library_service import sync_face_library
        result = sync_face_library()
    else:
        from modules.face.services.library_service import rebuild_face_library
        result = rebuild_face_library()
    return result


HANDLERS: dict[str, callable] = {
    "train": _handle_train,
    "auto_annotate": _handle_auto_annotate,
    "face_library": _handle_face_library,
}


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def run_worker(task_type: str | None = None, poll_interval: float = 2.0) -> None:
    """Poll the task queue and execute tasks until shutdown."""
    init_db()
    reset_stale_running()
    logger.info(
        "worker started  type_filter=%s  poll_interval=%.1fs",
        task_type or "(all)",
        poll_interval,
    )

    last_cleanup = time.time()

    while not _shutdown:
        task = claim_task(task_type)
        if task is None:
            # No work — idle sleep then housekeeping.
            time.sleep(poll_interval)
            now = time.time()
            if now - last_cleanup > 3600:
                reset_stale_running()
                cleanup_old_tasks(30)
                last_cleanup = now
            continue

        tid = task["id"]
        ttype = task["task_type"]
        logger.info("worker: claimed task %s  type=%s", tid, ttype)

        handler = HANDLERS.get(ttype)
        if handler is None:
            fail_task(tid, error=f"unknown task type: {ttype}")
            logger.error("worker: no handler for task type %r", ttype)
            continue

        try:
            result = handler(task["payload"])
            complete_task(tid, result=result)
        except Exception as exc:
            logger.exception("worker: task %s failed", tid)
            fail_task(tid, error=str(exc)[:1000])

    logger.info("worker: exited cleanly")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Multi-rider task worker")
    parser.add_argument(
        "--type",
        dest="task_type",
        default=None,
        choices=list(HANDLERS.keys()),
        help="Only consume tasks of this type (default: all)",
    )
    parser.add_argument(
        "--interval",
        dest="poll_interval",
        type=float,
        default=2.0,
        help="Seconds between queue polls when idle (default: 2)",
    )
    args = parser.parse_args()
    run_worker(task_type=args.task_type, poll_interval=args.poll_interval)


if __name__ == "__main__":
    main()
