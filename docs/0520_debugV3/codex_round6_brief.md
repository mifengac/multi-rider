# Round6 任务书：内网联调问题 + 诊断脚本 + Docker 模型包外置

## 背景

内网测试反馈三类问题（见 `docs/0520_debugV3.md` 原始记录）：

1. **关系图谱报错**：访问 `/api/graph/person/<zjhm>` 返回 500，错误为 `psycopg2.errors.UndefinedColumn: column "yxx" does not exist` (来自 `SELECT yxx FROM "ywdata"."b_per_qscxwcnr"`，定位到 `modules/graph/services/graph_builder.py:346` 的旧版本 `_add_school`)。
2. **态势总览全空**：案件类型分布、月度趋势、风险等级分布、辖区排名、实时预警、年龄分布、轨迹热力图全部无数据。
3. **诊断需求**：用户希望我们给出**可在内网执行的脚本**，把诊断结果发回给我们再继续定位。
4. **Docker 打包策略调整**：用户希望把 `model/` 目录搬到宿主机（与 `app.env`、`docker-compose.yml` 同级），启动时通过 volume 挂载，减小镜像体积、加快构建/分发。

---

## 硬约束

1. **不要新增第三方依赖**。
2. **不要执行 `git commit`**。
3. 修改 `Dockerfile` / `docker-compose.yml` / `.dockerignore` / `.env.example` 是允许的（因为 R4 就是要改打包策略）。
4. 完成后必须运行 `uv run pytest -q` 验证全部通过（基线 118 passed），运行 `uv run python -c "import app"` 验证 exit 0。
5. 完成后用中文逐项输出 R1-R4 的改动文件清单与验收结果，写入 `docs/0520_debugV3/codex_run_round6_last.txt`。

---

## R1：graph 模块 yxx 修复确认 & 边界加固

### 现状

`modules/graph/services/graph_builder.py` 的 `_add_school()` 在 commit `9a5bea4` 已经把对 `ywdata.b_per_qscxwcnr.yxx` 的旧查询删除，只保留 `ywdata.zq_zfba_wcnr_sfzxx.yxx`。但内网仍报这个错，说明**部署的镜像还是旧版本**。这部分需要我们做两件事：

### 做什么

1. **确认当前代码正确**：阅读 `modules/graph/services/graph_builder.py` 中 `_add_school`、`_add_guardian`、`_add_appeared_at`、`_add_checked_in` 等所有从 KingBase 查表的函数，把每条 SQL 用到的表/字段都列出来，对照 `docs/business/business_database.md` 检查是否存在；如果发现还有"列不存在"风险，**就地修复并补 fallback**（参考 R3 area 那种"先查主字段，空就 fallback"的写法）。
2. **加强容错**：所有 `_add_*` 函数里每条 `query_one/query_all` 调用必须用 `try/except` 包起来，捕获 `psycopg2.errors.UndefinedColumn`、`psycopg2.errors.UndefinedTable`、`Exception` 后 `logger.warning(...)` 一句，**不要让单个子查询失败把整个 person graph 拖垮**。`build_person_graph` 已经是组合调用，单点失败应该降级跳过那一类边/节点，不影响其他关系。
3. **测试**：在 `tests/test_0517_add_graph_score_profile_dashboard.py` 新增 1-2 个测试：mock `query_one` 抛出 `UndefinedColumn`，断言 `_add_school` 不抛异常、不增加节点；`build_person_graph` 整体返回结构正常（其他关系还能走通）。

### 验收

- `_add_*` 里所有 SQL 涉及的表/列都能在 `docs/business/business_database.md` 或 `docs/region/region_grouping.md` 里查到（如果某列文档没记录但代码用了，就在改动说明里标出来，让用户去确认）。
- pytest 新增用例通过。
- 单条查询失败不会让 `/api/graph/person/<zjhm>` 返回 500（最坏返回少边的 graph）。

---

## R2：态势总览空数据问题的"代码侧"加固

### 现状

我们怀疑空数据来自两方面：(a) 内网部署的还是旧镜像（不带 round5 的 fallback）；(b) 即使是 round5 镜像，可能还有些查询在内网数据下没命中（比如 risk_level 拼写、年龄/辖区 fallback 路径在内网真实数据上没覆盖到）。

### 做什么

1. **降级日志**：`distribution_service.get_area_distribution` / `get_age_distribution` / `summary_service._query_case_count_with_degrade` / `trend_service.get_case_trend` 在走 fallback 时各自 `logger.info("xxx fallback triggered, primary returned %d rows", ...)`，方便内网日志里直接看哪条路径在用。
2. **空响应自检**：在 `modules/dashboard/services/data_health_service.py` 的 `collect_health()` 里新增一个 `endpoint_probes` 字段，**逐个调用**：
   - `get_summary()`
   - `get_case_type_distribution()` / `get_risk_level_distribution()` / `get_area_distribution()` / `get_age_distribution()`
   - `get_case_trend(months=12)` / `get_person_trend(12)` / `get_score_trend(12)`
   - `get_school_ranking('risk_count')`
   - `get_heatmap(days=30)`
   - `get_recent_alerts(5)`
   
   每个 probe 输出 `{"name": "<func_name>", "ok": bool, "count": int_or_null, "sample": <头 1 条>, "error": "..."}`。这样一次 `/api/dashboard/data-health` 就能完整看到所有面板的"后端是不是真的有数据"。失败的 probe 不能让整接口挂掉，全部 try/except 包起来。
