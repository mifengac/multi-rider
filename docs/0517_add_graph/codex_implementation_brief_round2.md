# Codex 第二轮任务书 — P0/P1/P2 补强

> 依据 `docs/0517_add_graph/design_graph_score_profile_dashboard.md` 第二轮缺口分析。
> 范围聚焦：**预警规则引擎、调度器、动态评分衰减、前端三页对接新接口、图谱关系边补全**。
> 仍然遵守首轮任务书的全局约束（KingBase 兼容 SQL、双引号 schema、`shared.db.kingbase.query_*`、`%(name)s` 占位、离线无新外部依赖）。

## 全局约束（追加）

- **不能新增第三方依赖**。`pyproject.toml` 不存在，`requirements.txt` 控制。调度器**只许用 Python 标准库 `threading` + `time`**，不引入 APScheduler / celery / schedule 等。
- 前端模板使用的 Tailwind class **必须复用现有页面里已用过的 token**（slate-*/blue-*/red-*/orange-*/yellow-*/green-* + 基础布局类）。如确实新增了未用过的 class，最后运行 `npm run build:css`。
- 现有 ECharts 已 vendor 在 `static/vendor/echarts.min.js`；**不要**引入 AntV G6 / Leaflet / 高德等。地图改用 ECharts 自带的 `scatter`+`visualMap` 在 jd/wd 坐标上渲染热力（无底图，靠 visualMap 颜色梯度），保持离线可用。
- 凡涉及未知表（如 `wcnr_visit`、`wcnr_alert` 之外的表），用 `query_one("SELECT 1 FROM information_schema.tables WHERE table_schema=%(s)s AND table_name=%(t)s", ...)` 探测，**缺失则降级跳过**该指标，不要让接口 500。
- 测试沿用现有 `tests/test_0517_add_graph_score_profile_dashboard.py` 风格（Flask test client + `monkeypatch.setattr(<module>, 'query_*', fake)`）。
- 蓝图已注册，新增路由加到对应 `routes.py` 即可。
- 提交粒度由 Claude 父进程统一负责，**codex 不要自行 git commit / push**。

---

## A. 后端补强

### A1. 预警规则引擎（§7.4）— 实现 3 条优先规则

新建 `modules/dashboard/services/alert_rule_engine.py`，定义纯函数：

1. `scan_high_risk_face_hit(window_minutes: int = 5) -> int`
   - 找近 `window_minutes` 分钟内 `jcgkzx_monitor.wcnr_ryrl_gj` 抓拍记录中，对应人员在 `wcnr_score.total_score >= 80` 者。
   - 对每条命中调用内部 `_insert_alert(...)` 写入 `jcgkzx_monitor.wcnr_alert`，字段：`zjhm, xm, alert_type='high_risk_face_hit', alert_level='critical', alert_content=<f"{xm} 在 {device_name} 出现">, location=device_name, trigger_time=shot_time`。
   - 同一人同设备 30 分钟内幂等去重：插入前 `SELECT 1` 查重。
2. `scan_night_aggregation() -> int`
   - 同一 `device_name`，时间窗 22:00–次日 06:00 之间，**3 人及以上**且其中 ≥2 人评分 ≥60，认为聚集预警，`alert_type='night_aggregation', alert_level='warning'`。
3. `scan_abnormal_hotel_checkin() -> int`
   - 近 24h `wcnr_ly_checkin` 中，入住人 `zjhm` 命中 `jcgkzx_monitor.wcnr_target_pool`（即在管控池）且 `tfrxm` 为空或同住人不是其监护人（监护人姓名取自 `b_per_qskjwcnr.jhr1xm` / 画像基础信息），生成 `alert_type='abnormal_hotel_checkin', alert_level='warning'`。

新增统一入口 `run_all_rules() -> dict`，返回 `{"high_risk_face_hit": n, "night_aggregation": n, "abnormal_hotel_checkin": n}`。

路由：`modules/dashboard/routes.py` 新增 `POST /api/dashboard/alerts/scan` → 同步执行 `run_all_rules()` 并返回结果。

### A2. 轻量调度器（§5.5）

新建 `shared/scheduler.py`：

