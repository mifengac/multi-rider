from __future__ import annotations

from flask import Flask, request

from modules.security.services.audit_service import record_action


AUDITED_ROUTES = (
    ("POST", "/start", "detection", "run", "job"),
    ("POST", "/upload/start", "detection", "upload", "job"),
    ("POST", "/face/identify", "face", "identify", "face_result"),
    ("POST", "/dispatch/send", "dispatch", "send", "dispatch_queue"),
    ("POST", "/dispatch/sms/send", "dispatch", "sms", "dispatch_queue"),
    ("POST", "/train", "training", "manage", "training"),
    ("POST", "/api/graph/sync", "graph", "run_algo", "graph_sync"),
    ("POST", "/api/graph/detect", "graph", "run_algo", "gang_detect"),
    ("POST", "/ruizhi/api", "ruizhi", "ai_call", "ruizhi"),
)


def _match_audit_route(method: str, path: str):
    for route_method, prefix, module_code, action_code, target_type in AUDITED_ROUTES:
        if method == route_method and path.startswith(prefix):
            return module_code, action_code, target_type
    return None


def register_security_hooks(app: Flask) -> None:
    @app.after_request
    def audit_after_request(response):
        match = _match_audit_route(request.method, request.path)
        if not match:
            return response
        module_code, action_code, target_type = match
        status = "success" if response.status_code < 400 else "failed"
        record_action(
            request,
            module_code=module_code,
            action_code=action_code,
            target_type=target_type,
            target_id=(request.view_args or {}).get("job_id") or (request.view_args or {}).get("queue_id") or "",
            result_status=status,
            error_msg="" if status == "success" else f"HTTP {response.status_code}",
        )
        return response
