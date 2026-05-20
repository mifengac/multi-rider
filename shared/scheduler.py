from __future__ import annotations

import os
import sys
import threading
import time

from shared.config.config import logger


_scheduler_thread: threading.Thread | None = None
_stop_event: threading.Event | None = None
_state_lock = threading.Lock()
_last_daily_key: tuple[int, int] | None = None
_last_monthly_key: tuple[int, int] | None = None
_last_alert_slot: int | None = None
_last_incremental_score_slot: int | None = None


def _int_env(name: str, default: int, minimum: int = 1) -> int:
    try:
        value = int(os.environ.get(name, str(default)) or default)
    except (TypeError, ValueError):
        value = default
    return max(minimum, value)


SCHEDULER_BATCH_HOUR = _int_env("WCNR_SCHEDULER_BATCH_HOUR", 3, 0)
SCHEDULER_DECAY_DOM = _int_env("WCNR_SCHEDULER_DECAY_DOM", 1, 1)
SCHEDULER_ALERT_SCAN_SECONDS = _int_env("WCNR_SCHEDULER_ALERT_SCAN_MINUTES", 5, 1) * 60
SCHEDULER_INCREMENTAL_SECONDS = _int_env("WCNR_SCHEDULER_INCREMENTAL_MINUTES", 10, 1) * 60


def _run_job(name: str, func) -> None:
    try:
        func()
    except Exception as exc:
        logger.warning("Scheduled job failed: %s: %s", name, exc)


def _scheduler_loop(app, stop_event: threading.Event) -> None:
    global _last_daily_key, _last_monthly_key, _last_alert_slot, _last_incremental_score_slot

    logger.info("WCNR scheduler thread started")
    app_context = app.app_context() if app is not None else None
    if app_context is not None:
        app_context.push()
    try:
        while not stop_event.is_set():
            now = time.localtime()
            daily_key = (now.tm_year, now.tm_yday)
            monthly_key = (now.tm_year, now.tm_mon)
            alert_slot = int(time.time() // SCHEDULER_ALERT_SCAN_SECONDS)
            incremental_score_slot = int(time.time() // SCHEDULER_INCREMENTAL_SECONDS)

            if now.tm_hour == SCHEDULER_BATCH_HOUR and _last_daily_key != daily_key:
                _last_daily_key = daily_key

                def daily_recalculate():
                    from modules.score.services.score_engine import batch_recalculate

                    batch_recalculate()

                _run_job("score batch_recalculate", daily_recalculate)

            if now.tm_mday == SCHEDULER_DECAY_DOM and now.tm_hour == 4 and _last_monthly_key != monthly_key:
                _last_monthly_key = monthly_key

                def monthly_score_decay():
                    from modules.score.services.score_engine import monthly_decay

                    monthly_decay()

                _run_job("score monthly_decay", monthly_score_decay)

            if _last_alert_slot != alert_slot:
                _last_alert_slot = alert_slot

                def alert_scan():
                    from modules.dashboard.services.alert_rule_engine import run_all_rules

                    run_all_rules()

                _run_job("alert run_all_rules", alert_scan)

            if _last_incremental_score_slot != incremental_score_slot:
                _last_incremental_score_slot = incremental_score_slot

                def incremental_score_scan():
                    from modules.score.services.score_engine import incremental_recalculate

                    incremental_recalculate(15)

                _run_job("score incremental_recalculate", incremental_score_scan)

            time.sleep(1)
    finally:
        if app_context is not None:
            app_context.pop()
        logger.info("WCNR scheduler thread stopped")


def start_scheduler(app=None) -> bool:
    global _scheduler_thread, _stop_event, _last_alert_slot, _last_incremental_score_slot

    if os.environ.get("WCNR_SCHEDULER_ENABLED", "1") != "1":
        return False
    if "pytest" in sys.modules:
        return False

    with _state_lock:
        if _scheduler_thread is not None and _scheduler_thread.is_alive():
            return False
        _stop_event = threading.Event()
        _last_alert_slot = int(time.time() // SCHEDULER_ALERT_SCAN_SECONDS)
        _last_incremental_score_slot = int(time.time() // SCHEDULER_INCREMENTAL_SECONDS)
        _scheduler_thread = threading.Thread(
            target=_scheduler_loop,
            args=(app, _stop_event),
            name="wcnr-scheduler",
            daemon=True,
        )
        _scheduler_thread.start()
        return True


def is_scheduler_running() -> bool:
    with _state_lock:
        return _scheduler_thread is not None and _scheduler_thread.is_alive()


def shutdown_scheduler() -> None:
    global _scheduler_thread, _stop_event

    with _state_lock:
        thread = _scheduler_thread
        stop_event = _stop_event
        _scheduler_thread = None
        _stop_event = None

    if stop_event is not None:
        stop_event.set()
    if thread is not None and thread.is_alive():
        thread.join(timeout=2)
