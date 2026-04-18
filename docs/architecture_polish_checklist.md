# Architecture And Polish Checklist

Date: 2026-04-19

This checklist records follow-up work after moving heavy jobs to the durable SQLite-backed Worker queue and adding `/healthz` plus task-queue diagnostics.

## Architecture Improvements

| Priority | Area | Observation | Recommended follow-up |
|---|---|---|---|
| P0 | Ubuntu deployment | Current Windows workspace can parse Compose, but true Ubuntu E2E still needs Linux Oracle Instant Client files and a real `app.env`. | Validate on the target Ubuntu 22 host with `docker compose config`, `docker compose up -d`, `/healthz`, one Oracle job, and one upload job. |
| P1 | Queue operations | Diagnostics are now read-only; stale/failed tasks are visible but cannot be retried or reset from UI. | Add guarded admin actions later: reset stale running tasks, retry failed tasks, and inspect a single task. Keep them explicit and auditable. |
| P1 | Docker health | Container health now checks `/healthz`, which also verifies models and queue state. A missing model can mark Web unhealthy even when the HTTP process is alive. | Keep this strict for production; if rollout needs softer checks, split `/livez` from `/healthz`. |
| P1 | Config hygiene | `docker-compose.yml` defaults to `./app.env`, but the repo only ships examples. | Document the required copy step clearly and consider adding a safe `app.env.local.example` for Windows demos. |
| P2 | Module boundaries | `modules/detection/job_routes.py` still mixes page rendering, request parsing, status APIs, and dashboard stats. | Split dashboard/history helpers into service modules after the worker migration stabilizes. |
| P2 | Task observability | The queue stores task result/error, while business jobs store richer progress. The relationship is only linked by `payload.job_id`. | Keep using `job_id`, but consider a small task detail endpoint that joins queue row and business job snapshot. |
| P2 | SQLite lifecycle | WAL and busy timeouts are set, but backups and compaction are still manual. | Add an ops note for backing up `jobs.sqlite3` and optionally a maintenance command for old queue rows. |
| P3 | Auth model | Browser-side demo auth is useful for intranet demos but not a strong access-control boundary. | Before broader rollout, decide whether to add server-side login, IP allowlist, or reverse-proxy auth. |

## Polish Improvements

| Priority | Area | Observation | Recommended follow-up |
|---|---|---|---|
| P1 | Encoding/readability | Some terminal output shows mojibake on Windows PowerShell even when pages render as UTF-8. | Standardize PowerShell profile or docs around UTF-8 output (`chcp 65001`, `$OutputEncoding`). |
| P1 | Header actions | The shared top-right action button still mostly uses the Oracle start action across tabs. | Make each tab own its primary action: upload file, sync face library, start training, dispatch selected, refresh diagnostics. |
| P1 | Empty/error states | Most modules have usable empty states, but diagnostics and history should consistently show next action guidance. | Add concise remediation text for missing Worker, missing models, stale tasks, and empty queues. |
| P2 | Queue detail UX | The diagnostics table is intentionally compact and omits full payload/result. | Later add a drawer for one task with redacted payload/result, linked business job, and related logs. |
| P2 | Manual test script | There is no single smoke script for local deployment checks. | Add an ops smoke script that hits `/healthz`, `/diagnostics/task-queue`, `/`, and verifies Worker can claim a synthetic task in a test DB. |
| P2 | Deployment docs | README covers Windows and Ubuntu paths, but final Ubuntu validation results are not yet captured from the real server. | After target-host validation, add a short deployment runbook with exact commands and expected outputs. |
| P3 | Visual consistency | The new diagnostics page follows the existing Tailwind/editorial style, but operational tables could be denser. | Tune table density and sticky headers after real queue volume is known. |
| P3 | Internationalized labels | Internal API statuses are English while UI labels are Chinese. This is acceptable but scattered. | Centralize status label maps if more admin pages are added. |

## Current Validation Notes

- Local automated test baseline is green.
- Docker Desktop is available on this Windows machine.
- `docker compose config` succeeds when `APP_ENV_FILE=ops/app.env.ubuntu.example` is provided.
- Default `docker compose config` fails until a real `app.env` is created.
- `instantclient_11_2/libclntsh.so.11.1` is absent in this Windows workspace, so Docker image build and true Ubuntu-style startup should be treated as blocked until Linux Instant Client files are supplied.
