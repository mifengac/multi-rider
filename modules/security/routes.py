from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request

from modules.security.services.audit_service import (
    current_user_from_request,
    list_audit_logs,
    list_sensitive_access_logs,
    record_sensitive_access,
)
from modules.security.services.masking_service import mask_value
from modules.security.services.permission_service import permissions_for_roles


security_bp = Blueprint("security", __name__, url_prefix="/security")


@security_bp.get("/")
def security_page():
    return render_template("security/index.html")


@security_bp.get("/api/me")
def security_me():
    user = current_user_from_request(request)
    user["permissions"] = permissions_for_roles(user.get("roles") or [])
    return jsonify({"ok": True, "user": user})


@security_bp.get("/api/audit-logs")
def security_audit_logs():
    return jsonify(
        {
            "ok": True,
            "items": list_audit_logs(
                module_code=(request.args.get("module_code") or "").strip(),
                action_code=(request.args.get("action_code") or "").strip(),
                username=(request.args.get("username") or "").strip(),
                limit=int(request.args.get("limit") or 100),
            ),
        }
    )


@security_bp.get("/api/sensitive-access")
def security_sensitive_access():
    return jsonify({"ok": True, "items": list_sensitive_access_logs(limit=int(request.args.get("limit") or 100))})


@security_bp.post("/api/reveal-sensitive")
def security_reveal_sensitive():
    payload = request.get_json(silent=True) or {}
    sfzh = str(payload.get("sfzh") or "").strip()
    field_code = str(payload.get("field_code") or "").strip()
    value = payload.get("value") or ""
    purpose = str(payload.get("purpose") or "").strip()
    if not purpose:
        return jsonify({"ok": False, "error": "purpose is required"}), 400
    record_sensitive_access(
        request,
        sfzh=sfzh,
        field_codes=[field_code] if field_code else [],
        purpose=purpose,
        module_code=str(payload.get("module_code") or "security"),
    )
    return jsonify({"ok": True, "value": value, "masked": mask_value(field_code, value)})

