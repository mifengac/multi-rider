CREATE SCHEMA IF NOT EXISTS jcgkzx_monitor;

SET search_path TO jcgkzx_monitor;

CREATE TABLE IF NOT EXISTS wcnr_target_pool (
    zjhm VARCHAR(18) PRIMARY KEY,
    xm VARCHAR(50),
    xb VARCHAR(4),
    csrq VARCHAR(20),
    source_type VARCHAR(30),
    risk_score INTEGER DEFAULT 0,
    risk_level VARCHAR(10),
    ssfj VARCHAR(50),
    ssfjdm VARCHAR(12),
    sspcs VARCHAR(50),
    sspcsdm VARCHAR(12),
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE wcnr_target_pool IS '未成年人目标人员池';

CREATE TABLE IF NOT EXISTS wcnr_ryrl_gj (
    id BIGSERIAL PRIMARY KEY,
    zjhm VARCHAR(18),
    xm VARCHAR(50),
    device_id VARCHAR(50),
    device_name VARCHAR(200),
    shot_time TIMESTAMP,
    face_image TEXT,
    jd NUMERIC(12,8),
    wd NUMERIC(12,8),
    ssfj VARCHAR(50),
    sspcs VARCHAR(50)
);
CREATE INDEX IF NOT EXISTS idx_wcnr_ryrl_gj_zjhm ON wcnr_ryrl_gj (zjhm);
CREATE INDEX IF NOT EXISTS idx_wcnr_ryrl_gj_shot_time ON wcnr_ryrl_gj (shot_time);
CREATE INDEX IF NOT EXISTS idx_wcnr_ryrl_gj_device_id ON wcnr_ryrl_gj (device_id);
COMMENT ON TABLE wcnr_ryrl_gj IS '未成年人人员人脸轨迹';

CREATE TABLE IF NOT EXISTS wcnr_ly_checkin (
    id BIGSERIAL PRIMARY KEY,
    zjhm VARCHAR(18),
    xm VARCHAR(50),
    xb VARCHAR(4),
    nl INTEGER,
    lgmc VARCHAR(200),
    lgdz VARCHAR(300),
    rzsj TIMESTAMP,
    lksj TIMESTAMP,
    tfrxm VARCHAR(50),
    tfrzjhm VARCHAR(18),
    ssfj VARCHAR(50),
    sspcs VARCHAR(50)
);
CREATE INDEX IF NOT EXISTS idx_wcnr_ly_checkin_zjhm ON wcnr_ly_checkin (zjhm);
CREATE INDEX IF NOT EXISTS idx_wcnr_ly_checkin_rzsj ON wcnr_ly_checkin (rzsj);
COMMENT ON TABLE wcnr_ly_checkin IS '未成年人旅业入住记录';

CREATE TABLE IF NOT EXISTS wcnr_rk_zp (
    zjhm VARCHAR(18) PRIMARY KEY,
    xm VARCHAR(50),
    zp TEXT,
    zp_source VARCHAR(20),
    update_time TIMESTAMP
);
COMMENT ON TABLE wcnr_rk_zp IS '未成年人人口照片';

CREATE TABLE IF NOT EXISTS wcnr_czrk (
    zjhm VARCHAR(18) PRIMARY KEY,
    xm VARCHAR(50),
    xb VARCHAR(4),
    mz VARCHAR(20),
    csrq VARCHAR(20),
    hjdz VARCHAR(300),
    xzdxz VARCHAR(300),
    whcd VARCHAR(20),
    fqxm VARCHAR(50),
    fqzjhm VARCHAR(18),
    mqxm VARCHAR(50),
    mqzjhm VARCHAR(18),
    lxdh VARCHAR(30)
);
COMMENT ON TABLE wcnr_czrk IS '未成年人常住人口信息';

CREATE TABLE IF NOT EXISTS wcnr_score (
    zjhm VARCHAR(18) PRIMARY KEY,
    total_score INTEGER DEFAULT 0,
    risk_level VARCHAR(10),
    dim_case INTEGER DEFAULT 0,
    dim_behavior INTEGER DEFAULT 0,
    dim_family INTEGER DEFAULT 0,
    dim_education INTEGER DEFAULT 0,
    dim_social INTEGER DEFAULT 0,
    calc_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    detail_json TEXT
);
COMMENT ON TABLE wcnr_score IS '未成年人风险评分';

CREATE TABLE IF NOT EXISTS wcnr_score_history (
    id BIGSERIAL PRIMARY KEY,
    zjhm VARCHAR(18),
    total_score INTEGER,
    risk_level VARCHAR(10),
    calc_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_wcnr_score_history_zjhm ON wcnr_score_history (zjhm);
COMMENT ON TABLE wcnr_score_history IS '未成年人风险评分历史';

CREATE TABLE IF NOT EXISTS wcnr_alert (
    id BIGSERIAL PRIMARY KEY,
    zjhm VARCHAR(18),
    xm VARCHAR(50),
    alert_type VARCHAR(30),
    alert_level VARCHAR(10),
    alert_content TEXT,
    location VARCHAR(300),
    jd NUMERIC(12,8),
    wd NUMERIC(12,8),
    trigger_time TIMESTAMP,
    is_read BOOLEAN DEFAULT FALSE,
    handle_status VARCHAR(10) DEFAULT 'pending'
);
CREATE INDEX IF NOT EXISTS idx_wcnr_alert_trigger_time_desc ON wcnr_alert (trigger_time DESC);
CREATE INDEX IF NOT EXISTS idx_wcnr_alert_zjhm ON wcnr_alert (zjhm);
COMMENT ON TABLE wcnr_alert IS '未成年人风险预警';
