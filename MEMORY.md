# MEMORY

This file is a compact handoff for continuing development without rereading the full chat history.

## Project Context

- Project path: `C:\Users\So\Desktop\project\multi-rider`
- Current working branch for this handoff: `feature/worker-compose-architecture`
- Previous base branch: `refactor/readability-reorg`
- Current local runtime: Windows 10, managed with `uv`
- Future target runtime: Ubuntu 22 intranet server, 16 CPU cores, no GPU, long-running deployment
- Maintainer model: mostly one person, so prefer simple, observable, low-ops architecture

## Product Understanding

- This is an intranet AI-assisted task management / analysis system.
- It is an assembled system rather than a monolith of novel algorithms.
- Core modules:
  - `detection`: Oracle image query, local ZIP/video upload detection, result ZIP/history.
  - `face`: face library sync/rebuild, face identification, identity result persistence.
  - `dispatch`: auth, dispatch queue, task sending, SMS.
  - `training`: datasets, labeling, auto-annotation, YOLO training, model registry.
- Architecture direction: keep the system single-machine and simple, but separate Web request handling from CPU-heavy background work.

## Architecture Decision

Recommended target architecture for Ubuntu 22:

```text
Browser / intranet users
        |
        v
Web process/container
Flask API + pages + task creation
        |
        v
SQLite database
jobs, task state, durable queue
        ^
        |
Worker process/container
CPU-heavy jobs
        |
        v
Persistent local directories
output, datasets, face_data, train_runs, upload_tmp
```

Do not introduce Redis, Celery, PostgreSQL, Kubernetes, or microservices yet. For this deployment size, they add maintenance burden without enough benefit.

## Current Runtime Modes

### Windows 10 Current Mode

Continue using `uv` directly:

```powershell
.\.venv\Scripts\python.exe app.py
.\.venv\Scripts\python.exe worker.py
```

Optional typed workers:

```powershell
.\.venv\Scripts\python.exe worker.py --type detection
.\.venv\Scripts\python.exe worker.py --type upload
.\.venv\Scripts\python.exe worker.py --type train
.\.venv\Scripts\python.exe worker.py --type auto_annotate
.\.venv\Scripts\python.exe worker.py --type face_library
```

### Future Ubuntu 22 Mode

Use Docker Compose. Do not manually enter the container to start `worker.py`.

```bash
sudo docker compose up -d
```

Compose services:

- `multi-rider-web`: runs `python app.py`
- `multi-rider-worker`: runs `python worker.py`

Default persistent runtime root:

```text
/opt/multi-rider/runtime/
  data/jobs.sqlite3
  output/
  datasets/
  face_data/
  train_runs/
  upload_tmp/
```

## Work Completed In This Session

### Training Worker Migration

Changed training from Web-process threads to durable queued Worker mode.

- `modules/training/services/train_task_service.py`
  - `start_train_job()` now creates/saves a `train_jobs` record and calls:
    `submit_task("train", {"job_id": job_id}, task_id=job_id)`
  - No direct `threading.Thread(...)`.
- `modules/training/services/auto_annotate_task_service.py`
  - `start_auto_annotate_job()` now creates/saves an `auto_annotate_jobs` record and calls:
    `submit_task("auto_annotate", {"job_id": job_id, "asset_ids": asset_ids}, task_id=job_id)`
  - No direct `threading.Thread(...)`.
- `worker.py`
  - `train` handler loads existing train job by `job_id`, then calls `_run_train_job(job)`.
  - `auto_annotate` handler loads existing auto-annotate job by `job_id`, then calls `_run_auto_annotate_job(job, asset_ids)`.
  - Removed dependency on nonexistent `_prepare_train_job`.

### Task Queue Hardening

- `shared/task_queue.py`
  - Cleaned up documentation/comments.
  - `claim_task()` now uses `BEGIN IMMEDIATE` to avoid duplicate claims by concurrent workers.
  - Claim order is deterministic: `ORDER BY created_ts ASC, id ASC`.