- 暴露 `start_scheduler(app)` 与 `shutdown_scheduler()`。
- 内部用 `threading.Thread(daemon=True)` + `time.sleep` 循环，按 wall-clock 时间触发：
  - 每日 03:00 → `from modules.score.services.score_engine import batch_recalculate; batch_recalculate()`
  - 每月 1 号 04:00 → 新增的 `monthly_decay()`（见 A3）
  - 每 5 分钟 → `from modules.dashboard.services.alert_rule_engine import run_all_rules; run_all_rules()`
- 所有触发 try/except 包裹并打日志，**不能让线程因单次异常退出**。
- 提供环境变量开关 `WCNR_SCHEDULER_ENABLED`（默认 `"1"`）；测试/单元环境置 `"0"` 可关闭。
- 在 `app.py` 的 `create_app()` 末尾调用 `start_scheduler(app)`，仅当 `os.environ.get("WCNR_SCHEDULER_ENABLED", "1") == "1"` 时启动。
- pytest 收集时不应自动启动（通过 conftest 设置 env=0，或在调度器内部检测 `pytest` 模块已 import 时不启动；二选一即可）。

### A3. 月度评分衰减

`modules/score/services/score_engine.py` 新增：

```python
def monthly_decay(decrement: int = 2) -> dict:
    """Decay scores by `decrement` for all rows whose total_score > 0."""
    # UPDATE jcgkzx_monitor.wcnr_score
    #   SET total_score = GREATEST(total_score - %(d)s, 0),
    #       risk_level = ... (重算映射)
    # 用一次 UPDATE，再 SELECT 重算后的 total_score 范围回填 risk_level
    # 或直接 SQL 内 CASE 表达式映射
```

返回 `{"updated": n}`。SQL 用 KingBase/PostgreSQL 兼容写法。

### A4. 画像嵌入近 6 月评分趋势

`modules/profile/services/profile_assembler.py` 的 `assemble_profile` 返回字典追加 `"score_trend": [...]`，调用 `from modules.score.services.score_store import get_score_trend; get_score_trend(zjhm, 6)`。

### A5. 统计面板同比/环比

`modules/dashboard/services/summary_service.py` 的 `get_summary` 返回字典追加：

- `month_cases_prev`, `month_cases_change_pct`（与上月对比，pct 保留 1 位小数；上月为 0 时 pct 返 `null`）
- `high_risk_count_prev`, `high_risk_count_change_pct`（与 `wcnr_score_history` 月度快照比；若该历史表不存在则全部置 `null`，**用 information_schema 探测**）

### A6. 走访达标率（条件实现）

只有当 `jcgkzx_monitor.wcnr_visit`（或类似）表存在时，summary 才追加 `visit_total_month` 与 `visit_pass_rate`。**不存在则不加这两个字段**。

### A7. 图谱关系边补全 — LIVES_AT / SAME_SCHOOL / SAME_AREA

在 `modules/graph/services/relation_engine.py` 增加：

- `lives_at(zjhm)`：从 `jcgkzx_monitor.wcnr_czrk.hjdz`/`xzdxz` 取出地址，生成 `Location` 节点 + `LIVES_AT` 边。
- `same_school(zjhm, limit=5)`：先取本人 `yxx`（来自 `b_per_qscxwcnr` 或 `zq_zfba_wcnr_sfzxx`），再查同 `yxx` 的其他管控对象 LIMIT 5，生成 person-person `SAME_SCHOOL` 边。
- `same_area(zjhm, limit=5)`：用 `wcnr_target_pool.sspcs` 同派出所 → person-person `SAME_AREA` 边 LIMIT 5。

`modules/graph/services/graph_builder.py` 的 `build_person_graph` 新增可选关系名 `lives_at,same_school,same_area`，受 `relations` 过滤参数控制，默认不开启（避免节点爆炸）；当 `relations` 显式包含时启用。

---

## B. 前端补强

### B1. Dashboard — 热力图面板

`templates/modules/dashboard/dashboard.html`：在底排（年龄分布右侧或替换其中一格）新增 `<div id="chartHeatmap">` 容器，标题 "轨迹热力图"。

`static/modules/dashboard/dashboard.js`：新增 `loadHeatmap()` 拉 `/api/dashboard/heatmap?days=30`，用 ECharts `scatter` + `visualMap`（连续型）渲染：x=lng, y=lat, value=weight。x/y 轴隐藏刻度但保留比例。在 `loadXxx()` 队尾调用。

