-- 护苗系统锐智 AI 服务平台接入表
-- 用途: 记录大模型调用、AI 助手会话、知识库映射和知识库文件关联。
-- 注意: 不保存完整敏感提示词，仅保存脱敏内容或摘要。

CREATE TABLE IF NOT EXISTS jcgkzx_monitor.hm_ruizhi_call_log (
    call_id           VARCHAR(64) PRIMARY KEY,
    module_code       VARCHAR(40) NOT NULL DEFAULT '',      -- chat/kb/embedding/rerank/ocr/audio/report
    operation         VARCHAR(80) NOT NULL DEFAULT '',      -- models.list/chat.completions/kbs.create 等
    model_name        VARCHAR(120) NOT NULL DEFAULT '',
    request_digest    VARCHAR(80) NOT NULL DEFAULT '',
    response_digest   VARCHAR(80) NOT NULL DEFAULT '',
    status_code       INTEGER NOT NULL DEFAULT 0,
    success           BOOLEAN NOT NULL DEFAULT FALSE,
    elapsed_ms        INTEGER NOT NULL DEFAULT 0,
    error_msg         TEXT NOT NULL DEFAULT '',
    operator_id       VARCHAR(80) NOT NULL DEFAULT '',
    operator_name     VARCHAR(120) NOT NULL DEFAULT '',
    created_at        TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hm_ruizhi_call_log_created
    ON jcgkzx_monitor.hm_ruizhi_call_log (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_hm_ruizhi_call_log_module
    ON jcgkzx_monitor.hm_ruizhi_call_log (module_code, operation, created_at DESC);

CREATE TABLE IF NOT EXISTS jcgkzx_monitor.hm_ai_assistant_session (
    session_id        VARCHAR(64) PRIMARY KEY,
    session_title     VARCHAR(200) NOT NULL DEFAULT '',
    scenario_code     VARCHAR(40) NOT NULL DEFAULT 'general',
    related_sfzh      VARCHAR(32) NOT NULL DEFAULT '',
    related_job_id    VARCHAR(80) NOT NULL DEFAULT '',
    related_queue_id  VARCHAR(80) NOT NULL DEFAULT '',
    created_by        VARCHAR(80) NOT NULL DEFAULT '',
    created_at        TIMESTAMP DEFAULT NOW(),
    updated_at        TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hm_ai_assistant_session_updated
    ON jcgkzx_monitor.hm_ai_assistant_session (updated_at DESC);

CREATE TABLE IF NOT EXISTS jcgkzx_monitor.hm_ai_assistant_message (
    message_id       VARCHAR(64) PRIMARY KEY,
    session_id       VARCHAR(64) NOT NULL,
    role             VARCHAR(20) NOT NULL DEFAULT 'user',  -- user/assistant/system/tool/docs
    content_text     TEXT NOT NULL DEFAULT '',             -- 脱敏后的消息内容
    content_digest   VARCHAR(80) NOT NULL DEFAULT '',
    model_name       VARCHAR(120) NOT NULL DEFAULT '',
    tool_call_json   TEXT NOT NULL DEFAULT '{}',
    docs_ref_json    TEXT NOT NULL DEFAULT '[]',
    created_at       TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hm_ai_assistant_message_session
    ON jcgkzx_monitor.hm_ai_assistant_message (session_id, created_at);

CREATE TABLE IF NOT EXISTS jcgkzx_monitor.hm_ruizhi_kb_mapping (
    kb_id              VARCHAR(64) PRIMARY KEY,
    kb_name            VARCHAR(160) NOT NULL UNIQUE,
    display_name       VARCHAR(200) NOT NULL DEFAULT '',
    description        TEXT NOT NULL DEFAULT '',
    ruizhi_kb_name     VARCHAR(160) NOT NULL DEFAULT '',
    split_config_json  TEXT NOT NULL DEFAULT '{}',
    status             VARCHAR(30) NOT NULL DEFAULT 'active',
    created_by         VARCHAR(80) NOT NULL DEFAULT '',
    created_at         TIMESTAMP DEFAULT NOW(),
    updated_at         TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS jcgkzx_monitor.hm_ruizhi_kb_file (
    id               VARCHAR(64) PRIMARY KEY,
    kb_name          VARCHAR(160) NOT NULL DEFAULT '',
    file_id          VARCHAR(120) NOT NULL DEFAULT '',
    filename         VARCHAR(300) NOT NULL DEFAULT '',
    purpose          VARCHAR(40) NOT NULL DEFAULT '',
    bytes            BIGINT NOT NULL DEFAULT 0,
    parse_status     VARCHAR(40) NOT NULL DEFAULT '',
    callback_status  VARCHAR(40) NOT NULL DEFAULT '',
    created_at       TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hm_ruizhi_kb_file_kb
    ON jcgkzx_monitor.hm_ruizhi_kb_file (kb_name, created_at DESC);

