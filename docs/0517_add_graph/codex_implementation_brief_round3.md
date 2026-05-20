# Codex 第三轮任务书 — 闭环演示与实时性补强

> 依据 `docs/0517_add_graph/design_graph_score_profile_dashboard.md` §4/§5/§7/§10/§12。
> 前两轮已落地：四模块 API、评分细则、调度器、预警三规则、前端三页核心。
> 本轮目标：把"宏观面板 → 个人画像 → 关系图谱 → 派发任务"演示闭环跑通，并补实时性与遗漏的图谱/预警细节。

## 全局约束（沿用前两轮）

- 禁止新增第三方依赖（SSE 用 Flask `Response` + `text/event-stream` stdlib 实现）。
- KingBase/PostgreSQL 兼容 SQL；未知表/字段必须 `information_schema` 探测后降级，不要 500。
- 前端复用现有 ECharts vendor 与既有 Tailwind token；如新增 class 才跑 `npm run build:css`。
- 测试沿用 `tests/test_0517_add_graph_score_profile_dashboard.py` 风格（monkeypatch + Flask test client）。
- 不要自行 git commit，不要重写已通过的前两轮实现。

---

## 任务

### T1. 图谱·全屏按钮（§4.4）

`templates/modules/graph/graph.html`：在头部右侧（深度按钮组之前/之后）加一个 `[全屏]` `<button class="control-btn">`。

`static/modules/graph/graph.js`：实现 `toggleFullscreen()`，对 `#graphCanvas` 容器调用 `requestFullscreen()`/`exitFullscreen()`，按钮文字在 `全屏 ↔ 退出全屏` 切换；进入/退出后调用 `chart.resize()`。

### T2. 图谱·案件节点双击 → 加载案件子图

`static/modules/graph/graph.js`：当前 `dblclick` 只处理 `person`。扩展为：`case` 节点 → 取 `properties.ajbh`，调用既有 `loadCaseGraph(ajbh)`。

### T3. 图谱·Case-case 串并案边（§4 设计「案件→案件 同类案由串并、时空关联」）

`modules/graph/services/graph_builder.py` 的 `build_case_graph` 内：

- 对中心 case，查同 `ajxx_ay`（案由）且 `ajxx_fasj` 落在 ±30 天窗口、`ajxx_cbdw_mc` 含相同辖区前缀（或同 `ssfj` 字段）的其他案件（LIMIT 10），添加节点（如尚未存在）与 `RELATED_CASE` 边（边色用浅紫 `#a78bfa`、虚线 `lineDash:[4,4]`）。
- 仅在 `depth>=1` 时启用（默认开启）；`depth=0` 跳过。
- 新增对应单元测试（monkeypatch query_all 返回两个 ay+fasj 接近的案件，断言生成 RELATED_CASE 边）。

### T4. §7.4 规则 5 — 学校周边 200m 高风险出没（条件实现）

新增 `modules/dashboard/services/alert_rule_engine.py` 的函数 `scan_school_perimeter(radius_m: int = 200) -> int`：

1. 用 `information_schema.columns` 探测 `ywdata.sh_fzxxsj_xx` 是否含有形如 `jd/wd/lng/lat/经度/纬度` 的列；列名命中则启用，**未命中直接 return 0** 并打日志。
2. 查询近 1 小时 `wcnr_ryrl_gj`（评分≥80 的人）每条轨迹点，对每所学校做 Haversine 距离判断（用 PostgreSQL 表达式 `2 * 6371000 * ASIN(SQRT(POWER(SIN(...),2)+COS(...)*COS(...)*POWER(SIN(...),2)))`），筛选 ≤ `radius_m` 命中。
3. 命中则 `_insert_alert(..., alert_type='school_perimeter_high_risk', alert_level='warning', alert_content=f"{xm} 出现在学校 {xxmc} 周边 ~{round(dist)}米")`，30 分钟去重沿用现有 helper。

`run_all_rules()` 追加该规则的统计。

### T5. §7.4 规则 4 — 飙车预警联动 detection（条件实现）

`modules/dashboard/services/alert_rule_engine.py` 增 `scan_speeding_detection() -> int`：