- `tests/test_task_queue.py`
  - Added tests for basic claim behavior, type filtering, oldest-first ordering, concurrent claiming, and SQLite WAL settings.

### Face Library Worker Migration

Changed face library sync/rebuild from in-memory Web thread tasks to durable queued Worker mode.

- `shared/db/sqlite.py`
  - Added `face_library_jobs` table.
  - Added `save_face_library_job()`.
  - Added `get_face_library_job()`.
  - Added `get_active_face_library_job()`.
  - Added `list_face_library_jobs()`.
- `modules/face/services/library_task_service.py`
  - Removed in-memory `FACE_LIBRARY_TASKS` and background `threading.Thread(...)`.
  - `start_face_library_task()` now creates/saves a `queued` task and calls:
    `submit_task("face_library", {"job_id": task_id}, task_id=task_id)`
  - `_run_face_library_task(task)` executes `sync_face_library()` or `rebuild_face_library()` and persists progress.
- `worker.py`
  - `face_library` handler loads existing face-library job by `job_id`, then calls `_run_face_library_task(job)`.
- `static/modules/face/face-library.js`
  - Polling now treats both `queued` and `running` as active states.

### Oracle Detection Worker Migration

Changed Oracle batch detection from Web-process threads to durable queued Worker mode.

- `modules/detection/job_routes.py`
  - `/start` no longer starts `threading.Thread(...)`.
  - Route now creates a persisted queued job via `start_detection_job(...)`.
- `modules/detection/services/job_service.py`
  - Added `start_detection_job(...)`.
  - Oracle jobs now persist to SQLite before execution with status `queued`.
  - Active Oracle jobs are listed from SQLite instead of Web-process memory.
  - `_run_job(...)` now accepts the persisted job record, then writes running progress back to SQLite during batch execution.
  - Cancellation now works against persisted Oracle job state, not only in-process memory.
- `worker.py`
  - Added `detection` handler.
  - Worker now loads the persisted Oracle job by `job_id` and executes the existing detection pipeline.
- `shared/db/sqlite.py`
  - Added `list_active_jobs(...)` for queued/running job queries.
  - `mark_running_jobs_interrupted(...)` now supports filtering by `job_type`.
- `app.py`
  - Web bootstrap now only marks running `upload` jobs interrupted on restart.
  - This avoids incorrectly marking Worker-owned Oracle detection jobs as interrupted when only the Web process restarts.

### Upload Detection Worker Migration

Changed ZIP/video upload detection from Web-process threads to durable queued Worker mode.

- `modules/detection/services/upload_job_service.py`
  - Removed direct `threading.Thread(...)` startup for ZIP/video detection.
  - `start_zip_job()` and `start_video_job()` now create/save a queued `jobs` record and submit:
    `submit_task("upload", {"job_id": job_id}, task_id=job_id)`
  - Upload source file path, temp directory, and video `frame_interval` are now persisted in SQLite job records.
  - `_run_upload_job(...)` now loads the persisted job, executes inside Worker, and writes running progress back to SQLite during batch execution.
  - Upload cancellation now works against persisted SQLite job state instead of only Web-process memory.
- `worker.py`
  - Added `upload` handler.
  - Worker now loads the persisted upload job by `job_id` and runs ZIP/video detection.
- `shared/db/sqlite.py`
  - Added `source_path`, `temp_dir`, and `frame_interval` columns to `jobs`.
  - Old-job cleanup now removes persisted upload temp directories/source files in addition to result ZIPs.
- `app.py`
  - Web bootstrap no longer marks any `jobs` rows interrupted.
  - All entries in the shared `jobs` table are now Worker-owned (`oracle` and `upload`).
- `static/modules/detection/tasks.js`
  - Added explicit `queued` status UI so queued Worker tasks do not render as running.
- `templates/modules/detection/history/history.html`
  - Added explicit `queued` status UI.
