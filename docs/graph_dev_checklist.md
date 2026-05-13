# 刑智·护苗 — Neo4j知识图谱+团伙挖掘 开发清单

> 状态说明：⬜ 待开发 / 🔄 进行中 / ✅ 已完成  
> 触发条件：用户说"开始修改代码"后开始执行  
> 最后更新：2026-05-13

---

## 阶段一：基础设施接入（Prerequisites）

### 1.1 数据库建表
| # | 任务 | 文件 | 说明 | 状态 |
|---|------|------|------|------|
| 1 | 在KingBase执行建表SQL | `sql/01_create_hm_tables.sql` | 创建 `jcgkzx_monitor.hm_graph_sync_log` 和 `hm_gang_result` | ✅ |
| 2 | 在Neo4j执行初始化Cypher | `sql/02_neo4j_init.cypher` | 创建唯一约束和索引 | ✅ |

### 1.2 配置文件
| # | 任务 | 文件 | 改动内容 | 状态 |
|---|------|------|---------|------|
| 3 | 添加Neo4j配置变量 | `shared/config/config.py` | `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` | ✅ |
| 4 | 添加KingBase配置变量 | `shared/config/config.py` | `KINGBASE_HOST/PORT/DBNAME/USER/PASSWORD` | ✅ |
| 5 | 更新env示例文件 | `ops/app.env.example` | 追加Neo4j和KingBase的env变量示例 | ✅ |

### 1.3 数据库驱动模块
| # | 任务 | 文件 | 改动内容 | 状态 |
|---|------|------|---------|------|
| 6 | 新建KingBase连接模块 | `shared/db/kingbase.py` | psycopg2连接封装，`connect/fetch/execute` | ✅ |
| 7 | 新建Neo4j驱动模块 | `shared/db/neo4j_db.py` | neo4j-driver连接，`get_driver()` / `run_query()` 封装 | ✅ |
| 8 | 安装Python依赖 | `requirements.txt` | 添加 `neo4j>=5.20` / `psycopg2-binary>=2.9` / `networkx>=3.3` | ✅ |

---

## 阶段二：ETL数据管道（KingBase → Neo4j）

### 2.1 ETL核心服务
| # | 任务 | 文件 | 改动内容 | 状态 |
|---|------|------|---------|------|
| 9 | ETL主服务 | `modules/graph/services/etl_service.py` | 读KingBase、写Neo4j、写同步日志 | ✅ |
| 10 | 同步Person节点 | `etl_service.py` 中 `sync_persons()` | 来源：`zq_zfba_xyrxx` / `zq_zfba_wcnr_xyr`，按 `xyrxx_sfzh` 去重 | ✅ |
| 11 | 同步Case节点 | `etl_service.py` 中 `sync_cases()` | 来源：`zq_zfba_ajxx WHERE ajxx_aymc LIKE '%盗%'`，过滤盗窃类案件 | ✅ |
| 12 | 同步SAME_CASE关系 | `etl_service.py` 中 `sync_same_case_rels()` | 来源：`zq_zfba_xyrxx`，`xyrxx_sfzh → ajxx_join_ajxx_ajbh` | ✅ |
| 13 | 聚合CO_SUSPECT关系 | `etl_service.py` 中 `sync_co_suspect_rels()` | 同案两人之间建边，weight=共同涉案次数；按案件号分组聚合 | ✅ |
| 14 | 标记前科属性 | `etl_service.py` 中 `sync_prior_records()` | 来源：`b_per_dqqkrygj`，更新Person节点 `has_prior=true` | ✅ |
| 15 | 增量同步控制 | `etl_service.py` 中 `get_last_cursor()` | 读 `hm_graph_sync_log` 最新游标，支持增量更新 | ✅ |

### 2.2 ETL批量写入优化
| # | 任务 | 文件 | 说明 | 状态 |
|---|------|------|------|------|
| 16 | Cypher批量MERGE | `etl_service.py` | 用 `UNWIND $batch MERGE (p:Person {sfzh: row.sfzh})` 替代逐条写入，每批500条 | ✅ |
| 17 | ETL任务入队 | `shared/task_queue.py` | ETL通过现有SQLite任务队列触发，不阻塞HTTP请求 | ✅ |

---

## 阶段三：图算法服务

| # | 任务 | 文件 | 改动内容 | 状态 |
|---|------|------|---------|------|
| 18 | Louvain社区发现 | `modules/graph/services/algo_service.py` | 通过GDS插件调用：`gds.louvain.stream`；或用NetworkX作为备选 | ✅ |
| 19 | 介数中心度计算 | `algo_service.py` 中 `calc_betweenness()` | `gds.betweenness.stream`；识别团伙组织者 | ✅ |
| 20 | 链接预测 | `algo_service.py` 中 `predict_links()` | 用Common Neighbors预测潜在共犯关系 | ✅ |
| 21 | 结果写回KingBase | `algo_service.py` 中 `save_gang_results()` | 社区结果写入 `jcgkzx_monitor.hm_gang_result`，含团伙ID/成员/中心度 | ✅ |

---

## 阶段四：后端API