3. **测试**：mock `query_all/query_one` 返回 `[]`，断言 `data-health` 接口返回 200，`endpoint_probes` 里每项 `ok` 为 True 但 `count` 为 0；mock 抛异常时该 probe 的 `ok` 为 False 且 `error` 非空。

### 验收

- `curl http://127.0.0.1:5001/api/dashboard/data-health` 在本地能返回新的 `endpoint_probes` 字段，9 张表 + 11+ 个 probe。
- pytest 新增用例通过。

---

## R3：内网诊断脚本（一键发回数据用）

写一个独立脚本 `scripts/diagnostics/internal_dashboard_probe.py`，用户拷到内网执行，输出**单个 JSON 文件**让我们排查。脚本要求：

1. **入口**：`python scripts/diagnostics/internal_dashboard_probe.py [--base-url http://127.0.0.1:5001] [--zjhm 445381xxxxxxxx0415] [--out probe_<timestamp>.json]`。
2. **不引入新依赖**：用 `urllib.request`/`json`/`argparse`/`datetime` 标准库；DB 查询直接复用项目里的 `shared.db.kingbase.query_all/query_one`（脚本里 `import` 即可，前提是脚本通过 `python -m scripts.diagnostics.internal_dashboard_probe` 或者把 repo 根目录加到 `sys.path`）。
3. **三段输出**：
   - `meta`：当前时间、`git rev-parse HEAD`（用 subprocess 拿）、Python 版本、`MULTI_RIDER_IMAGE` env、`KINGBASE_*` env（只打印 host/db，不打印密码）。
   - `db_probes`：直接走 DB，对以下表/字段做 SELECT 并把结果塞进 JSON：
     * `wcnr_target_pool`：`COUNT(*)`、`COUNT(ssfj)`、`COUNT(csrq)`、`COUNT(DISTINCT ssfj)` 取前 5 个 sample（带行数）。
     * `wcnr_score`：`COUNT(*)`、`COUNT(*) WHERE total_score >= 60`、`COUNT(*) WHERE total_score >= 80`、`risk_level` 的分布。
     * `wcnr_alert`：`COUNT(*)`、按 `alert_type` 分组的 top10。
     * `wcnr_score_history`：`COUNT(*)`、`COUNT(DISTINCT DATE(calc_time))`、最近 3 个 distinct calc_time。
     * `wcnr_ryrl_gj`：`COUNT(*)`、`COUNT(*) WHERE shot_time >= now() - interval '30 days'`、最近 1 条 sample（脱敏：zjhm 中间用 `*`）。
     * `zq_zfba_ajxx`：`COUNT(*)`、`MIN/MAX(ajxx_fasj)`、按 `ajxx_ay` top 10、按 `ajxx_cbdw_mc` top 10。
     * `zq_zfba_xyrxx`：`COUNT(*)`、`COUNT(*) WHERE LENGTH(xyrxx_sfzh)=18`、年龄分布（基于 zjhm 解析）按 `<14`、`14-15`、`16-17`、`>=18` 分桶。
     * `zq_zfba_wcnr_sfzxx`：`COUNT(*)`、`COUNT(yxx IS NOT NULL)`、`yxx` top 10。
     * **可选**：`b_per_qscxwcnr` 是否存在（`information_schema.tables` 查），如果存在列出它的全部列名（这样能彻底确认 yxx 是不是真的没有）。
   - `api_probes`：用 `urllib.request` 调用部署的服务 base-url，逐个 GET：
     * `/api/health`、`/api/dashboard/data-health`
     * `/api/dashboard/summary`、`/api/dashboard/distribution?dim={case_type,risk_level,area,age,gender}`
     * `/api/dashboard/trend?metric={cases,persons,score}&months=12`
     * `/api/dashboard/ranking?by=area`、`/api/dashboard/heatmap?days=30`
     * `/api/dashboard/alerts?limit=5`
     * 若 `--zjhm` 指定：`/api/graph/person/<zjhm>?depth=1`
     
     每个 API 输出 `{"url": "...", "status": 200, "items_or_points_count": N, "first_item": {...}, "raw_size_bytes": M, "error": null}`。**超时 10 秒**，错误用字符串记录但不让脚本挂掉。
4. **输出**：默认写 `probe_<UTC时间戳>.json`（在脚本同目录或当前工作目录），中文打印一句"已生成 probe_xxx.json，请发回"。
5. **测试**：在 `tests/` 下新增 `test_internal_dashboard_probe.py`，用 monkeypatch 把 `query_all/query_one` 和 `urllib.request.urlopen` 全 mock 掉，断言脚本能跑完、JSON 三段都齐、写到 tmp_path。

