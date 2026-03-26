# 任务:现在改造当前系统,请你按照我的需求生成开发清单,写入multi-rider\0323_dev_list.md中,如有疑问或更好的意见则向我提出
## 1. 所有代码注释全部使用英文
## 2. 增加下拉列表可以选择模型"飙车炸街"和"通用"两个模型,"飙车炸街"对应"biaochezhajiev2.pt","通用"对应"yolov8s-worldv2.pt"("biaochezhajiev2.pt"我到时会放到目录中,现在暂时没有)
## 3. 当选择"飙车炸街"时SQL条件后面加个`AND 1=1`(方便我加其他条件),当选择"通用"模型时,使用原来的SQL
## 4. 选择"通用"模型时是用的"yolov8s-worldv2.pt"意味着可以根据提示词检测图片,你帮我设计下选择"通用"模型时"类别过滤"用什么方式检测图片好些
## 5.使用mcp工具figma优化前端页面

---

# 开发清单（2026-03-24）

> 背景：原有功能不变，在此基础上做两件事：
> 1. 代码拆分松耦合（Blueprint 架构）
> 2. SQLite 持久化任务状态 + 历史记录页面

---

## 目标目录结构

```
multi-rider/
├── app.py                  # 只保留 Flask 工厂函数 + Blueprint 注册 + main()
├── config.py               # 全部常量/环境变量
├── db/
│   ├── __init__.py
│   ├── oracle.py           # Oracle 连接、SQL 查询
│   └── sqlite.py           # SQLite 持久化（阶段二实现）
├── service/
│   ├── __init__.py
│   ├── infer_service.py    # 模型加载、图片下载、_predict_batch、ZIP 打包
│   └── job_service.py      # JOBS 字典、_new_job_record、_run_job、_summarize
├── routes/
│   ├── __init__.py
│   ├── job_routes.py       # /start /progress /cancel /jobs /history（Blueprint）
│   └── file_routes.py      # /download /summary（Blueprint）
└── utils/
    ├── __init__.py
    └── helpers.py          # sanitize_zip_name、parse_and_normalize_dt 等工具函数
```

---

## 阶段一：代码拆分（只重构，不改功能）

| # | 任务 | 说明 |
|---|---|---|
| 1.1 | 新建 `config.py` | 迁移所有 `os.getenv()`、`BASE_DIR`、`OUTPUT_DIR` 等常量 |
| 1.2 | 新建 `utils/helpers.py` | 迁移 `_sanitize_zip_name`、`_filename_from_url`、`_infer_ext_from_bytes`、`ensure_hours_list`、`parse_and_normalize_dt`、`default_time_range`、`to_datetime_local_str` |
| 1.3 | 新建 `db/oracle.py` | 迁移 `init_oracle_client_if_needed`、`get_oracle_connection`、`build_query_and_binds`、`fetch_image_urls` |
| 1.4 | 新建 `service/infer_service.py` | 迁移 `get_model`、`download_image_with_status`、`_predict_batch`、`requests.Session` |
| 1.5 | 新建 `service/job_service.py` | 迁移 `JOBS`、`JOBS_LOCK`、`_new_job_record`、`_summarize`、`_run_job`（含内部 `gen_downloads`） |
| 1.6 | 新建 `routes/job_routes.py` | 迁移 `/start`、`/progress/<job_id>`、`/cancel/<job_id>`、`/jobs`，注册为 Blueprint |
| 1.7 | 新建 `routes/file_routes.py` | 迁移 `/download/<job_id>`、`/download/<job_id>/<part>`、`/summary/<job_id>`，注册为 Blueprint |
| 1.8 | 改造 `app.py` | 只保留：创建 Flask app、注册两个 Blueprint、调用 `main()` |
| 1.9 | 新建各目录 `__init__.py` | `db/`、`service/`、`routes/`、`utils/` 各一个空文件 |
| 1.10 | **验证** | 启动服务，确认所有原有接口功能正常，无回归 |

---

## 阶段二：SQLite 持久化 + 历史记录

> 进度更新策略：**方案A** — 仅在任务完成/取消/出错时写一次 SQLite，进行中的进度仍查内存。

