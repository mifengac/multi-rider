from __future__ import annotations

import threading
import time
from uuid import uuid4

from service.face_library_service import get_face_library_status, rebuild_face_library, sync_face_library


FACE_LIBRARY_TASKS: dict[str, dict] = {}
FACE_LIBRARY_TASKS_LOCK = threading.Lock()


def _task_snapshot(task: dict | None) -> dict | None:
    if task is None:
        return None
    return dict(task)


def list_face_library_tasks() -> list[dict]:
    with FACE_LIBRARY_TASKS_LOCK:
        return [_task_snapshot(task) for task in FACE_LIBRARY_TASKS.values()]


def get_face_library_task(task_id: str) -> dict | None:
    with FACE_LIBRARY_TASKS_LOCK:
        return _task_snapshot(FACE_LIBRARY_TASKS.get(task_id))


def get_running_face_library_task() -> dict | None:
    with FACE_LIBRARY_TASKS_LOCK:
        for task in FACE_LIBRARY_TASKS.values():
            if task.get("status") == "running":
                return _task_snapshot(task)
    return None


def _update_task(task_id: str, **values) -> None:
    with FACE_LIBRARY_TASKS_LOCK:
        task = FACE_LIBRARY_TASKS.get(task_id)
        if task is None:
            return
        task.update(values)


def _run_task(task_id: str, action: str) -> None:
    def progress_cb(update: dict) -> None:
        payload = {}
        if "message" in update:
            payload["message"] = update["message"]
        if "stage" in update:
            payload["stage"] = update["stage"]
        if "processed" in update:
            payload["processed"] = update["processed"]
        if "total" in update:
            payload["total"] = update["total"]
        _update_task(task_id, **payload)

    try:
        if action == "sync":
            result = sync_face_library(progress_cb=progress_cb)
        else:
            result = rebuild_face_library(progress_cb=progress_cb)
        _update_task(
            task_id,
            status="done",
            end_ts=int(time.time()),
            result=result,
            library=get_face_library_status(),
            message="completed",
        )
    except Exception as exc:
        _update_task(
            task_id,
            status="error",
            end_ts=int(time.time()),
            error=str(exc),
            message=str(exc),
            library=get_face_library_status(),
        )


def start_face_library_task(action: str) -> tuple[dict, bool]:
    running = get_running_face_library_task()
    if running is not None:
        return running, False

    task = {
        "id": uuid4().hex,
        "action": action,
        "status": "running",
        "message": "queued",
        "stage": "queued",
        "processed": 0,
        "total": 0,
        "start_ts": int(time.time()),
        "end_ts": None,
        "error": "",
        "result": None,
        "library": get_face_library_status(),
    }
    with FACE_LIBRARY_TASKS_LOCK:
        FACE_LIBRARY_TASKS[task["id"]] = task

    threading.Thread(target=_run_task, args=(task["id"], action), daemon=True).start()
    return _task_snapshot(task), True

