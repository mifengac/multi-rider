-- 护苗系统态势统计扩展表
-- 用途: 缓存统计指标与报表，便于日报/周报/月报复用。

CREATE TABLE IF NOT EXISTS jcgkzx_monitor.hm_statistics_metric_snapshot (
    snapshot_id       VARCHAR(64) PRIMARY KEY,
    metric_code       VARCHAR(80) NOT NULL,
    metric_name       VARCHAR(120) NOT NULL,
    metric_value      NUMERIC(18, 4) DEFAULT 0,
    metric_unit       VARCHAR(20) DEFAULT '',
    dimension_json    TEXT DEFAULT '{}',
    period_type       VARCHAR(20) NOT NULL DEFAULT 'custom',
    period_start      TIMESTAMP,
    period_end        TIMESTAMP,
    computed_at       TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hm_statistics_metric_period
    ON jcgkzx_monitor.hm_statistics_metric_snapshot (metric_code, period_type, period_start, period_end);

CREATE TABLE IF NOT EXISTS jcgkzx_monitor.hm_statistics_report_cache (
    report_id         VARCHAR(64) PRIMARY KEY,
    report_type       VARCHAR(30) NOT NULL DEFAULT 'custom',
    title             VARCHAR(200) NOT NULL DEFAULT '',
    period_start      TIMESTAMP,
    period_end        TIMESTAMP,
    report_json       TEXT NOT NULL DEFAULT '{}',
    created_at        TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hm_statistics_report_created
    ON jcgkzx_monitor.hm_statistics_report_cache (created_at DESC);

