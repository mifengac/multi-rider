-- 护苗系统安全审计扩展表

CREATE TABLE IF NOT EXISTS jcgkzx_monitor.hm_sys_user (
    user_id       VARCHAR(64) PRIMARY KEY,
    username      VARCHAR(80) NOT NULL UNIQUE,
    display_name  VARCHAR(100) NOT NULL DEFAULT '',
    org_code      VARCHAR(40) NOT NULL DEFAULT '',
    org_name      VARCHAR(160) NOT NULL DEFAULT '',
    phone         VARCHAR(40) NOT NULL DEFAULT '',
    status        VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at    TIMESTAMP DEFAULT NOW(),
    updated_at    TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS jcgkzx_monitor.hm_sys_role (
    role_id      VARCHAR(64) PRIMARY KEY,
    role_code    VARCHAR(60) NOT NULL UNIQUE,
    role_name    VARCHAR(100) NOT NULL,
    description  TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS jcgkzx_monitor.hm_sys_user_role (
    id          BIGSERIAL PRIMARY KEY,
    user_id     VARCHAR(64) NOT NULL,
    role_id     VARCHAR(64) NOT NULL,
    created_at  TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uq_hm_sys_user_role UNIQUE (user_id, role_id)
);

CREATE TABLE IF NOT EXISTS jcgkzx_monitor.hm_audit_log (
    audit_id                VARCHAR(64) PRIMARY KEY,
    user_id                 VARCHAR(64) NOT NULL DEFAULT '',
    username                VARCHAR(80) NOT NULL DEFAULT '',
    owner_key               VARCHAR(100),
    owner_ip                VARCHAR(80),
    module_code             VARCHAR(60) NOT NULL DEFAULT '',
    action_code             VARCHAR(60) NOT NULL DEFAULT '',
    target_type             VARCHAR(80) NOT NULL DEFAULT '',
    target_id               VARCHAR(120) NOT NULL DEFAULT '',
    request_path            TEXT NOT NULL DEFAULT '',
    request_method          VARCHAR(20) NOT NULL DEFAULT '',
    request_payload_digest  VARCHAR(80) NOT NULL DEFAULT '',
    result_status           VARCHAR(30) NOT NULL DEFAULT 'success',
    error_msg               TEXT NOT NULL DEFAULT '',
    created_at              TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hm_audit_log_created
    ON jcgkzx_monitor.hm_audit_log (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_hm_audit_log_module_action
    ON jcgkzx_monitor.hm_audit_log (module_code, action_code, created_at DESC);

CREATE TABLE IF NOT EXISTS jcgkzx_monitor.hm_sensitive_access_log (
    access_id     VARCHAR(64) PRIMARY KEY,
    user_id       VARCHAR(64) NOT NULL DEFAULT '',
    username      VARCHAR(80) NOT NULL DEFAULT '',
    sfzh          VARCHAR(32) NOT NULL DEFAULT '',
    field_codes   TEXT NOT NULL DEFAULT '',
    purpose       TEXT NOT NULL DEFAULT '',
    module_code   VARCHAR(60) NOT NULL DEFAULT '',
    created_at    TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hm_sensitive_access_created
    ON jcgkzx_monitor.hm_sensitive_access_log (created_at DESC);