| # | 任务 | 文件 | 接口 | 状态 |
|---|------|------|------|------|
| 22 | 注册graph蓝图 | `app.py` | `from modules.graph import bp; app.register_blueprint(bp)` | ✅ |
| 23 | 蓝图初始化 | `modules/graph/__init__.py` | Flask Blueprint定义 | ✅ |
| 24 | 路由文件 | `modules/graph/routes.py` | 注册所有图谱相关路由 | ✅ |
| 25 | ETL触发接口 | `POST /api/graph/sync` | 触发ETL同步任务，返回task_id | ✅ |
| 26 | 同步状态查询 | `GET /api/graph/sync/status` | 查询最近一次同步状态和进度 | ✅ |
| 27 | 团伙挖掘触发 | `POST /api/graph/detect-gangs` | 触发Louvain算法，返回task_id | ✅ |
| 28 | 团伙列表接口 | `GET /api/graph/gangs` | 返回最新团伙列表（分页），含团伙规模/核心人员 | ✅ |
| 29 | 团伙详情接口 | `GET /api/graph/gangs/<gang_id>` | 返回团伙成员列表、关系边，供Cytoscape渲染 | ✅ |
| 30 | 人物关系图查询 | `GET /api/graph/person/<sfzh>` | 当前提供人物1跳关系图（人物+案件）JSON | ✅ |
| 31 | 轨迹按需查询 | `GET /api/graph/person/<sfzh>/trajectory` | 实时查KingBase `t_spy_ryrlgj_xx`，返回轨迹打点列表 | ✅ |

---

## 阶段五：前端页面

| # | 任务 | 文件 | 改动内容 | 状态 |
|---|------|------|---------|------|
| 32 | 图谱主页面（HTML） | `templates/modules/graph/index.html` | Cytoscape.js画布、侧边栏、搜索框，CDN引入 | ✅ |
| 33 | 图谱前端JS | `static/modules/graph/graph.js` | 初始化Cytoscape、加载数据、点击交互逻辑 | ✅ |
| 34 | 团伙列表组件 | `templates/modules/graph/index.html` | 右侧面板展示团伙列表，点击高亮对应节点 | ✅ |
| 35 | 轨迹展示组件 | `templates/modules/graph/index.html` | 点击人物节点，侧边展示摄像头轨迹时间线 | ✅ |
| 36 | 导航菜单添加入口 | `templates/index.html` 或主导航文件 | 添加"知识图谱"菜单项 | ✅ |

---

## 阶段六：Docker集成

| # | 任务 | 文件 | 改动内容 | 状态 |
|---|------|------|---------|------|
| 37 | compose文件接入Neo4j服务 | `compose.yaml`、`docker-compose.yml` | 已补 neo4j:5.20-community 服务、数据/日志/插件卷、应用依赖关系 | ✅ |
| 38 | 更新镜像依赖链 | `requirements.lock` 等 | 已补 Neo4j Python 驱动锁定版本；compose 与 env 示例、README、离线部署文档已同步 | ✅ |

---

## 阶段七：测试

| # | 任务 | 文件 | 说明 | 状态 |
|---|------|------|------|------|
| 39 | ETL单元测试 | `tests/test_graph_etl.py` | 测试sync_persons/sync_cases/sync_rels逻辑 | ✅ |
| 40 | API接口测试 | `tests/test_graph_routes.py` | 当前已覆盖关键路由入口，后续补全更多接口分支 | ✅ |
| 41 | 算法测试 | `tests/test_graph_algo.py` | 用小型mock图测试Louvain和介数中心度结果 | ✅ |

---

## 开发顺序建议

```
阶段一(1.2+1.3) → 阶段一(1.1,执行SQL) → 阶段二 → 阶段三 → 阶段四 → 阶段五 → 阶段六 → 阶段七
    ↑配置+驱动           ↑建表                ↑ETL      ↑算法     ↑API     ↑前端     ↑Docker   ↑测试
```

**最小可用版本（MVP）路径（任务编号）：**  
`3→4→5→6→7→8` → 执行SQL → `9→10→11→12→13` → `22→23→24→25→27→28→29→30` → `32→33`  
共约20个任务，可在2-3天内完成核心功能。

---

## 关键设计决策记录

| 决策 | 选项 | 结论 | 原因 |
|------|------|------|------|
| 视频云400万条是否入图谱 | 入图/不入图 | **不入图，按需查询** | 全量建共现边会产生千万级边，无实际意义 |
| 算法实现方式 | GDS插件/NetworkX | **优先GDS，备选NetworkX** | GDS在Neo4j内部运行，性能好；NetworkX无需插件 |
| ETL方式 | 实时同步/定时批量 | **定时批量+增量游标** | 业务数据不是实时流，批量更高效 |
| 新建表位置 | ywdata/jcgkzx_monitor | **jcgkzx_monitor，前缀hm_** | 与原有业务表（zq_/t_/b_前缀）明确区分 |
| Neo4j部署 | Windows原生/Docker | **Docker（neo4j-hm容器）** | 与生产环境保持一致，便于迁移 |

---

## 本轮实做与验证结果

- 已在本机执行 `sql/01_create_hm_tables.sql`，KingBase 中已创建 `jcgkzx_monitor.hm_graph_sync_log` 和 `hm_gang_result`
- 已在 `neo4j-hm` 容器中执行 `sql/02_neo4j_init.cypher`，约束和索引已初始化
- 已完成一次 `run_graph_sync(limit=10, theft_only=True)` 运行时验证，返回成功；当前本地源表为空，因此同步计数为0
- 已完成 `python -m pytest -q tests/test_graph_routes.py`，结果 `3 passed`
- 已完成 `compose.yaml` 和 `docker-compose.yml` 的 `docker compose config` 校验，Neo4j 服务编排合法
- 已补齐 `.env.example`、`ops/app.env.ubuntu.example`、`README.md`、`docs/OFFLINE_DEPLOY_CENTOS_STREAM10.md` 的 Neo4j 部署说明
