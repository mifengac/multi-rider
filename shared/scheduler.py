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


def _run_job(name: str, func) -> None:
    try:
        func()
    except Exception as exc:
        logger.warning("Scheduled job failed: %s: %s", name, exc)


def _scheduler_loop(app, stop_event: threading.Event) -> None:
    global _last_daily_key, _last_monthly_key, _last_alert_slot

    logger.info("WCNR scheduler thread started")
    app_context = app.app_context() if app is not None else None
    if app_context is not None:
        app_context.push()
    try:
        while not stop_event.is_set():
            now = time.localtime()
            daily_key = (now.tm_year, now.tm_yday)
            monthly_key = (now.tm_year, now.tm_mon)
            alert_slot = int(time.time() // 300)

            if now.tm_hour == 3 and _last_daily_key != daily_key:
                _last_daily_key = daily_key

                def daily_recalculate():
                    from modules.score.services.score_engine import batch_recalculate

                    batch_recalculate()

                _run_job("score batch_recalculate", daily_recalculate)

            if now.tm_mday == 1 and now.tm_hour == 4 and _last_monthly_key != monthly_key:
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

            time.sleep(1)
    finally:
        if app_context is not None:
            app_context.pop()
        logger.info("WCNR scheduler thread stopped")


def start_scheduler(app=None) -> bool:
    global _scheduler_thread, _stop_event, _last_alert_slot

    if os.environ.get("WCNR_SCHEDULER_ENABLED", "1") != "1":
        return False
    if "pytest" in sys.modules:
        return False

    with _state_lock:
        if _scheduler_thread is not None and _scheduler_thread.is_alive():
            return False
        _stop_event = threading.Event()
        _last_alert_slot = int(time.time() // 300)
        _scheduler_thread = threading.Thread(
            target=_scheduler_loop,
            args=(app, _stop_event),
            name="wcnr-scheduler",
            daemon=True,
        )
        _scheduler_thread.start()
        return True


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
