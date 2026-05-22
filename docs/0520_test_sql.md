 ---
  一、关系图谱「未找到该人员的关系数据」根因

  入口卡点（graph_builder.py:212）：
  center = query_one(SELECT … FROM jcgkzx_monitor.wcnr_target_pool WHERE zjhm = %(zjhm)s)
  if not center:
      return {"nodes": [], "edges": []}    # ← 前端看到这个就提示"未找到"

  本地体检：你查的 445302200905041512 在本地 4 张表里全部 hits=0：

  ┌─────────────────────────────────┬────────┐
  │               表                │ 命中数 │
  ├─────────────────────────────────┼────────┤
  │ jcgkzx_monitor.wcnr_target_pool │ 0      │
  ├─────────────────────────────────┼────────┤
  │ ywdata.zq_zfba_xyrxx            │ 0      │
  ├─────────────────────────────────┼────────┤
  │ ywdata.b_per_qscxwcnr           │ 0      │
  ├─────────────────────────────────┼────────┤
  │ ywdata.zq_zfba_wcnr_sfzxx       │ 0      │
  └─────────────────────────────────┴────────┘

  结论：内网测试时这个 zjhm 不在 target_pool 中，不是依赖也不是 bug。可能性二选一：
  1. 内网 wcnr_target_pool 是空的（聚合层没跑过）
  2. 这个 zjhm 没被收入目标池

  内网验证 SQL（按顺序跑）：
  -- 1. target_pool 是否为空？
  SELECT COUNT(*) FROM jcgkzx_monitor.wcnr_target_pool;
  -- 2. 这个 zjhm 是否存在？
  SELECT zjhm, xm, ssfj FROM jcgkzx_monitor.wcnr_target_pool WHERE zjhm = '445302200905041512';
  -- 3. 取 3 个真实存在的 zjhm 用来测试
  SELECT zjhm, xm FROM jcgkzx_monitor.wcnr_target_pool LIMIT 3;

  关系图谱完整依赖表（按调用顺序）：

  ┌──────────────────┬──────────────────────────────────────────┬───────────────────────────────────────┐
  │       关系       │                    表                    │               关键字段                │
  ├──────────────────┼──────────────────────────────────────────┼───────────────────────────────────────┤
  │ 入口检索         │ jcgkzx_monitor.wcnr_target_pool          │ zjhm, xm                              │
  ├──────────────────┼──────────────────────────────────────────┼───────────────────────────────────────┤
  │ 评分着色         │ jcgkzx_monitor.wcnr_score                │ total_score, risk_level               │
  ├──────────────────┼──────────────────────────────────────────┼───────────────────────────────────────┤
  │ 涉案             │ ywdata.zq_zfba_xyrxx +                   │ xyrxx_sfzh, ajxx_join_ajxx_ajbh,      │
  │ SUSPECTED_IN     │ ywdata.zq_zfba_ajxx                      │ ajxx_ay                               │
  ├──────────────────┼──────────────────────────────────────────┼───────────────────────────────────────┤
  │ 同案 CO_SUSPECT  │ ywdata.zq_zfba_xyrxx (自关联)            │ 同上                                  │
  ├──────────────────┼──────────────────────────────────────────┼───────────────────────────────────────┤
  │ 监护 GUARDIAN_OF │ ywdata.zq_zfba_wcnr_sfzxx                │ sfzhm, jhr, lxdh                      │
  ├──────────────────┼──────────────────────────────────────────┼───────────────────────────────────────┤
  │ 就读 STUDIES_AT  │ ywdata.zq_zfba_wcnr_sfzxx                │ sfzhm, yxx                            │
  ├──────────────────┼──────────────────────────────────────────┼───────────────────────────────────────┤
  │ 出现 APPEARED_AT │ jcgkzx_monitor.wcnr_ryrl_gj              │ zjhm, device_name, jd, wd             │
  ├──────────────────┼──────────────────────────────────────────┼───────────────────────────────────────┤
  │ 入住 CHECKED_IN  │ jcgkzx_monitor.wcnr_ly_checkin           │ zjhm, jdmc, rzsj                      │
  └──────────────────┴──────────────────────────────────────────┴───────────────────────────────────────┘

  ---
  二、态势总览各组件不显示的根因（按组件逐一）

  ┌───────────────┬──────────────────────────────────────┬──────────────┬─────────────────────────────┐
  │     组件      │             依赖表/字段              │ 本地数据状态 │      不显示的可能原因       │
  ├───────────────┼──────────────────────────────────────┼──────────────┼─────────────────────────────┤
  │               │                                      │              │ SQL 强制要求嫌疑人 18       │
  │ 案件类型分布  │ ywdata.zq_zfba_ajxx 350 + xyrxx 990  │ 本地有数据   │ 岁以下（AGE(...) < 18），内 │
  │               │                                      │              │ 网若全是成年嫌疑人则为空    │
  ├───────────────┼──────────────────────────────────────┼──────────────┼─────────────────────────────┤
  │ 月度趋势      │ ywdata.zq_zfba_ajxx.ajxx_fasj        │ 本地 2025-11 │ 同上：含 18 岁未成年过滤    │
  │ cases         │                                      │ ~2026-05     │                             │
  ├───────────────┼──────────────────────────────────────┼──────────────┼─────────────────────────────┤
  │ 月度趋势      │ jcgkzx_monitor.wcnr_score_history.ca │ 本地仅       │ 历史快照只有 1 个月点 → 趋  │
  │ persons/score │ lc_time                              │ 2026-05-19   │ 势近乎一条线，肉眼像"没数据 │
  │               │                                      │ 当天 2163 条 │ "                           │
  ├───────────────┼──────────────────────────────────────┼──────────────┼─────────────────────────────┤
  │               │                                      │ 本地         │                             │
  │ 风险等级分布  │ jcgkzx_monitor.wcnr_score.risk_level │ risk_level   │ 评分引擎没回填 risk_level → │
  │               │                                      │ 全 NULL（677 │  分布为空                   │
  │               │                                      │ /677）       │                             │
  ├───────────────┼──────────────────────────────────────┼──────────────┼─────────────────────────────┤
  │ 辖区排名（ris │                                      │ 本地 ssfj 全 │ target_pool 聚合时没填      │
  │ k）           │ wcnr_target_pool.ssfj + wcnr_score   │  NULL（0/677 │ ssfj/ssfjdm → 排名为空      │
  │               │                                      │ ）           │                             │
  ├───────────────┼──────────────────────────────────────┼──────────────┼─────────────────────────────┤
  │ 辖区排名（cas │ ywdata.zq_zfba_ajxx.ajxx_cbdw_mc     │ 本地应有     │ 需查内网                    │
  │ e）           │                                      │              │                             │
  ├───────────────┼──────────────────────────────────────┼──────────────┼─────────────────────────────┤
  │ 实时预警      │ jcgkzx_monitor.wcnr_alert            │ 本地 0 条    │ 告警表为空 →                │
  │               │                                      │              │ 需调度器/手动扫描产生告警   │
  ├───────────────┼──────────────────────────────────────┼──────────────┼─────────────────────────────┤
  │ 年龄分布      │ wcnr_target_pool.csrq                │ 本地 168/677 │ csrq 缺失 75% → 显示偏少    │
  │               │                                      │  有值        │                             │
  ├───────────────┼──────────────────────────────────────┼──────────────┼─────────────────────────────┤
  │               │                                      │ 本地近 30 天 │ 应能显示；内网若 shot_time  │
  │ 轨迹热力图    │ wcnr_ryrl_gj.shot_time, jd, wd       │  3010        │ 旧 / jd/wd 缺失则空         │
  │               │                                      │ 条且全有坐标 │                             │
  └───────────────┴──────────────────────────────────────┴──────────────┴─────────────────────────────┘

  ---
  三、内网一键自检 SQL（直接复制到 KingBase）

  -- 【A】关键表存量
  SELECT 'wcnr_target_pool' AS tbl, COUNT(*) AS rows FROM jcgkzx_monitor.wcnr_target_pool
  UNION ALL SELECT 'wcnr_score', COUNT(*) FROM jcgkzx_monitor.wcnr_score
  UNION ALL SELECT 'wcnr_alert', COUNT(*) FROM jcgkzx_monitor.wcnr_alert
  UNION ALL SELECT 'wcnr_ryrl_gj', COUNT(*) FROM jcgkzx_monitor.wcnr_ryrl_gj
  UNION ALL SELECT 'wcnr_score_history', COUNT(*) FROM jcgkzx_monitor.wcnr_score_history
  UNION ALL SELECT 'wcnr_ly_checkin', COUNT(*) FROM jcgkzx_monitor.wcnr_ly_checkin
  UNION ALL SELECT 'zq_zfba_ajxx', COUNT(*) FROM ywdata.zq_zfba_ajxx
  UNION ALL SELECT 'zq_zfba_xyrxx', COUNT(*) FROM ywdata.zq_zfba_xyrxx
  UNION ALL SELECT 'zq_zfba_wcnr_sfzxx', COUNT(*) FROM ywdata.zq_zfba_wcnr_sfzxx;

  -- 【B】关键字段空值情况（target_pool）
  SELECT COUNT(*) FILTER (WHERE ssfj IS NOT NULL) AS with_ssfj,
         COUNT(*) FILTER (WHERE csrq IS NOT NULL) AS with_csrq,
         COUNT(*) AS total
  FROM jcgkzx_monitor.wcnr_target_pool;

  -- 【C】risk_level 是否回填（评分引擎是否跑过）
  SELECT COUNT(*) FILTER (WHERE risk_level IS NOT NULL) AS with_risk,
         COUNT(*) AS total
  FROM jcgkzx_monitor.wcnr_score;

  -- 【D】案件 fasj/嫌疑人年龄情况
  SELECT MIN(ajxx_fasj)::text AS min_fasj, MAX(ajxx_fasj)::text AS max_fasj,
         COUNT(*) AS total_cases
  FROM ywdata.zq_zfba_ajxx;

  -- 【E】轨迹时间/坐标
  SELECT MIN(shot_time)::text AS min_t, MAX(shot_time)::text AS max_t,
         COUNT(*) FILTER (WHERE jd IS NOT NULL AND wd IS NOT NULL) AS with_coord,
  FROM jcgkzx_monitor.wcnr_ryrl_gj
  FROM jcgkzx_monitor.wcnr_ryrl_gj
  WHERE shot_time >= CURRENT_TIMESTAMP - INTERVAL '30 days';

  四、若内网数据都在，仍空白时的诊断动作

  1. 风险等级分布空 → 调一次评分回填：
  curl -X POST http://<host>/api/score/batch  # 或 import + monthly_decay 触发
  2. 实时预警空 → 手动触发告警扫描：
  SELECT COUNT(*) FILTER (WHERE ssfj IS NOT NULL) AS with_ssfj,
         COUNT(*) FILTER (WHERE csrq IS NOT NULL) AS with_csrq,
         COUNT(*) AS total
  FROM jcgkzx_monitor.wcnr_target_pool;

  -- 【C】risk_level 是否回填（评分引擎是否跑过）
  SELECT COUNT(*) FILTER (WHERE risk_level IS NOT NULL) AS with_risk,
         COUNT(*) AS total
  FROM jcgkzx_monitor.wcnr_score;

  -- 【D】案件 fasj/嫌疑人年龄情况
  SELECT MIN(ajxx_fasj)::text AS min_fasj, MAX(ajxx_fasj)::text AS max_fasj,
         COUNT(*) AS total_cases
  FROM ywdata.zq_zfba_ajxx;

  -- 【E】轨迹时间/坐标
  SELECT MIN(shot_time)::text AS min_t, MAX(shot_time)::text AS max_t,
         COUNT(*) FILTER (WHERE jd IS NOT NULL AND wd IS NOT NULL) AS with_coord,
         COUNT(*) AS total
  FROM jcgkzx_monitor.wcnr_ryrl_gj
  WHERE shot_time >= CURRENT_TIMESTAMP - INTERVAL '30 days';

  -- 【F】告警表回填（触发扫描后看是否有新增）
  SELECT alert_type, COUNT(*) FROM jcgkzx_monitor.wcnr_alert GROUP BY alert_type;

  ---
  四、若内网数据都在，仍空白时的诊断动作
  四、若内网数据都在，仍空白时的诊断动作

  1. 风险等级分布空 → 调一次评分回填：
  curl -X POST http://<host>/api/score/batch  # 或 import + monthly_decay 触发
  2. 实时预警空 → 手动触发告警扫描：
  curl -X POST http://<host>/api/dashboard/alerts/scan
  3. 看后端日志 / 浏览器 F12 Network：
    - 看 /api/dashboard/summary、/distribution?dim=risk_level、/heatmap?days=30 是否 200 但 items=[]
    - 看是否 500 → 抓 traceback 给我

  需要我现在改哪个？两个选项：
  - A：把 build_person_graph 入口放宽 —— target_pool 未命中时也尝试从 ywdata.zq_zfba_xyrxx
  反查并展示"涉案信息"子图（避免一刀切返回空）
  - B：先等你内网跑完上面 6 个 SQL 把结果发我，根据真实数据再修