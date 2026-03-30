# Worklog

> 用途：记录项目推进过程，重点写“做了什么、为什么、下一步做什么”。

## Template

### YYYY-MM-DD HH:MM

- Device:
- Branch:
- Goal:
- Done:
  - 
- Files:
  - 
- Decision:
  - 
- Risk:
  - 
- Next:
  - 

---

## Entries

### 2026-03-30 10:40

- Device: current machine
- Branch: `main`
- Goal: 完成面向阅读的目录重构收尾，并把交接文档更新到当前仓库状态
- Done:
  - 将后端代码按业务域收拢到 `modules/`：`detection`、`face`、`dispatch`、`training`
  - 将共享能力收拢到 `shared/`：`config`、`db`、`inference`、`ownership`、`utils`
  - 将首页模板与前端脚本按模块迁移到 `templates/modules/`、`static/modules/`、`static/shared/`
  - 将说明文档、交接材料、部署文件分别整理到 `docs/`、`docs/handoff/`、`ops/`
  - 修正 `shared/config/config.py` 的根目录计算、环境变量加载路径和人脸 SQL 默认路径
  - 更新 `README.md`，补充代码导航和运行目录维护说明
  - 补充本轮重构摘要与 handoff，避免后续继续沿用 3 月 26 日的旧上下文
  - 调整 `.gitignore`，忽略本地 `.env` 与 `.mcp/` 工作区文件
- Files:
  - `app.py`
  - `README.md`
  - `.gitignore`
  - `modules/`
  - `shared/`
  - `templates/modules/`
  - `static/modules/`
  - `static/shared/`
  - `ops/`
  - `docs/handoff/SESSION_HANDOFF.md`
  - `docs/handoff/HANDOFF_CHECKLIST.md`
  - `docs/handoff/REFACTOR_SUMMARY.md`
- Decision:
  - 这次重构优先服务“看得懂、找得到”，而不是继续推严格插件化拆分
  - 保留现有 Flask Blueprint 和页面壳层，不在收尾阶段额外引入路由聚合器或前端构建工具
- Risk:
  - 本轮主要验证了应用可启动和模块导入链路，Oracle、真实人脸库、短信/下发平台仍需要业务环境回归
  - 当前工作区除本次重构外，还存在用户本地环境类文件，提交前仍应再看一次 `git status`
- Next:
  - 将本次重构按“结构迁移 / 文档收尾”整理为提交说明
  - 在真实内网环境回归检测、识别、下发、训练四条主链路

### 2026-03-30 11:15

- Device: current machine
- Branch: `main`
- Goal: 对目录重构后的入口与关键页面做一轮本地最小回归
- Done:
  - 配置并确认当前仓库 Python 环境为本地 `.venv`
  - 通过 `create_app()` 验证 Blueprint 仍注册为 `dispatch`、`face`、`file`、`job`、`train`、`upload`
  - 验证关键路由仍存在：`/`、`/history`、`/dispatch/queue`、`/face/library/status`、`/train/datasets`、`/train/model-registry-page`
  - 使用 Flask test client 验证首页、模型管理页、历史接口可返回 200
  - 使用 Flask test client 验证 `face/library/status`、`dispatch/auth/status`、`train/models` 三个 JSON 接口可返回 200
- Files:
  - `app.py`
  - `docs/handoff/SESSION_HANDOFF.md`
  - `docs/handoff/WORKLOG.md`
  - `docs/handoff/REGRESSION_CHECKLIST.md`
- Decision:
  - 先做“入口级 + 页面级 + 关键 JSON 接口”本地 smoke test，再进入真实内网联调
- Risk:
  - 当前验证仍未覆盖 Oracle、真实人脸库、短信平台和真实训练任务
- Next:
  - 在真实环境按 `REGRESSION_CHECKLIST.md` 回归 detection / face / dispatch / training 四条链路

### 2026-03-30 11:35

- Device: current machine
- Branch: `main`
- Goal: 对重构后的空态接口和缺参校验做一轮无副作用 API 合同测试
- Done:
  - 验证下列 GET 接口在空态下仍返回 200：
    - `/jobs`
    - `/history`
    - `/dispatch/queue`
    - `/train/datasets`
    - `/train/jobs`
    - `/train/auto-annotate-jobs`
    - `/face/library/persons`
  - 验证下列 POST 接口在缺少必要参数时仍返回 400，而不是结构迁移导致的 500：
    - `/upload/start`
    - `/train/jobs`
    - `/dispatch/preview`
    - `/dispatch/send`
    - `/dispatch/sms/send`
    - `/face/identify`
  - 额外确认 JSON 返回结构仍稳定：
    - `/dispatch/queue` 仍包含 `auth`、`defaults`、`history`、`items`
    - `/train/datasets` 仍包含 `items`、`summary`
- Files:
  - `docs/handoff/SESSION_HANDOFF.md`
  - `docs/handoff/WORKLOG.md`
  - `docs/handoff/REGRESSION_CHECKLIST.md`
- Decision:
  - 本地回归继续坚持“先测无副作用接口，再测会落库或调用外部依赖的接口”顺序