### 验收

- 本地 `uv run python scripts/diagnostics/internal_dashboard_probe.py` 能跑通（API 调用大概率连不上，每个 probe 应该是 error 字符串而不是 raise）。
- pytest 新增用例通过。
- 脚本头部用中文注释写明：①使用方式；②输出位置；③把生成的 JSON 文件发回给开发即可。

---

## R4：Docker 模型目录外置可行性 & 实现

### 现状

- `model/` 目录现在被 `COPY . .` 整体打入镜像，每次构建/分发都拖大。
- `shared/config/config.py` 的 `MODEL_DIR` 已经是 `BASE_DIR/model`，但**没有走 env 变量**。
- `.env.example` 里 `MODEL_PATH*` 已经是绝对路径 `/app/model/xxx.pt`，跟容器内路径绑死。

### 做什么

1. **环境变量化**：把 `shared/config/config.py:8` 的 `MODEL_DIR` 改成可被 env 覆盖：
   ```python
   MODEL_DIR = os.environ.get("MODEL_DIR") or os.path.join(BASE_DIR, "model")
   ```
   其他 `MODEL_YOLO_DIR/MODEL_INSIGHTFACE_DIR/MODEL_ASSETS_DIR/DEPLOYMENT_SLOTS_PATH` 自动跟随。
2. **docker-compose 加挂载**：在 `docker-compose.yml` 的 `x-app-common.volumes:` 列表里新增一行：
   ```yaml
   - ${MULTI_RIDER_MODEL_ROOT:-./model}:/app/model
   ```
   `MULTI_RIDER_MODEL_ROOT` 默认 `./model`（即 compose 同级），允许用户在 `.env` 里改。
3. **`.dockerignore` 排除 model**：在末尾加：
   ```
   model/*
   !model/README.md
   ```
   保持 `model/README.md` 进镜像作占位，**但模型文件不再打包**。
4. **Dockerfile 加占位目录**：在 `COPY . .` 之后加一行 `RUN mkdir -p /app/model`，避免挂载点为空时容器启动找不到目录（其实 volume 挂载会自动创建，但显式建一下更稳）。
5. **`.env.example` 注释更新**：在 `MODEL_PATH=...` 那几行上方加中文注释，说明现在 `model/` 是宿主机目录，启动前请把模型文件放到 `${MULTI_RIDER_MODEL_ROOT}` 下；也补一个 `# MULTI_RIDER_MODEL_ROOT=./model` 注释行。
6. **写一份文档** `docs/0520_debugV3/docker_model_external.md`，包含：
   - 可行性分析（性能、安全、运维各方面影响）
   - 迁移步骤（从旧版镜像迁到新版的 5 步操作清单）
   - 回退方案（出问题怎么改回去）
   - 性能基准：现在镜像大小估算 vs 改造后估算（粗略数字即可，比如 model 目录 1.5GB vs 0）
7. **测试**：新增 `tests/test_model_dir_env.py`：用 monkeypatch 设置 `MODEL_DIR=/tmp/custom_model`，`importlib.reload(shared.config.config)`，断言 `MODEL_DIR == "/tmp/custom_model"`、`MODEL_YOLO_DIR.startswith("/tmp/custom_model")`。

### 验收

- `uv run python -c "import os; os.environ['MODEL_DIR']='/tmp/x'; import importlib, shared.config.config as c; importlib.reload(c); print(c.MODEL_DIR)"` 输出 `/tmp/x`。
- `docker-compose.yml` 的 volumes 列表里能看到 model 挂载行。
- `.dockerignore` 里 `model/*` 和 `!model/README.md` 都在。
- 文档 `docs/0520_debugV3/docker_model_external.md` 存在且包含上述四节。
- pytest 新增用例通过。
- 注意：**不需要真的构建/启动 docker**（用户的环境受限）；只需保证文件改对、测试过。

---

## 最终输出格式（写入 `docs/0520_debugV3/codex_run_round6_last.txt`）

沿用前几轮格式：

```
已按第六轮任务书完成 R1-R4，未执行 git commit。

| 任务 | 改动文件 | 验收 |
|---|---|---|
| R1 graph 容错 | modules/graph/services/graph_builder.py, tests/... | ... |
| R2 dashboard probe | modules/dashboard/services/data_health_service.py, tests/... | ... |
| R3 内网诊断脚本 | scripts/diagnostics/internal_dashboard_probe.py, tests/... | ... |
| R4 model 外置 | shared/config/config.py, docker-compose.yml, .dockerignore, Dockerfile, .env.example, docs/0520_debugV3/docker_model_external.md, tests/... | ... |

验收命令：
- `uv run pytest -q`：exit 0，X passed in Ys.
- `uv run python -c "import app"`：exit 0。

备注：...
```

请严格按这个任务书执行，分步完成。每个 R 完成后跑一次 pytest 看是否 regression，再做下一个。
