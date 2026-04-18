# MEMORY

This file is a compact handoff for continuing development without rereading the full chat history.

## Project Context

- Project path: `C:\Users\Administrator\Desktop\project\multi-rider`
- Current working branch for this handoff: `feature/worker-compose-architecture`
- Previous base branch: `refactor/readability-reorg`
- Current local runtime: Windows 10, managed with `uv` and `.venv`
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

Latest local verification:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Result:

```text
28 passed
```

Docker is not installed on the current Windows development machine, so `docker compose config` could not be run locally.

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
- `modules/face/services/library_task_service.py`
- `modules/face/services/identity_service.py`
- `modules/training/services/train_task_service.py`
- `modules/training/services/auto_annotate_task_service.py`
- `static/modules/face/face-library.js`
- `docs/project_design_methodology.md`

## Remaining Architecture Debt

The main remaining task is `detection`.

Current Web-thread entry points still exist:

- `modules/detection/job_routes.py`
  - `/start` Oracle batch detection starts a Web-process thread.
- `modules/detection/services/upload_job_service.py`
  - ZIP upload detection starts a Web-process thread.
  - Video upload detection starts a Web-process thread.

Recommended next migration:

1. Migrate Oracle batch detection `/start` first.
2. Keep `/progress/<job_id>`, `/jobs`, `/history`, and result download contracts stable.
3. Persist detection job state to SQLite from creation time.
4. Enqueue with `submit_task("detection", {"job_id": job_id, ...}, task_id=job_id)`.
5. Add `worker.py` detection handler that loads the persisted job and runs the existing `_run_job(...)`.
6. Only after Oracle detection is stable, migrate ZIP/video upload detection.

## Practical Priorities Next Time

Start here:

1. Verify GitHub branch CI or remote visibility after push.
2. If continuing architecture work, implement Worker migration for `modules/detection/job_routes.py` `/start`.
3. Add a lightweight `/healthz` route checking:
   - SQLite open/read/write.
   - output directory writable.
   - model files exist.
   - Worker queue has no excessive stale `running` tasks.
4. Consider adding a small admin/diagnostic page for task queue status.
5. On Ubuntu, validate:
   - `docker compose config`
   - `docker compose up -d`
   - `docker compose logs -f worker`
   - one end-to-end queued task.

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
