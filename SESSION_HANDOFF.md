# Session Handoff

> 用途：切换电脑前快速记录当前项目状态，保证下一台电脑可以直接继续。

## Current Status

- Date: 2026-03-26
- Device: current machine before switching
- Branch: `codex/face-identity-integration`
- Latest feature commit before this handoff refresh: `5f7116a`
- Workspace path: `C:\Users\So\Desktop\project\multi-rider-repo`

## What Was Finished

- `Train` 已从 mockup 推进到真实首页页签，支持真实数据集创建。
- 已完成 ZIP 导入到数据集的第一版能力：
  - 图片解压到 `datasets/<dataset_id>/images/`
  - 图片元数据写入 SQLite `dataset_assets`
  - 数据集统计和“最近导入”缩略图预览联动更新
- [templates/index.html](C:/Users/So/Desktop/project/multi-rider-repo/templates/index.html) 里的大段业务 JS 已抽离到 [static/js/index-page.js](C:/Users/So/Desktop/project/multi-rider-repo/static/js/index-page.js)，模板现在只保留服务端 bootstrap 配置和脚本引用。
- 本地已完成 Train 回归：
  - 页面可正常加载外链 JS
  - 可创建数据集
  - 可导入一个包含 2 张图片和 1 个非图片文件的 ZIP
  - 最近导入缩略图、图片数和图片链接都正常
  - smoke test 数据已清理

## What Was Changed

- Files touched in the current train phase:
  - `db/sqlite.py`
  - `routes/train_routes.py`
  - `service/dataset_service.py`
  - `templates/index.html`
  - `static/js/index-page.js`
  - `WORKLOG.md`
  - `SESSION_HANDOFF.md`
  - `HANDOFF_CHECKLIST.md`
- Key behavior changes:
  - `Train` 页现在有“创建数据集”和“导入 ZIP”两个真实入口
  - SQLite 新增 `dataset_assets` 表，记录数据集图片资产
  - 首页 JS 不再内嵌在模板中，后续继续维护首页逻辑时应优先改 `static/js/index-page.js`

## What Is In Progress

- Current task: 训练模块第一阶段继续落地
- Current step: 换电脑前补齐 handoff 文档并提交当前状态
- Current blocker:
  - Oracle 链路和内网人脸库链路仍需要在对应环境继续回归
  - `index-page.js` 已从模板中抽离，但还没有按 feature 再拆细

## What Still Needs To Be Done

1. 实现“历史结果加入数据集”，把已有 Oracle / Upload 检测结果回流到 `Train`
2. 在数据集里继续补图片浏览、标注和复核入口
3. 再往后接训练任务、版本管理和模型发布
4. 如首页继续演进，把 `static/js/index-page.js` 按 `job / upload / train / face` 再拆分

## Risks / Notes

- `jobs.sqlite3`、`datasets/`、`.venv/` 都是本地态，不会跟随 Git 走；换电脑后需要重新准备运行环境
- 当前本地 Flask 服务仍可以用 `.venv\Scripts\python.exe app.py` 在 `5001` 端口启动
- 这次重构主要影响首页模板和前端脚本组织方式；Train 功能 smoke test 已过，但 Oracle / Upload / Face 本轮没有做全回归
- 当前仓库已经移除了本仓库 Git 代理配置，不再依赖 `127.0.0.1:7890`

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
  - 浏览器打开首页后，外链 `static/js/index-page.js` 正常加载
  - `refreshTrainTab`、`createTrainDataset` 和 `PERSON_STATE` 在页面上下文中可访问
  - Train 页真实创建数据集成功
  - Train 页真实导入 ZIP 成功，导入结果为 `2` 张图片、`1` 项跳过
  - 数据集图片数、最近导入预览、图片访问链接都已验证
- Not tested:
  - Oracle 检测主流程未在这次 handoff 前重跑
  - Upload 检测主流程未在这次 handoff 前重跑
  - Face Library 的同步 / 重建 / 名录浏览未在这次 handoff 前重跑
- Known broken:
  - 没有发现新的明确坏点

## Next Direct Instruction For Codex

```text
先读取项目根目录的 SESSION_HANDOFF.md 和 WORKLOG.md，再继续训练模块。下一步优先做“历史结果加入数据集”，不要重复从 Train mockup 开始。
```

## History Notes

- 这次 handoff 的重点不是新增文档，而是把“Train 第一阶段已经真实做到哪一步”写清楚，让下一台电脑能直接继续开发。
