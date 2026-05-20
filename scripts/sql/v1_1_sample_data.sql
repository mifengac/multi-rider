INSERT INTO "jcgkzx_monitor"."wcnr_alert"
  (zjhm, xm, alert_type, alert_level, alert_content, location, trigger_time)
VALUES
  (
    '441901200812045018',
    '张某',
    'high_risk_face_hit',
    'critical',
    '高风险人员在XX路口被抓拍',
    'XX路与XX路交叉口',
    NOW() - INTERVAL '30 minutes'
  ),
  (
    '441901200812045019',
    '李某',
    'night_aggregation',
    'warning',
    '夜间聚集预警：XX网吧 3人聚集',
    'XX网吧',
    NOW() - INTERVAL '15 minutes'
  )
ON CONFLICT DO NOTHING;
