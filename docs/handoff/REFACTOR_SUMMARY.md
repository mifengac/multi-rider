# Structure Refactor Summary

> 用途：说明 2026-03-30 这一轮“阅读友好型重构”具体改了什么、为什么这样改、接下来怎么继续。

## Goal

- 目标不是做插件化架构，而是把“代码应该去哪里找”这件事变简单。
- 核心原则：按业务模块收拢代码，按共享能力集中基础设施，按用途整理文档与部署材料。

## New Top-Level Layout

- `modules/`
  - `detection/`：数据库检测、本地上传、结果下载与历史页
  - `face/`：人脸库、身份识别、旧识别流水线、SQL 资产
  - `dispatch/`：认证、队列、短信、任务下发
  - `training/`：数据集、预标注、训练任务、模型注册
- `shared/`
  - `config/`：配置与环境变量加载
  - `db/`：SQLite / Oracle
  - `inference/`：YOLO 推理共享入口
  - `ownership/`：会话归属判断
  - `utils/`：通用工具函数
- `templates/modules/`：按模块拆分的模板
- `static/modules/`：按模块拆分的前端脚本
- `static/shared/`：共享前端脚本
- `docs/`：笔记、交接、设计稿、辅助脚本
- `ops/`：部署与环境模板

## What Was Moved

### Detection

- 原 `routes/job_routes.py`、`routes/upload_routes.py`、`routes/file_routes.py`
  - 已迁移到 `modules/detection/`
- 原 `service/job_service.py`、`service/upload_job_service.py`、`service/result_store_service.py`
  - 已迁移到 `modules/detection/services/`
- 原 `templates/history.html`、`templates/history_detail.html`
  - 已迁移到 `templates/modules/detection/history/`
- 原首页相关模板和脚本
  - 已迁移到 `templates/modules/detection/`、`static/modules/detection/`

### Face

- 原 `routes/face_routes.py`
  - 已迁移到 `modules/face/routes.py`
- 原 `service/face_library_service.py`、`service/face_identity_service.py`、`service/face_library_task_service.py`
  - 已迁移到 `modules/face/services/`
- 原 `service/0312face_recognition_pipeline.py`
  - 已迁移到 `modules/face/legacy/`
- 原 `face_library.sql`
  - 已迁移到 `modules/face/sql/`

### Dispatch

- 原 `routes/dispatch_routes.py`
  - 已迁移到 `modules/dispatch/routes.py`
- 原 `service/dispatch_*`
  - 已迁移到 `modules/dispatch/services/`
- 原 `db/face_sql.py`
  - 已迁移到 `modules/dispatch/repository/face_sql.py`

### Training

- 原 `routes/train_routes.py`
  - 已迁移到 `modules/training/routes.py`
- 原 `service/dataset_service.py`、`service/train_task_service.py`、`service/auto_annotate*.py`、`service/model_registry_service.py`
  - 已迁移到 `modules/training/services/`
- 原训练相关页面和首页模板/脚本
  - 已迁移到 `templates/modules/training/`、`static/modules/training/`

### Shared

- 原 `config.py`
  - 已迁移到 `shared/config/config.py`
- 原 `db/sqlite.py`、`db/oracle.py`
  - 已迁移到 `shared/db/`
- 原 `service/infer_service.py`
  - 已迁移到 `shared/inference/infer_service.py`
- 原 `utils/helpers.py`、`utils/ownership.py`
  - 已迁移到 `shared/utils/`、`shared/ownership/`

### Docs / Ops

- 原根目录说明文档
  - 已迁移到 `docs/notes/`
- 原 handoff 文件
  - 已迁移到 `docs/handoff/`
- 原 `design-mockup.html`
  - 已迁移到 `docs/mockups/`
- 原辅助脚本
  - 已迁移到 `docs/tools/`
- 原 `Dockerfile`、`deploy/app.env.example`
  - 已迁移到 `ops/`

## Important Fixes During Migration

- 修正了 `shared/config/config.py` 中 `BASE_DIR` 的计算，避免迁移后路径仍指向错误目录。
- 环境变量加载位置已从旧部署目录调整为当前结构可识别的位置。
- 人脸 SQL 默认路径已切到 `modules/face/sql/face_library.sql`。
- `templates/index.html` 已改为引用新的模板 include 路径和新的静态脚本路径。
- `ops/Dockerfile` 已改为复制 `modules/`、`shared/`、`templates/`、`static/` 等新目录。

## What Was Verified

- Flask 应用可初始化。
- Blueprint 名称保持不变，现有 URL 前缀不需要随结构迁移而改变。
- 共享配置、Oracle、推理入口在新路径下可导入。
- `README.md` 已与新结构同步。

## Current Residual Risks

- 这轮主要做的是结构迁移和路径修正，不是完整业务联调。
- Oracle、真实人脸库、短信和任务平台依赖内网环境，仍需在真实环境回归。
- 当前工作区有本地 `.env` 与 `.mcp/` 文件，已经加入 `.gitignore`，但提交前仍建议手工确认一次状态。

## Recommended Commit Framing

如果要拆提交，建议按下面两段：

1. `refactor: regroup codebase into modules shared docs ops`
2. `docs: refresh README and handoff after structure refactor`

如果只做一段提交，建议：

1. `refactor: reorganize project structure for readability`

## Next Suggested Step

1. 在真实环境回归 detection / face / dispatch / training 四条主链路。
2. 回归完成后，再考虑是否继续把各模块内部做更细的二级目录整理。