| # | 任务 | 说明 |
|---|---|---|
| 2.1 | 新建 `db/sqlite.py` | 实现以下函数 |
| | `init_db()` | 建表 `jobs`，字段见下方表结构 |
| | `save_job(job: dict)` | 任务结束时 INSERT 一条完整记录（仅在完成/取消/出错时调用一次） |
| | `get_job(job_id) → dict\|None` | 按 job_id 查询单条 |
| | `list_jobs(owner_ip, limit=50) → list` | 查询该 IP 的历史记录，按 start_ts 倒序 |
| | `cleanup_old_jobs(days=7)` | 删除 end_ts 超过 7 天的记录，同时删除 output/ 下对应 .zip 文件 |
| 2.2 | `db/sqlite.py` 表结构 | `id`、`status`、`message`、`total`、`processed`、`kept`、`notfound`、`failed`、`downloaded`、`start_ts`、`end_ts`、`owner_ip`、`conf_thresh`、`batch_size`、`imgsz`、`classes_raw`、`zip_paths_json`（JSON数组）、`summary_text` |
| 2.3 | 改造 `service/job_service.py` | `_run_job` 在 done/canceled/error 三处出口各调用 `sqlite.save_job()` |
| 2.4 | 改造 `app.py` 启动逻辑 | 启动时依次调用 `init_db()`、`cleanup_old_jobs(7)`；将 SQLite 中残留的 `running` 状态记录改为 `interrupted`（服务异常重启后避免误显示） |
| 2.5 | 改造 `routes/job_routes.py` | `/progress/<job_id>`：先查内存 `JOBS`，内存无记录时查 SQLite（支持重开浏览器后仍能查到已完成任务） |
| 2.6 | 改造 `routes/file_routes.py` | `/download/<job_id>`：内存找不到时从 SQLite 读取 `zip_paths_json`，再返回文件 |
| 2.7 | 新增 `GET /history` 接口 | 在 `routes/job_routes.py` 中实现，返回 JSON，字段：`id`、`start_ts`（格式化字符串）、`status`、`kept`、`total`、`zip_parts_count` |
| 2.8 | 新增 `GET /history-page` 接口 | 渲染 `history.html` 页面 |
| 2.9 | 新建 `templates/history.html` | 列表展示：任务时间 / 状态（颜色区分：done=绿、error=红、canceled=灰、interrupted=橙）/ 保留图片数/总数 / 下载按钮（复用 `/download/<job_id>`） |
| 2.10 | 改造 `templates/index.html` | 顶部添加"历史记录"入口链接，跳转到 `/history-page` |
| 2.11 | **验证** | 提交任务 → 关闭浏览器 → 重新打开 → 历史记录可见 → ZIP 可下载；重启服务后历史记录仍在；7天前的记录自动清理 |

---

## 关键约束备注

| 约束 | 处理方式 |
|---|---|
| `threading.Event` 不可序列化 | SQLite 只存可序列化字段，`cancel` 事件不入库 |
| 方案A：运行中不写库 | 进度查询优先查内存，内存无才查库（库里只有结束状态的记录） |
| ZIP 多分片路径 | 以 JSON 数组字符串存入 `zip_paths_json` 字段 |
| 7天过期清理 | 启动时执行，同步删除磁盘 `.zip` 文件，避免空间累积 |

---

# 开发清单（2026-03-24 补充）

> 新增需求：多模型切换 / YOLOE 提示词检测设计 / 注释英文化 / 前端优化

---

## 阶段三：多模型切换 + SQL 动态条件

### 3.1 后端：多模型支持

| # | 任务 | 说明 |
|---|---|---|
| 3.1.1 | 改造 `config.py` | 新增 `MODEL_REGISTRY` 字典：`{"bczj": "model/biaochezhajiev2.pt", "general": "model/yolov8s-worldv2.pt"}`；新增 `MODEL_DEFAULT = "general"` |
| 3.1.2 | 改造 `service/infer_service.py` | `get_model()` 改为 `get_model(model_key: str)`，按 key 加载对应文件；用字典缓存已加载的模型实例，避免重复加载 |
| 3.1.3 | 改造 `service/job_service.py` | `_run_job()` 新增参数 `model_key: str`；透传给 `get_model(model_key)` |
| 3.1.4 | 改造 `db/sqlite.py` 表结构 | `jobs` 表新增 `model_key` 字段（VARCHAR，默认 `'general'`） |
| 3.1.5 | 改造 `routes/job_routes.py` | `/start` 接收前端传来的 `model_key` 参数，校验合法性（只允许 `bczj` / `general`），传入 `_run_job` |

### 3.2 后端：SQL 动态条件

| # | 任务 | 说明 |
|---|---|---|
| 3.2.1 | 改造 `db/oracle.py` → `build_query_and_binds()` | 新增参数 `model_key: str`；当 `model_key == "bczj"` 时在 WHERE 末尾追加 `AND 1=1`；否则保持原 SQL 不变 |
| 3.2.2 | 改造 `db/oracle.py` → `fetch_image_urls()` | 透传 `model_key` 给 `build_query_and_binds()` |
| 3.2.3 | 改造 `routes/job_routes.py` → `/start` | 将 `model_key` 传给 `fetch_image_urls()` |

### 3.3 前端：模型选择下拉

