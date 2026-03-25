from __future__ import annotations

from uuid import uuid4

from flask import Request, session


OWNER_SESSION_KEY = "owner_key"


def get_request_owner(request: Request) -> tuple[str, str]:
    owner_key = str(session.get(OWNER_SESSION_KEY) or "").strip()
    if not owner_key:
        owner_key = uuid4().hex
        session[OWNER_SESSION_KEY] = owner_key
        session.modified = True

    owner_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or request.remote_addr or ""
    return owner_key, owner_ip


def job_matches_owner(job: dict | None, owner_key: str, owner_ip: str) -> bool:
    if not job:
        return False

    stored_owner_key = str(job.get("owner_key") or "").strip()
    if stored_owner_key:
        return bool(owner_key) and stored_owner_key == owner_key

    stored_owner_ip = str(job.get("owner_ip") or "").strip()
    return bool(owner_ip) and stored_owner_ip == owner_ip