- Risk:
  - 当前仍未覆盖真实写入型接口，例如数据集创建、ZIP 导入、训练任务创建
- Next:
  - 如果继续本地回归，下一层应进入可控写入型测试，优先训练模块数据集与任务链路

### 2026-03-30 11:50

- Device: current machine
- Branch: `main`
- Goal: 在隔离临时目录中验证训练模块可控写入链路
- Done:
  - 通过环境变量把 `SQLITE_DB_PATH`、`DATASETS_DIR`、`TRAIN_RUNS_DIR`、`OUTPUT_DIR`、`UPLOAD_TEMP_DIR` 全部重定向到临时目录
  - 使用 Flask test client 成功创建数据集，返回 201
  - 成功导入内存构造的测试 ZIP，返回 200
  - 成功获取资产列表，确认导入后资产数为 1
  - 成功保存一条手工标注，返回 200，`is_labeled=True`
  - 成功把该资产复核状态改为 `confirmed`，返回 200
  - 成功读取数据集详情，确认计数为 `image_count=1`、`labeled_count=1`、`reviewed_count=1`
  - 测试结束后已删除临时目录，不污染当前仓库实际数据
- Files:
  - `docs/handoff/SESSION_HANDOFF.md`
  - `docs/handoff/WORKLOG.md`
  - `docs/handoff/REGRESSION_CHECKLIST.md`
- Decision:
  - 对会落库的接口，优先用环境变量重定向到隔离目录做本地回归，避免污染仓库内真实数据目录
- Risk:
  - 当前仍未覆盖真实训练任务创建与模型发布；这两步会引入实际训练线程和模型依赖，需单独安排
- Next:
  - 如果继续本地回归，下一步优先验证训练任务创建链路是否能在隔离目录下成功生成任务骨架

### 2026-03-30 12:05

- Device: current machine
- Branch: `main`
- Goal: 在隔离临时目录中验证训练任务骨架、报告接口和发布接口的空产物行为
- Done:
  - 通过 monkey patch 将训练线程替换为不执行的 fake thread，避免在本地回归中启动真实训练
  - 在隔离目录中成功完成“创建数据集 -> 导入 ZIP -> 保存标注 -> 创建训练任务”链路
  - 验证 `/train/jobs` 列表接口可返回新任务，且任务状态为 `queued`
  - 验证 `/train/jobs/<job_id>` 详情接口可返回新任务，状态为 `queued`
  - 验证 `/train/jobs/<job_id>/report` 在任务未真正训练时仍可返回 200 和稳定的报告结构
  - 验证 `/train/jobs/<job_id>/publish` 在没有 `best.pt` 产物时返回业务级 400，而不是结构错误
  - 已清理本轮训练任务 smoke test 产生的隔离临时目录
- Files:
  - `docs/handoff/SESSION_HANDOFF.md`
  - `docs/handoff/WORKLOG.md`
  - `docs/handoff/REGRESSION_CHECKLIST.md`
- Decision:
  - 对训练模块继续采用“先隔离目录、再 fake thread、最后测接口行为”的方式做本地回归
- Risk:
  - 当前仍未验证真实训练线程执行后的日志、artifact、best.pt、模型发布成功链路
- Next:
  - 如果继续本地回归，下一步应测试真实训练线程的最小可行跑通条件，或转去整理 staged 提交清单

### 2026-03-30 23:20

- Device: current machine
- Branch: `main`
- Goal: 在隔离临时目录中验证真实训练线程、训练报告和模型发布成功链路
- Done:
  - 首次实跑前定位出隔离脚本缺少 `init_db()` 的问题，确认这不是训练代码故障，而是测试初始化路径遗漏
  - 在隔离临时目录中成功完成“创建数据集 -> 导入 ZIP -> 保存标注 -> 启动真实训练任务”链路
  - 使用 `yolov8s-worldv2.pt` 以 `epochs=1/imgsz=64/batch=1` 成功跑完一次真实 Ultralytics 训练
  - 轮询确认训练任务状态从 `queued` 进入 `running`，最终进入 `done`
  - 验证训练产物落地成功：`best.pt`、`results.csv`、训练日志、报告摘要均已生成
  - 基于真实训练产物验证 `build_train_job_report()` 可读回报告、曲线图和历史指标
  - 基于真实训练产物验证 `publish_train_job_best()` 可成功复制模型并生成 `.meta.json`
  - 已删除发布测试生成的仓库内测试模型文件，并清理本轮隔离临时目录
- Files:
  - `modules/training/services/train_task_service.py`
  - `shared/db/sqlite.py`
  - `docs/handoff/SESSION_HANDOFF.md`
  - `docs/handoff/WORKLOG.md`
- Decision:
  - 训练模块本地深回归可以继续沿用“隔离目录 + `init_db()` 初始化 + 真训练最小参数”的方式执行，不需要污染仓库真实数据目录
- Risk:
  - 本轮真实训练仅验证了 CPU 下的最小数据集与最小 epoch，不代表真实业务数据规模下的训练耗时和指标表现
  - `publish_train_job_best()` 当前发布目标仍固定写入仓库 `model/` 目录，做自动化回归时需要自行清理测试模型