| # | 任务 | 说明 |
|---|---|---|
| 3.3.1 | 改造 `templates/index.html` | 在表单中新增下拉框 `<select name="model_key">`，选项：`飙车炸街（bczj）` / `通用（general）` |
| 3.3.2 | 改造 `templates/index.html` JS | 监听下拉变化：选 `bczj` 时将"检测提示词"输入框隐藏并禁用；选 `general` 时显示并启用 |
| 3.3.3 | **验证** | 分别选两个模型提交任务，检查数据库查询语句和加载的模型是否对应正确 |

---

## 阶段四：YOLOE"通用"模型检测提示词设计

> **需求4设计方案说明**
>
> 原"类别过滤"字段对 YOLOE 无效（因为 `model.names` 返回的是数字索引而非类别名）。
> YOLOE 的正确使用方式是 `model.set_classes(["text", ...])` + 推理，完全基于文本提示。

### 方案设计

```
用户在"检测提示词"输入框中填写（英文，逗号分隔）：
  motorcycle, person, helmet, reflective vest

↓ 后端解析为列表传给 YOLOE：
  model.set_classes(["motorcycle", "person", "helmet", "reflective vest"])

↓ model.predict() 推理，置信度仍由"置信度阈值"控制

↓ 留空时：使用 YOLOE 无提示模式（内置 LVIS 1200+ 类别，自动检测所有物体）
```

| # | 任务 | 说明 |
|---|---|---|
| 4.1 | 改造 `service/infer_service.py` → `_predict_batch()` | 新增参数 `prompt_classes: list[str] \| None`；当 `model_key == "general"` 且 `prompt_classes` 非空时，推理前调用 `model.set_classes(prompt_classes)`；留空则跳过（无提示模式） |
| 4.2 | 改造 `service/job_service.py` → `_run_job()` | 当 `model_key == "general"` 时，将 `classes_raw` 按逗号分割为 `prompt_classes` 列表（去空格）；当 `model_key == "bczj"` 时，沿用原有数字索引过滤逻辑 |
| 4.3 | 改造 `templates/index.html` | 将"类别过滤"根据模型选择动态切换标签和 placeholder：`bczj` → 标签"类别过滤"，placeholder `0,1,2 或类别名`；`general` → 标签"检测提示词"，placeholder `motorcycle, person, helmet（留空=检测所有）` |
| 4.4 | 改造 `templates/index.html` | 在"通用"模式下，提示词输入框旁增加常用预设按钮（可选）：`摩托车`, `未戴头盔`, `人员` → 点击自动填入对应英文提示词 |
| 4.5 | **验证** | 选"通用"填写 `motorcycle, person` → 检查只保留含摩托车或人的图片；留空 → 检查所有有检出物体的图片均保留 |

---

## 阶段五：代码注释英文化

| # | 任务 | 说明 |
|---|---|---|
| 5.1 | 全量替换注释 | 将 `app.py`、`config.py`、`db/oracle.py`、`db/sqlite.py`、`service/infer_service.py`、`service/job_service.py`、`routes/job_routes.py`、`routes/file_routes.py`、`utils/helpers.py` 中所有中文注释改为英文 |
| 5.2 | 范围 | 仅包括代码注释（`#` 开头）和 docstring；不包括日志消息、错误提示文字（面向用户的中文保留） |

---

## 阶段六：前端界面优化

> **关于需求5（Figma MCP）**：当前运行环境中没有 Figma MCP 工具，无法直接调用。
> 替代方案：直接用 **Tailwind CSS** 重写前端，无需外部工具，效果更直接可控。

| # | 任务 | 说明 |
|---|---|---|
| 6.1 | 引入 Tailwind CSS 本地文件 | `tailwind.min.js` 已下载至 `static/tailwind.min.js`（✅ 已完成）；在模板 `<head>` 中引入：`<script src="{{ url_for('static', filename='tailwind.min.js') }}"></script>`，无需 CDN，内网可用 |
| 6.2 | 优化 `index.html` 布局 | 表单卡片式布局，字段分组（时间范围 / 模型与参数 / 高级设置）；模型下拉、提示词输入、置信度滑块横排对齐 |
| 6.3 | 进度条美化 | 用 Tailwind 实现动态进度条（宽度由 JS 控制），显示"已处理/总数"和"保留数" |
| 6.4 | 状态颜色统一 | running=蓝、done=绿、error=红、canceled=灰、interrupted=橙，与 `history.html` 保持一致 |
| 6.5 | `history.html` 样式 | 表格行悬停高亮，状态 badge，下载按钮统一样式 |
| 6.6 | **验证** | 在 Chrome / Edge 下检查响应式布局和交互效果 |

---

## 完整实现顺序建议

```
阶段一（拆分）→ 阶段五（注释英文化）→ 阶段二（SQLite）→ 阶段三（多模型）→ 阶段四（提示词）→ 阶段六（前端）
```

每个阶段完成后独立验证，避免多阶段同时改动导致难以定位问题。