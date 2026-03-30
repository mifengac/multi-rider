# Session Handoff

> 用途：切换电脑前，快速记录当前项目状态，保证下一台电脑可以直接继续。

## Current Status

- Date: 2026-03-30
- Device: current machine
- Branch: `main`
- Latest committed revision: `8a7e174`
- Workspace path: `C:\Users\So\Desktop\project\multi-rider-repo`

## What Was Finished

- 已完成一轮“阅读友好型”目录重构，当前代码入口和职责分布已明显收拢。
- 后端业务代码已按模块迁移到：
  - `modules/detection/`
  - `modules/face/`
  - `modules/dispatch/`
  - `modules/training/`
- 共享基础设施已迁移到：
  - `shared/config/`
  - `shared/db/`
  - `shared/inference/`
  - `shared/ownership/`
  - `shared/utils/`
- 前端模板和脚本已按模块迁移到：
  - `templates/modules/`
  - `static/modules/`
  - `static/shared/`
- 文档和部署材料已迁移到：
  - `docs/notes/`
  - `docs/handoff/`
  - `docs/mockups/`
  - `docs/tools/`
  - `ops/`
- `README.md` 已更新为新目录结构，并补充“代码导航”“运行目录维护”说明。
- 旧的 `routes/`、`service/`、`db/`、`utils/` 目录已从仓库主结构中退出。

## What Was Changed

- 本轮核心文件：
  - `app.py`
  - `README.md`
  - `.gitignore`
  - `shared/config/config.py`
  - `shared/db/sqlite.py`
  - `shared/db/oracle.py`
  - `shared/inference/infer_service.py`
  - `modules/detection/`
  - `modules/face/`
  - `modules/dispatch/`
  - `modules/training/`
  - `templates/index.html`
  - `templates/modules/`
  - `static/modules/`
  - `static/shared/`
  - `ops/Dockerfile`
  - `ops/app.env.example`
  - `docs/handoff/REFACTOR_SUMMARY.md`

## What Is In Progress

- Current task: 结构重构后的回归与提交收口
- Current step: 本地结构回归与训练链路深回归已基本完成，当前重点是整理提交边界并转向外部依赖链路回归
- Current blocker:
  - Oracle 检测、真实人脸库、短信/下发平台依赖内网环境，当前只能完成结构层与导入层验证
  - 工作区存在与本次重构无关的本地环境文件，提交前需要再次筛选

## What Still Needs To Be Done

1. 按业务链路做回归：
   - 数据库检测
   - 本地上传检测
   - 人脸库同步与身份识别
   - 下发与短信
  - 训练页面联调与模型槽位切换
2. 规划提交边界：
   - 结构迁移
   - README / handoff 文档更新
   - `.gitignore` 清理
3. 如需继续演进：
   - 在各模块内部继续做更细的二级拆分
   - 为关键路径补更明确的 smoke test 脚本

## Risks / Notes

- 当前 Flask 入口仍是 `app.py`，启动方式未变：`.venv\Scripts\python.exe app.py`。
- `output/`、`upload_tmp/`、`logs/`、`train_runs/` 是运行产物目录；`datasets/`、`jobs.sqlite3` 属于业务数据，不应当作缓存直接清空。
- 当前已把 `.env`、`.mcp/` 加入 `.gitignore`，但本地若已有敏感值，仍不要手工 `git add -f`。
- 本轮验证重点已扩展到：应用可导入、蓝图可注册、训练模块写入链路、真实训练、真实报告和真实发布成功链路；但仍不是完整业务联调。

## Commands To Resume

```powershell
git pull
git branch --show-current
git log --oneline -5
git status
.venv\Scripts\python.exe app.py
```

## Verification Status

- Tested:
  - `create_app()` 可正常初始化
  - Blueprint 仍能注册 `dispatch`、`face`、`file`、`job`、`train`、`upload`
  - `shared/config/config.py` 的 `BASE_DIR` 指向仓库根目录
  - 共享 Oracle / inference 模块可从新路径导入
  - 首页模板 `templates/index.html` 已切换到新的模板与静态资源路径
  - 本地最小页面回归通过：`/`、`/train/model-registry-page`、`/history`
  - 本地最小接口回归通过：`/face/library/status`、`/dispatch/auth/status`、`/train/models`
  - 本地空态 GET 接口回归通过：`/jobs`、`/history`、`/dispatch/queue`、`/train/datasets`、`/train/jobs`、`/train/auto-annotate-jobs`、`/face/library/persons`
  - 本地缺参 POST 校验回归通过：`/upload/start`、`/train/jobs`、`/dispatch/preview`、`/dispatch/send`、`/dispatch/sms/send`、`/face/identify` 都返回了预期的 400
  - JSON 结构抽查通过：`/dispatch/queue` 仍返回 `auth/defaults/history/items`，`/train/datasets` 仍返回 `items/summary`
  - 训练模块隔离写入链路回归通过：在临时目录中成功完成“创建数据集 -> 导入 ZIP -> 列资产 -> 保存标注 -> 更新复核状态 -> 读取详情”，最终计数为 `1/1/1`
  - 训练任务骨架回归通过：在隔离目录 + fake thread 下，`/train/jobs` 创建成功并可被列表与详情接口读回，状态保持 `queued`
  - 训练任务报告空产物行为回归通过：`/train/jobs/<job_id>/report` 返回 200，`/train/jobs/<job_id>/publish` 在没有产物时返回业务级 400
  - 训练模块真实训练回归通过：在隔离目录 + `init_db()` 初始化下，`yolov8s-worldv2.pt` 以 `1 epoch` 成功完成 CPU 训练，任务状态进入 `done`，并生成 `best.pt`、`results.csv`、训练日志和报告摘要
  - 训练模块真实发布回归通过：基于真实训练产物成功执行 `publish_train_job_best()`，模型复制和 `.meta.json` 生成成功，验证后已清理测试模型文件
- Not tested:
  - Oracle 检测主流程
  - 内网人脸库同步 / 重建 / 识别联调
  - 短信与任务平台真实下发
  - 训练页面 UI 与模型槽位切换在真实业务数据上的联调
- Known broken:
  - 当前没有确认的结构性坏点
  - `templates/index.html` 中的 Jinja 内嵌脚本片段可能继续触发编辑器假阳性提示

## Next Direct Instruction For Codex

```text
先读取 docs/handoff/REFACTOR_SUMMARY.md、docs/handoff/REGRESSION_CHECKLIST.md、docs/handoff/COMMIT_SPLIT_GUIDE.md、docs/handoff/SESSION_HANDOFF.md 和 docs/handoff/WORKLOG.md。
优先按 COMMIT_SPLIT_GUIDE 清理提交边界，然后把 REGRESSION_CHECKLIST 的重点放到 detection / face / dispatch 三条外部依赖链路，以及 training 的页面联调与模型槽位切换，不要再按旧的 routes/service/db/utils 目录寻找代码。
```
