CREATE SCHEMA IF NOT EXISTS "jcgkzx_monitor";

CREATE TABLE IF NOT EXISTS "jcgkzx_monitor"."wcnr_alert" (
  id SERIAL PRIMARY KEY,
  zjhm VARCHAR(18),
  xm VARCHAR(50),
  alert_type VARCHAR(50),
  alert_level VARCHAR(20),
  alert_content TEXT,
  location VARCHAR(200),
  trigger_time TIMESTAMP,
  is_read BOOLEAN DEFAULT FALSE,
  handle_status VARCHAR(50) DEFAULT 'pending',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(zjhm, alert_type, location, trigger_time)
);

CREATE TABLE IF NOT EXISTS "jcgkzx_monitor"."wcnr_score_history" (
  id SERIAL PRIMARY KEY,
  zjhm VARCHAR(18),
  total_score INT,
  risk_level VARCHAR(20),
  month_date DATE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(zjhm, month_date)
);

CREATE INDEX IF NOT EXISTS idx_wcnr_alert_trigger_time
  ON "jcgkzx_monitor"."wcnr_alert"(trigger_time DESC);
CREATE INDEX IF NOT EXISTS idx_wcnr_alert_zjhm
  ON "jcgkzx_monitor"."wcnr_alert"(zjhm);
CREATE INDEX IF NOT EXISTS idx_wcnr_score_history_month
  ON "jcgkzx_monitor"."wcnr_score_history"(month_date DESC);
