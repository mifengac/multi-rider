# Codex 实施任务书 — 补齐 graph/score/profile/dashboard 未实现项

> 依据设计文档：`docs/0517_add_graph/design_graph_score_profile_dashboard.md`
> 目标：仅补齐下列**功能缺口**，不做大范围重构，不重写已实现且正确的代码。

## 全局约束（必须遵守）

1. **数据库访问**统一用 `from shared.db.kingbase import query_all, query_one`，psycopg2 占位符 `%(name)s`。
2. **Schema/表名**全部双引号 schema 限定。业务表在 `"ywdata"`，聚合/镜像层在 `"jcgkzx_monitor"`。
   - 人员池：`jcgkzx_monitor.wcnr_target_pool`(zjhm,xm,xb,csrq,ssfj,sspcs,source_type)
   - 评分：`jcgkzx_monitor.wcnr_score`(zjhm,total_score,risk_level,dim_*,calc_time)
   - 常住人口：`jcgkzx_monitor.wcnr_czrk`，照片：`jcgkzx_monitor.wcnr_rk_zp`
   - 轨迹：`jcgkzx_monitor.wcnr_ryrl_gj`(zjhm,device_name,shot_time,jd,wd,ssfj,sspcs)
   - 旅馆：`jcgkzx_monitor.wcnr_ly_checkin`(zjhm,lgmc,lgdz,rzsj,lksj,tfrxm,tfrzjhm)
   - 案件：`ywdata.zq_zfba_ajxx`，嫌疑人：`ywdata.zq_zfba_xyrxx`，受害人：`ywdata.zq_zfba_saryxx`
3. SQL 保持 **KingBase V8 / PostgreSQL 兼容**。离线环境，禁止引入新第三方依赖或外网调用。
4. 蓝图模式：路由加到各模块 `routes.py`，blueprint 已在 `app.py` 注册，无需改 `app.py`（新增 service 文件即可）。
5. 返回 JSON 适配 ECharts/AntV G6（沿用 `graph_builder.py` 的 nodes/edges 结构）。
6. 改动后运行 `pytest`；若改了模板的 Tailwind class 才需 `npm run build:css`。
7. 风格与现有 service 文件保持一致（类型注解、私有 `_xxx` 函数、`query_one`/`query_all`）。

---

## 任务 1 — 图谱：案件子图 `GET /api/graph/case/<ajbh>`

- 在 `modules/graph/services/graph_builder.py` 新增 `build_case_graph(ajbh: str, depth: int = 1) -> dict`：
  - 中心节点为 case 节点（复用 `_case_node`，数据取 `ywdata.zq_zfba_ajxx`）。
  - 关联该案 **嫌疑人**（`zq_zfba_xyrxx` where `ajxx_join_ajxx_ajbh=ajbh`）→ person 节点 + `SUSPECTED_IN` 边（带各人 `wcnr_score` 风险着色，复用 `_person_node` 逻辑）。
  - 关联 **受害人**（`zq_zfba_saryxx`，匹配 `ajxx_ajbhs` 含 ajbh）→ person 节点 + `VICTIM_OF` 边。
  - `depth>=2`：对每个嫌疑人调用现有 `_add_cases` 展开其他涉案，形成串并案视图。
- `modules/graph/routes.py` 新增路由 `GET /case/<ajbh>`（`depth` 参数，min 与 person 一致 cap 3），未找到返回 404 `{"error":"not_found"}`。

## 任务 2 — 图谱：节点扩展 `POST /api/graph/expand`

- `graph_builder.py` 新增 `expand_node(node_id: str, node_type: str, direction: str = "both") -> dict`：
  - person 节点：返回其案件/共犯/监护/学校增量子图（复用现有 `_add_*`）。
  - case 节点：返回该案嫌疑人/受害人增量。
  - 返回 `{"nodes":[...], "edges":[...]}` 仅含**新增**节点边，前端做合并。
- `routes.py` 新增 `POST /expand`，body `{node_id, node_type, direction}`，缺参返回 400。

## 任务 3 — 图谱：person 图过滤参数

- `build_person_graph(zjhm, depth, relations=None, time_range=None)`：
  - `relations`：逗号分隔，取值 `suspected_in,co_suspect,guardian_of,studies_at`（大小写不敏感）；为空=全部。按需跳过对应 `_add_*` 调用。
  - `time_range`：`1m|3m|6m|1y`，仅对 case 边按 `ajxx_fasj` 时间窗过滤（在 `_add_cases` 内加可选时间下限参数）。
- `routes.py` person 路由解析 `relations`、`time_range` 透传。保持向后兼容（不传=原行为）。

## 任务 4 — 图谱：search 支持 type + 地点

- `search_nodes(keyword: str, node_type: str | None = None)`：
  - `node_type` in `{person,case,location}` 时仅查对应类型；None=全部。
  - 新增 location 搜索：从 `jcgkzx_monitor.wcnr_ryrl_gj.device_name` DISTINCT 模糊匹配，返回 `{"id":device_name,"type":"location","label":device_name}`，LIMIT 10。