### B2. Dashboard — 顶部统计卡片增加同比/环比指示

`dashboard.js` 的 `loadSummary()` 拿到新字段 `*_change_pct` 时，在 stat-value 下渲染 `<div class="stat-change up/down">↑/↓ X.X%</div>`（CSS 已有 `.stat-change.up/down`）。null 时不渲染。

### B3. Graph — 3 层 / 关系筛选 / 时间范围

`templates/modules/graph/graph.html`：
- 把现有 `1 层/2 层` 按钮组扩到 `1/2/3 层`。
- 新增 "关系筛选" 下拉（multi-select 用 `<select multiple>` 或自实现 checkbox 弹层；多选项 `suspected_in,co_suspect,guardian_of,studies_at,appeared_at,checked_in,lives_at,same_school,same_area`，默认全选）。
- 新增 "时间范围" 下拉 `<select>`：`全部 / 近 1 月 / 近 3 月 / 近 6 月 / 近 1 年`，对应空/1m/3m/6m/1y。

`static/modules/graph/graph.js`：
- `loadGraph(zjhm)` 在 URL 中拼接 `depth/relations/time_range`。
- 类别 `categories` 与 `categoryMap` 追加 `location, organization`（颜色：地点 `#14b8a6`，机构 `#a855f7`），图例 legend 同步。
- 搜索结果是 case 时，点击应跳到 `/api/graph/case/<ajbh>` 渲染案件子图（新增 `loadCaseGraph(ajbh)`）；搜索结果是 location 时仅展示，不渲染。
- "展开关系" 按钮改用 `POST /api/graph/expand`，body `{node_id, node_type, direction:"both"}`，把返回的新增 nodes/edges 合并到本地 `graphData` 后 `renderGraph`（增量），不再整图重载。

### B4. Profile — 时间轴 / 评分趋势 / 团伙卡 / 头像

`static/modules/profile/profile.js`：

- `load()` 拿 profile 主数据后，**并行**再 fetch `/api/profile/${ZJHM}/timeline` 与 `/api/profile/${ZJHM}/photo`。
- 在右侧栏插入 "评分趋势"（6 月）卡：用 `chartScoreTrend` 容器，ECharts 折线图渲染 `d.score_trend`。
- 在 "关系网络" 卡内：当 `relations.gang && relations.gang.is_gang` 时，顶部加红底高亮提示 `<div class="badge-extreme">团伙关联 ${size} 人</div>`，下面列出成员姓名。
- 新增 "时间轴"（全宽）卡，渲染 timeline：每条用 `.timeline-item` 样式，title + time + type 标签（case/behavior/trajectory/hotel）。
- 头像：拿到 `/photo` 接口的 `zp` 字段时（base64 或 URL）替换 placeholder 圆形里的首字母为 `<img src="...">`；接口返回 null 时不替换。

### B5. Tailwind / CSS

如改了 class（多数情况下不需要，因为复用了既有 token），最后执行 `npm run build:css`；否则跳过。

---

## C. 测试与验收

- 为本轮新增逻辑追加测试到 `tests/test_0517_add_graph_score_profile_dashboard.py`：
  - 预警规则三函数：用 monkeypatch 假数据各跑通至少 1 个 happy path + 1 个去重/降级 case
  - `monthly_decay` SQL UPDATE 调用断言（用 fake `execute`）
  - dashboard summary 同比字段在 history 表缺失时返回 `null` 而非崩溃
  - graph relation_engine 三新关系函数 happy path
- 全部完成后：
  - `uv run pytest -q`（必须全过）
  - `uv run python -c "import app"`（必须 exit 0）
  - 仅当 Tailwind 新增了未用 class 才执行 `npm run build:css`

完成后用中文输出每个任务（A1–A7、B1–B5、C）对应**改动文件清单 + 验收结果**。

---

## 不做（明确排除）

- 不引入 APScheduler/celery/Leaflet/AntV G6/高德等新依赖。
- 不重写已通过的首轮 11 项实现。
- 不改 `app.py` 现有蓝图注册（只在 `create_app` 末尾加调度器启动一行）。
- 不大规模重排前端布局，只在现有卡片内追加内容或替换其中一格。
- 不动 `business_database.md`/`region_grouping.md` 记录的业务库连接配置。