- Next:
  - 如果继续推进，本地工作重点应转向整理 staged 提交边界；业务回归重点则转向 Oracle / 人脸库 / 下发平台三条外部依赖链路

### 2026-03-25 22:45

- Device: office
- Branch: `codex/face-identity-integration`
- Goal: 完成训练模块第一阶段设计，并在换电脑前把交接文件落地
- Done:
  - 新增训练模块开发清单，明确 `YOLO26` 为主训练路线，`YOLO-World` 为预标注路线
  - 重建 `design-mockup.html`，加入 `Train` 页签原型
  - 删除 `yoloe-26n-seg.pt`、`yoloe-26s-seg.pt`
  - 新建 `docs/handoff/SESSION_HANDOFF.md`、`docs/handoff/WORKLOG.md`、`docs/handoff/HANDOFF_CHECKLIST.md`
  - 调整 `.gitignore`，避免把本地数据和离线大文件推上仓库
- Files:
  - `config.py`
  - `design-mockup.html`
  - `0325_train_module_checklist.md`
  - `0325_model_directory_strategy.md`
  - `.gitignore`
  - `docs/handoff/SESSION_HANDOFF.md`
  - `docs/handoff/WORKLOG.md`
  - `docs/handoff/HANDOFF_CHECKLIST.md`
- Decision:
  - 先不调整 `model/` 目录物理结构，先做文档规范和默认模型切换，避免打断现有运行链路
- Risk:
  - 训练模块当时还停留在设计态，没有真实前后端实现
- Next:
  - 下一台电脑接手后，优先落地 `Train` 页和数据集管理

### 2026-03-26 07:50

- Device: current machine
- Branch: `codex/face-identity-integration`
- Goal: 把训练模块从 mockup 推进到真实页面骨架
- Done:
  - 实现真实数据集创建
  - 实现 ZIP 导入
  - 新增 `dataset_assets` 落库
  - 把首页大段 JS 拆出模板
  - 首轮 smoke test 跑通
- Files:
  - `db/sqlite.py`
  - `routes/train_routes.py`
  - `service/dataset_service.py`
  - `templates/index.html`
  - `static/js/index-page.js`
- Decision:
  - 先解决首页模板过重问题，再继续做 Train 真实功能
- Risk:
  - Oracle / Face 模块这轮没有做完整回归
- Next:
  - 把历史结果回流到数据集，并补标注入口

### 2026-03-26 10:20

- Device: current machine
- Branch: `codex/face-identity-integration`
- Goal: 跑通训练模块主链路，让 `YOLO26` 能真实开始训练
- Done:
  - 把首页脚本继续拆成：
    - `dataset.js`
    - `training.js`
    - `annotation.js`
    - `results.js`
    - `face-library.js`
    - `bootstrap.js`
  - 补回第一版真实框标注交互
  - 补上标注效率功能：
    - 仅看未标注
    - 上一张 / 下一张未标注
    - 标注统计
  - 训练页增加真实表单和最近任务列表
  - 重写 `service/train_task_service.py`，训练任务改为真实调用 `yolo.exe detect train`
  - 定位 `YOLO26` 训练失败根因：
    - `ultralytics==8.3.226` 不支持当前 `yolo26*.pt`
  - 升级依赖到 `ultralytics==8.4.27`
  - 重新生成 `requirements.lock`
  - 补齐 `vendor/wheels/` 到新的锁文件版本
  - 真实 smoke test 跑通：
    - 创建数据集
    - 导入 `test/xp.jpg`
    - 保存 1 个框标注
    - 创建 `YOLO26n` 训练任务
    - `1 epoch` 训练成功完成
    - 生成 `best.pt / last.pt / results.csv / args.yaml`
  - 将 `train_runs/` 加入 `.gitignore`
- Files:
  - `.gitignore`
  - `requirements.txt`
  - `requirements.lock`
  - `app.py`
  - `db/sqlite.py`
  - `routes/train_routes.py`
  - `service/dataset_service.py`
  - `service/train_task_service.py`
  - `templates/index.html`
  - `templates/index/_train_tab.html`
  - `templates/index/_dataset_workspace_drawer.html`
  - `static/js/index-page/dataset.js`
  - `static/js/index-page/training.js`
  - `static/js/index-page/annotation.js`
  - `static/js/index-page/results.js`
  - `static/js/index-page/face-library.js`
  - `static/js/index-page/bootstrap.js`
  - `templates/history_detail.html`
  - `docs/handoff/SESSION_HANDOFF.md`
  - `docs/handoff/WORKLOG.md`
- Decision:
  - 训练基座先稳定在 `YOLO26n / YOLO26s`
  - 先证明“能真实起训练”，再补训练结果管理和模型发布
  - 离线 wheel 目录继续保留并同步维护
- Risk:
  - 当前 smoke test 只证明训练链路可跑通，不代表训练效果已经可靠
  - Oracle / 内网人脸库这轮仍未回归
  - 工作区仍有未提交改动
- Next:
  - 做训练结果管理页
  - 做模型发布到 `model/`
  - 再补标注效率功能和更多筛选能力