- `routes.py` search 路由解析 `type` 透传。

## 任务 5 — 图谱：relation_engine.py + Location/Organization 关系

- 新建 `modules/graph/services/relation_engine.py`，集中关系发现 helper（纯函数，输入 zjhm 返回边/邻居列表）：
  - `appeared_at(zjhm)`：取 `wcnr_ryrl_gj` 高频 device_name（按 §4.3 `APPEARED_AT`，Person→Location）。
  - `checked_in(zjhm)`：`wcnr_ly_checkin` → Organization(旅馆) 节点 + `CHECKED_IN` 边。
  - `victims_of_case(ajbh)`：供任务 1 复用。
- 在 `graph_builder.py` 增加 `_location_node`/`_organization_node` 样式（参考 §4.2 颜色：地点绿、机构），并在 `build_person_graph` 默认追加 APPEARED_AT(取前 3 高频点)与 CHECKED_IN，受 `relations` 过滤控制（新增可选关系名 `appeared_at,checked_in`）。

## 任务 6 — 评分：补 `/batch-recalculate` 别名

- `modules/score/routes.py`：新增 `@score_bp.route("/batch-recalculate", methods=["POST"])` 复用现有 `recalculate` 逻辑（保留旧 `/recalculate` 不删）。

## 任务 7 — 画像：时间轴 timeline

- 新建 `modules/profile/services/timeline_service.py`，`build_timeline(zjhm: str) -> list[dict]`：
  - 合并四类事件并按时间倒序：
    - 案件：`zq_zfba_ajxx` JOIN `zq_zfba_xyrxx`（time=ajxx_fasj, type=case）
    - 行为：`ywdata.t_wcnrxwjl_xx`（time=wf_sj, type=behavior, desc=wfxw_cn）
    - 轨迹：`jcgkzx_monitor.wcnr_ryrl_gj`（time=shot_time, type=trajectory, desc=device_name，LIMIT 50）
    - 入住：`jcgkzx_monitor.wcnr_ly_checkin`（time=rzsj, type=hotel, desc=lgmc）
  - 每条统一为 `{"time": ISO字符串, "type": ..., "title": ..., "detail": {...}}`，None 时间剔除。
- `modules/profile/routes.py` 新增 `GET /<zjhm>/timeline`。

## 任务 8 — 画像：团伙识别

- 在 `profile_assembler.py` 的 `assemble_profile` 的 `relations` 中新增 `gang`：
  - 若 `get_co_suspects` 结果中存在 ≥2 名共犯，且这些人之间也互为共犯（形成 ≥3 人团伙），则 `relations["gang"] = {"is_gang": True, "size": n, "members":[{zjhm,xm}...]}`，否则 `is_gang: False`。
  - 复用 `zq_zfba_xyrxx` 同案 JOIN 判断成员间互联，避免 N+1：可一次性查中心人 + 共犯集合的同案矩阵。

## 任务 9 — 面板：热力图 heatmap

- 新建 `modules/dashboard/services/heatmap_service.py`，`get_heatmap(days: int = 30) -> list[dict]`：
  - 聚合 `jcgkzx_monitor.wcnr_ryrl_gj` 近 `days` 天，按 `ROUND(jd,3),ROUND(wd,3)` 网格 GROUP BY，返回 `[{"lng":x,"lat":y,"weight":count}]`，过滤 jd/wd 为 NULL。
- `modules/dashboard/routes.py` 新增 `GET /heatmap`（`days` 参数，默认 30）。

## 任务 10 — 面板：ranking 支持 by/metric

- `modules/dashboard/services/distribution_service.py` 新增 `get_school_ranking()`（按画像/教育表 `yxx` 或 `b_per_qscxwcnr.yxx` 分组高风险人数）。
- `routes.py` 的 `/ranking`：解析 `by`(area|school) 与 `metric`(case_count|risk_count)；`by=area` 用现有 `get_area_distribution`，`by=school` 用新函数；返回 `{"by":...,"metric":...,"items":[...]}`，top 10。

## 任务 11 — models 数据模型包（按设计 §4.6/5.7/6.5/7.6）

- 为 graph/score/profile/dashboard 各建 `models/__init__.py` 与 `models/<m>_models.py`：
  - 用 `@dataclass` 定义节点/边/评分/画像/面板的轻量结构 + `to_dict()`，并在对应 service 中**可选**采用（不强制重写已有 dict 逻辑，至少提供类型定义供引用）。保持最小侵入。

---

## 验收

- 所有新增/修改路由可被 Flask 正常注册，`python -c "import app"` 不报错。
- `pytest` 通过（如无对应测试则不应破坏现有测试）。
- 不改变已通过的评分细则与既有正确接口的行为（向后兼容）。
- 不引入新依赖、不访问外网、SQL 保持 KingBase 兼容。