1. 探测 `modules/detection/repositories/ai_result_repository.py` 暴露的可调用接口（或读取其 SQLite 结果表），找近 5 分钟内带 "飙车/翘车头/炸街" 类别且 `confidence >= 0.6` 的结果。
2. 若结果中能解析出 `device_id`/`source_name` → 关联辖区，则生成 `alert_type='speeding_detected', alert_level='warning', alert_content=f"飙车检测命中 device={device_id}"`。
3. 找不到合适接口或表 → return 0 并日志，**绝不抛错**。

`run_all_rules()` 追加该规则。

### T6. §5.5 实时触发 — 增量评分扫描

`modules/score/services/score_engine.py` 增 `incremental_recalculate(window_minutes: int = 15) -> dict`：

1. 找近 `window_minutes` 分钟内有新案件（`zq_zfba_xyrxx` 入库时间不可靠，则用 `ajxx_fasj >= NOW() - interval`）或新行为（`t_wcnrxwjl_xx.wf_sj >= NOW() - interval`）的 zjhm 集合。
2. 与 `wcnr_score.calc_time` 比较，落后者调用 `calculate_score(zjhm)`。
3. 返回 `{"scanned": n, "recalculated": m}`。

`shared/scheduler.py` 追加每 10 分钟一次的 `incremental_recalculate(15)` 触发，沿用既有 try/except 与日志。

测试：monkeypatch query_all 给两个新案件 zjhm + 一个已有最新评分的 zjhm，断言只对前两个调用 calculate_score。

### T7. §10 SSE 实时预警推送

`modules/dashboard/routes.py` 新增 `GET /api/dashboard/alerts/stream`：

- 返回 `Response(generator, mimetype="text/event-stream")`。
- generator 内部用 `time.sleep(3)` 循环 fetch `get_recent_alerts(5)`，把**未推送过**的告警（按 `id` 维护游标）以 `data: <json>\n\n` 推送。
- 最长心跳 30 秒一次 `:\n\n`（注释帧），客户端断开通过抛 `GeneratorExit` 自然终止。
- 加 `Cache-Control: no-cache`、`X-Accel-Buffering: no` 响应头。

`static/modules/dashboard/dashboard.js`：在现有 `loadAlerts` 之外，初始化时启用 `new EventSource('/api/dashboard/alerts/stream')`：
- onmessage 把新告警 unshift 进 alert 列表（保持最长 15 条）。
- onerror 自动降级回原有 30s 轮询（断线时 `eventSource.close()` 并 fallback）。

测试：mock generator，断言响应 mimetype 为 `text/event-stream` 且首批数据可解析。

### T8. 演示闭环 — 派发任务跳转

仅做**前端跳转 + 后端轻封装**，不深改 dispatch 模块。

`static/modules/profile/profile.js`：在头部按钮栏（"展开图谱" 旁）追加 `<button>派发任务</button>`，点击 → 调用新增 `POST /api/dashboard/dispatch/from-person` body `{zjhm}`；后端返回 `{ok:true, redirect:"/dispatch"}` 后 `window.location.href = '/dispatch?zjhm=' + zjhm`。

`static/modules/dashboard/dashboard.js`：alert 列表每条尾部除 "详情" 链接外新增 "派发" `<button>`，同上跳转。

`modules/dashboard/routes.py` 新增 `POST /api/dashboard/dispatch/from-person`：
- 输入 `{zjhm}`；
- **不直接写 dispatch_queue**（避免与 `modules/dispatch` 内部模型耦合），只验证 zjhm 属于 wcnr_target_pool；
- 返回 `{ok:true, zjhm, redirect:"/dispatch?zjhm=" + zjhm}`；非法 zjhm 返 400。
- 留一行注释：`# TODO: 后续接入 dispatch.services.store_service.create_queue_item_from_wcnr`，作为接入点。

测试：监控 `POST /api/dashboard/dispatch/from-person`，validate 路径返回正确 redirect。

---

## 验收

- 新增/修改测试合入 `tests/test_0517_add_graph_score_profile_dashboard.py`。
- `uv run pytest -q` 全过；`uv run python -c "import app"` 退出 0。
- 仅当确实新增 Tailwind class 才 `npm run build:css`。
- 不要 git commit。完成后用中文逐项输出 T1–T8 的改动文件清单与验收结果。

## 明确不做

- 不重写 dispatch 模块内部数据模型/队列写入逻辑。
- 不引入 APScheduler/celery/WebSocket 库 / SSE 第三方库。
- 不调整 detection 模块路由；只读探测其结果表/接口。
- 不修改已通过的前两轮接口与评分细则。
