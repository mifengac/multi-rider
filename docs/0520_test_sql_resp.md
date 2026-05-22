#   一、关系图谱「未找到该人员的关系数据」根因
##  -- 1. target_pool 是否为空？
  SELECT COUNT(*) FROM jcgkzx_monitor.wcnr_target_pool;
  结果是:279
##  -- 2. 这个 zjhm 是否存在？
  SELECT zjhm, xm, ssfj FROM jcgkzx_monitor.wcnr_target_pool WHERE zjhm = '445302xxxxxxxx1512';
  结果是有数据的:INSERT INTO jcgkzx_monitor.wcnr_target_pool ("xm","zjhm","ssfj") VALUES
	 ('xxx','445302xxxxxxxx1512',NULL);
##  -- 3. 取 3 个真实存在的 zjhm 用来测试,
  SELECT zjhm, xm FROM jcgkzx_monitor.wcnr_target_pool LIMIT 3;
结果是3个都报这个错
[2026-05-20 03:10:48,404] ERROR: Exception on /api/graph/person/445381xxxxxxxx0831 [GET]
Traceback (most recent call last):
  File "/usr/local/lib/python3.12/site-packages/flask/app.py", line 1455, in wsgi_app
    response = self.full_dispatch_request()
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/site-packages/flask/app.py", line 869, in full_dispatch_request
    rv = self.handle_user_exception(e)
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/site-packages/flask/app.py", line 867, in full_dispatch_request
    rv = self.dispatch_request()
         ^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/site-packages/flask/app.py", line 852, in dispatch_request
    return self.ensure_sync(self.view_functions[rule.endpoint])(**view_args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/modules/graph/routes.py", line 33, in person_graph
    result = build_person_graph(zjhm, depth, relations=relations, time_range=time_range)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/modules/graph/services/graph_builder.py", line 229, in build_person_graph
    _add_school(zjhm, nodes, edges)
  File "/app/modules/graph/services/graph_builder.py", line 346, in _add_school
    row = query_one(sql, {"zjhm": zjhm})
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/shared/db/kingbase.py", line 107, in query_one
    cursor.execute(sql, params)
  File "/usr/local/lib/python3.12/site-packages/psycopg2/extras.py", line 236, in execute
    return super().execute(query, vars)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
psycopg2.errors.UndefinedColumn: column "yxx" does not exist
LINE 2:         SELECT yxx FROM "ywdata"."b_per_qscxwcnr" WHERE zjhm...
#   三、内网一键自检 SQL（直接复制到 KingBase）
##   -- 【A】关键表存量
  SELECT 'wcnr_target_pool' AS tbl, COUNT(*) AS rows FROM jcgkzx_monitor.wcnr_target_pool
  UNION ALL SELECT 'wcnr_score', COUNT(*) FROM jcgkzx_monitor.wcnr_score
  UNION ALL SELECT 'wcnr_alert', COUNT(*) FROM jcgkzx_monitor.wcnr_alert
  UNION ALL SELECT 'wcnr_ryrl_gj', COUNT(*) FROM jcgkzx_monitor.wcnr_ryrl_gj
  UNION ALL SELECT 'wcnr_score_history', COUNT(*) FROM jcgkzx_monitor.wcnr_score_history
  UNION ALL SELECT 'wcnr_ly_checkin', COUNT(*) FROM jcgkzx_monitor.wcnr_ly_checkin
  UNION ALL SELECT 'zq_zfba_ajxx', COUNT(*) FROM ywdata.zq_zfba_ajxx
  UNION ALL SELECT 'zq_zfba_xyrxx', COUNT(*) FROM ywdata.zq_zfba_xyrxx
  UNION ALL SELECT 'zq_zfba_wcnr_sfzxx', COUNT(*) FROM ywdata.zq_zfba_wcnr_sfzxx;
  结果是:
{
"  SELECT 'wcnr_target_pool' AS tbl, COUNT(*) AS rows FROM jcgkzx_monitor.wcnr_target_pool\n  UNION ALL SELECT 'wcnr_score', COUNT(*) FROM jcgkzx_monitor.wcnr_score\n  UNION ALL SELECT 'wcnr_alert', COUNT(*) FROM jcgkzx_monitor.wcnr_alert\n  UNION ALL SELECT 'wcnr_ryrl_gj', COUNT(*) FROM jcgkzx_monitor.wcnr_ryrl_gj\n  UNION ALL SELECT 'wcnr_score_history', COUNT(*) FROM jcgkzx_monitor.wcnr_score_history\n  UNION ALL SELECT 'wcnr_ly_checkin', COUNT(*) FROM jcgkzx_monitor.wcnr_ly_checkin\n  UNION ALL SELECT 'zq_zfba_ajxx', COUNT(*) FROM ywdata.zq_zfba_ajxx\n  UNION ALL SELECT 'zq_zfba_xyrxx', COUNT(*) FROM ywdata.zq_zfba_xyrxx\n  UNION ALL SELECT 'zq_zfba_wcnr_sfzxx', COUNT(*) FROM ywdata.zq_zfba_wcnr_sfzxx;": [
	{
		"tbl" : "wcnr_ly_checkin",
		"rows" : 60
	},
	{
		"tbl" : "wcnr_score_history",
		"rows" : 279
	},
	{
		"tbl" : "wcnr_target_pool",
		"rows" : 279
	},
	{
		"tbl" : "wcnr_alert",
		"rows" : 0
	},
	{
		"tbl" : "wcnr_score",
		"rows" : 279
	},
	{
		"tbl" : "zq_zfba_wcnr_sfzxx",
		"rows" : 680
	},
	{
		"tbl" : "wcnr_ryrl_gj",
		"rows" : 8427
	},
	{
		"tbl" : "zq_zfba_ajxx",
		"rows" : 31871
	},
	{
		"tbl" : "zq_zfba_xyrxx",
		"rows" : 58385
	}
]}
##  -- 【B】关键字段空值情况（target_pool）
  SELECT COUNT(*) FILTER (WHERE ssfj IS NOT NULL) AS with_ssfj,
         COUNT(*) FILTER (WHERE csrq IS NOT NULL) AS with_csrq,
         COUNT(*) AS total
  FROM jcgkzx_monitor.wcnr_target_pool;
  结果是:
  {
"  SELECT COUNT(*) FILTER (WHERE ssfj IS NOT NULL) AS with_ssfj,\n         COUNT(*) FILTER (WHERE csrq IS NOT NULL) AS with_csrq,\n         COUNT(*) AS total\n  FROM jcgkzx_monitor.wcnr_target_pool;": [
	{
		"with_ssfj" : 0,
		"with_csrq" : 0,
		"total" : 279
	}
]}
##   -- 【C】risk_level 是否回填（评分引擎是否跑过）
  SELECT COUNT(*) FILTER (WHERE risk_level IS NOT NULL) AS with_risk,
         COUNT(*) AS total
  FROM jcgkzx_monitor.wcnr_score;
  结果是:
  {
"  SELECT COUNT(*) FILTER (WHERE risk_level IS NOT NULL) AS with_risk,\n         COUNT(*) AS total\n  FROM jcgkzx_monitor.wcnr_score;": [
	{
		"with_risk" : 279,
		"total" : 279
	}
]}
##   -- 【D】案件 fasj/嫌疑人年龄情况
  SELECT MIN(ajxx_fasj)::text AS min_fasj, MAX(ajxx_fasj)::text AS max_fasj,
         COUNT(*) AS total_cases
  FROM ywdata.zq_zfba_ajxx;
结果是:
{
"  SELECT MIN(ajxx_fasj)::text AS min_fasj, MAX(ajxx_fasj)::text AS max_fasj,\n         COUNT(*) AS total_cases\n  FROM ywdata.zq_zfba_ajxx;": [
	{
		"min_fasj" : "1994-03-01 17:07:25",
		"max_fasj" : "2026-05-18 21:03:07",
		"total_cases" : 31871
	}
]}

##  -- 【E】轨迹时间/坐标
  SELECT MIN(shot_time)::text AS min_t, MAX(shot_time)::text AS max_t,
         COUNT(*) FILTER (WHERE jd IS NOT NULL AND wd IS NOT NULL) AS with_coord,
  FROM jcgkzx_monitor.wcnr_ryrl_gj
  FROM jcgkzx_monitor.wcnr_ryrl_gj
  WHERE shot_time >= CURRENT_TIMESTAMP - INTERVAL '30 days';
结果是:
SQL 错误 [42601]: ERROR: syntax error at or near "FROM"¶  Position: 156 At Line: 3, Line Position: 3
#  四、若内网数据都在，仍空白时的诊断动作
##  2. 实时预警空 → 手动触发告警扫描：
  SELECT COUNT(*) FILTER (WHERE ssfj IS NOT NULL) AS with_ssfj,
         COUNT(*) FILTER (WHERE csrq IS NOT NULL) AS with_csrq,
         COUNT(*) AS total
  FROM jcgkzx_monitor.wcnr_target_pool;
结果是:
{
"  SELECT COUNT(*) FILTER (WHERE ssfj IS NOT NULL) AS with_ssfj,\n         COUNT(*) FILTER (WHERE csrq IS NOT NULL) AS with_csrq,\n         COUNT(*) AS total\n  FROM jcgkzx_monitor.wcnr_target_pool;": [
	{
		"with_ssfj" : 0,
		"with_csrq" : 0,
		"total" : 279
	}
]}

##  -- 【C】risk_level 是否回填（评分引擎是否跑过）
  SELECT COUNT(*) FILTER (WHERE risk_level IS NOT NULL) AS with_risk,
         COUNT(*) AS total
  FROM jcgkzx_monitor.wcnr_score;
结果是:
{
"  SELECT COUNT(*) FILTER (WHERE risk_level IS NOT NULL) AS with_risk,\n         COUNT(*) AS total\n  FROM jcgkzx_monitor.wcnr_score;": [
	{
		"with_risk" : 279,
		"total" : 279
	}
]}

##  -- 【D】案件 fasj/嫌疑人年龄情况
  SELECT MIN(ajxx_fasj)::text AS min_fasj, MAX(ajxx_fasj)::text AS max_fasj,
         COUNT(*) AS total_cases
  FROM ywdata.zq_zfba_ajxx;
结果是:
{
"  SELECT MIN(ajxx_fasj)::text AS min_fasj, MAX(ajxx_fasj)::text AS max_fasj,\n         COUNT(*) AS total_cases\n  FROM ywdata.zq_zfba_ajxx;": [
	{
		"min_fasj" : "1994-03-01 17:07:25",
		"max_fasj" : "2026-05-18 21:03:07",
		"total_cases" : 31871
	}
]}
##  -- 【E】轨迹时间/坐标
  SELECT MIN(shot_time)::text AS min_t, MAX(shot_time)::text AS max_t,
         COUNT(*) FILTER (WHERE jd IS NOT NULL AND wd IS NOT NULL) AS with_coord,
         COUNT(*) AS total
  FROM jcgkzx_monitor.wcnr_ryrl_gj
  WHERE shot_time >= CURRENT_TIMESTAMP - INTERVAL '30 days';
结果是:
{
"  SELECT MIN(shot_time)::text AS min_t, MAX(shot_time)::text AS max_t,\n         COUNT(*) FILTER (WHERE jd IS NOT NULL AND wd IS NOT NULL) AS with_coord,\n         COUNT(*) AS total\n  FROM jcgkzx_monitor.wcnr_ryrl_gj\n  WHERE shot_time >= CURRENT_TIMESTAMP - INTERVAL '30 days';": [
	{
		"min_t" : "2026-04-20 11:34:45",
		"max_t" : "2026-05-18 20:10:43",
		"with_coord" : 2745,
		"total" : 2745
	}
]}

##  -- 【F】告警表回填（触发扫描后看是否有新增）
  SELECT alert_type, COUNT(*) FROM jcgkzx_monitor.wcnr_alert GROUP BY alert_type;
结果是:
{
"  SELECT alert_type, COUNT(*) FROM jcgkzx_monitor.wcnr_alert GROUP BY alert_type;": [

]}