- `templates/modules/detection/history/history_detail.html`
  - Added explicit `queued` status UI.

### Health Endpoint

Added a lightweight health endpoint for operability checks.

- `shared/health.py`
  - Added `/healthz` backend checks for:
    - SQLite open/read/write.
    - output directory writable.
    - configured model files exist.
    - stale `task_queue` rows stuck in `running`.
- `app.py`
  - Registered `GET /healthz`.
  - Returns HTTP `200` when all checks pass, otherwise `503`.

### Task Queue Diagnostics

Added read-only task queue observability.

- `shared/task_queue_diagnostics.py`
  - Summarizes task counts by status and task type.
  - Lists recent queue rows with redacted owners and without raw payload/result leakage.
  - Flags stale `running` tasks using the same stale threshold as `/healthz`.
- `modules/diagnostics/routes.py`
  - Registered `GET /diagnostics/task-queue`.
  - Supports `task_type`, `status`, and `limit` query parameters.
- `templates/modules/diagnostics/_task_queue_tab.html`
  - Added a Workbench diagnostics tab.
- `static/modules/diagnostics/task-queue.js`
  - Renders summary cards, health details, distributions, filters, and recent task rows.
- `ops/Dockerfile`
  - Container `HEALTHCHECK` now probes `/healthz` instead of the business `/jobs` endpoint.
- `docs/architecture_polish_checklist.md`
  - Added architecture and polish follow-up checklist.

### Ubuntu Compose Deployment

- Added `docker-compose.yml`
  - Starts Web and Worker as separate services.
  - Mounts persistent directories under `${MULTI_RIDER_ROOT:-./runtime}`.
  - Uses `${APP_ENV_FILE:-./app.env}`.
- Added `ops/app.env.ubuntu.example`
  - Ubuntu/Docker-specific paths:
    - `/app/data/jobs.sqlite3`
    - `/app/output`
    - `/app/datasets`
    - `/app/face_data`
    - `/app/train_runs`
    - `/app/upload_tmp`
  - Includes CPU-only defaults:
    - `OMP_NUM_THREADS=8`
    - `MKL_NUM_THREADS=8`
    - `OPENBLAS_NUM_THREADS=8`
    - `NUMEXPR_NUM_THREADS=8`
    - `TORCH_NUM_THREADS=8`
    - `OPENCV_NUM_THREADS=4`
- Updated `ops/Dockerfile`
  - Adds Linux container path ENV defaults.
  - Copies `worker.py`.
  - Creates `/app/data`, `/app/output`, `/app/datasets`, `/app/face_data`, `/app/train_runs`, `/app/upload_tmp`.
- Updated `README.md`
  - Keeps Windows 10 + `uv` workflow.
  - Adds Ubuntu 22 + Docker Compose workflow.
  - Explains that Worker does not need to be manually started inside the container.

### SQLite Multi-Process Hardening

- `shared/db/sqlite.py`
  - Main `_connect()` now uses:
    - `sqlite3.connect(SQLITE_DB_PATH, timeout=30)`
    - `PRAGMA journal_mode=WAL`
    - `PRAGMA busy_timeout=30000`
    - `PRAGMA synchronous=NORMAL`

### CPU Thread Controls

- `shared/config/config.py`
  - Added `TORCH_NUM_THREADS`.
  - Added `OPENCV_NUM_THREADS`.
- `shared/inference/infer_service.py`
  - Configures PyTorch CPU thread count when `TORCH_NUM_THREADS > 0`.
- `modules/face/services/identity_service.py`
  - Configures OpenCV thread count when `OPENCV_NUM_THREADS > 0`.

## Tests Added

- `tests/test_training_worker_queue.py`
  - Training job enqueue behavior.
  - Auto-annotate job enqueue behavior.
  - Worker train handler loads existing job.
  - Worker auto-annotate handler loads existing job.
- `tests/test_task_queue.py`
  - Durable queue claim behavior.
  - Type filtering and oldest-first claim behavior.
  - Concurrent claim safety.
  - SQLite WAL/busy-timeout configuration.
- `tests/test_face_library_worker_queue.py`
  - Face library task enqueue behavior.
  - Reuse existing active face library task.
  - Worker face library handler loads existing job.
  - Face library SQLite round-trip behavior.
- `tests/test_detection_worker_queue.py`
  - Oracle detection job enqueue behavior.
  - Worker detection handler loads existing job.
  - SQLite active-job listing and filtered interruption behavior.
- `tests/test_upload_worker_queue.py`
  - ZIP upload job enqueue behavior.
  - Video upload job enqueue behavior.
  - Worker upload handler loads existing job.
- `tests/test_health.py`
  - Healthy dependency state returns green report.
  - Missing model files and stale queue rows return unhealthy report.
- `tests/test_app_smoke.py`
  - Added `/healthz` route coverage for both healthy and unhealthy HTTP status codes.
  - Added task queue diagnostics route and template wiring coverage.
- `tests/test_task_queue_diagnostics.py`
  - Queue diagnostics summary, filtering, stale detection, and owner redaction.

Latest local verification:

```powershell
uv run --isolated --with-requirements requirements-dev.txt --with Flask==3.0.0 --with requests==2.31.0 --with Pillow==10.4.0 --with numpy==2.0.2 --with opencv-python-headless==4.12.0.88 -m pytest -q
```

Result:

```text
43 passed
```

Docker Desktop is installed on the current Windows development machine.

Compose precheck results:

- Default `docker compose config` fails because `./app.env` does not exist yet.
- `$env:APP_ENV_FILE='ops/app.env.ubuntu.example'; docker compose config` succeeds.
- `instantclient_11_2/libclntsh.so.11.1` is absent in this Windows workspace, so Docker build/start is not a valid Ubuntu E2E substitute until Linux Instant Client files are supplied.

Local endpoint smoke with Flask test client:

```text
/healthz 200 application/json
/diagnostics/task-queue 200 application/json
/ 200 text/html; charset=utf-8
```

## Important Files

- `README.md`
- `MEMORY.md`
- `docker-compose.yml`
- `ops/Dockerfile`
- `ops/app.env.example`
- `ops/app.env.ubuntu.example`
- `worker.py`
- `shared/task_queue.py`
- `shared/db/sqlite.py`
- `shared/config/config.py`
- `shared/inference/infer_service.py`
- `modules/detection/services/job_service.py`
- `modules/detection/services/upload_job_service.py`
- `modules/detection/job_routes.py`
- `modules/face/services/library_task_service.py`
- `modules/face/services/identity_service.py`
- `modules/training/services/train_task_service.py`
- `modules/training/services/auto_annotate_task_service.py`
- `static/modules/face/face-library.js`
- `tests/test_detection_worker_queue.py`
- `tests/test_upload_worker_queue.py`
- `docs/project_design_methodology.md`

## Remaining Architecture Debt

No remaining Web-thread debt exists in `detection`.

Current architecture debt is now mostly operability and diagnostics:

1. Validate Docker Compose end-to-end on Ubuntu with at least one Oracle job and one upload job.
2. Decide whether to expose task-queue inspection/retry controls in the UI.
3. Add a stronger deployment smoke script once the Ubuntu host and Linux Instant Client are available.

## Practical Priorities Next Time

Start here:

1. Verify GitHub branch CI or remote visibility after push.
2. On Ubuntu, validate:
   - `docker compose config`
   - `docker compose up -d`
   - `docker compose logs -f worker`
   - one Oracle task and one upload task end-to-end.
3. If operational controls are needed, add guarded retry/reset actions to the diagnostics page.

## Key Mental Model

Keep this project boring and durable:

```text
Web creates tasks.
SQLite persists tasks.
Worker executes tasks.
Local mounted directories persist artifacts.
Docker Compose keeps processes alive.
```

Avoid adding new infrastructure until SQLite + single-machine Docker Compose is no longer enough.
