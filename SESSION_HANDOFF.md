# Session Handoff

> 用途：切换电脑前，快速记录当前项目状态，保证下一台电脑可以直接继续。

## Current Status

- Date: 2026-03-26
- Device: current machine
- Branch: `codex/face-identity-integration`
- Latest committed revision: `ddcda47`
- Workspace path: `C:\Users\So\Desktop\project\multi-rider`

## What Was Finished

- `Train` 模块已经从 mockup 推进到真实首页骨架。
- 已支持创建数据集、导入本地图片 ZIP、浏览数据集图片。
- 已支持把 Oracle / Upload 结果图回流到 `Train` 数据集。
- 已支持第一版框标注：
  - 单图拖拽画框
  - 选择类别
  - 删除选中框
  - 保存 YOLO 标签
  - 上一张 / 下一张切图
  - `Ctrl+S`、`Delete`、`←/→`、`Esc` 快捷键
- 已补充标注效率功能：
  - 仅看未标注
  - 跳到上一张未标注
  - 跳到下一张未标注
  - 标注状态统计
- 已新增训练任务页：
  - 选择数据集
  - 选择 `yolo26n.pt / yolo26s.pt`
  - 选择预设
  - 创建训练任务
  - 查看最近训练任务
- 训练任务已经不再只是骨架，当前可以真实调用 Ultralytics 执行训练。
- 当前项目依赖已升级到 `ultralytics==8.4.27`，`YOLO26` 训练已验证可运行。
- 已补齐离线依赖：
  - `requirements.txt`
  - `requirements.lock`
  - `vendor/wheels/`
- 已把 `train_runs/` 加入 `.gitignore`，避免误提交训练产物。

## What Was Changed

- 本轮核心文件：
  - `requirements.txt`
  - `requirements.lock`
  - `.gitignore`
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
  - `static/js/index-page/bootstrap.js`
  - `templates/history_detail.html`

## What Is In Progress

- Current task: 训练模块第一阶段继续落地
- Current step: 训练任务已能真实启动，接下来要把训练结果管理做完整
- Current blocker:
  - Oracle 检测链路和内网人脸库链路这轮没有回归
  - 训练结果还没有“发布为线上模型”的完整 UI
  - 标注页还没有“仅看已标注 / 批量复核 / 快捷类别切换”这些更细的效率能力

## What Still Needs To Be Done

1. 训练任务结果管理：
   - 查看训练日志
   - 查看指标摘要
   - 查看 `best.pt / last.pt / results.csv / args.yaml`
2. 模型发布：
   - 把训练产物发布到 `model/`
   - 写入模型元数据
   - 让上传检测页直接可选
3. 标注效率增强：
   - 仅看已标注
   - 类别快捷键
   - 图片列表筛选
   - 标注统计面板
4. 训练页增强：
   - 训练中的轮询刷新
   - 错误日志展示
   - 训练完成后的下载 / 打开目录入口
5. 最后再做 Oracle / Face 模块的联动回归

## Risks / Notes

- `jobs.sqlite3`、`datasets/`、`train_runs/`、`.venv/` 都是本地态，不会随 Git 走。
- 当前训练 smoke test 使用的是极小数据集，仅用于证明训练链路可跑通，不代表模型效果。
- `vendor/wheels/` 是本地离线依赖目录，当前已补齐到新的锁文件版本，但目录本身仍被 `.gitignore` 忽略。
- 工作区里目前有未提交改动；如果要切电脑，建议先 `git status` 看清楚。

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
  - 首页 `/` 正常渲染
  - `Train` 页可创建数据集
  - 可导入本地 ZIP
  - 可保存单图框标注
  - 可创建真实训练任务
  - `YOLO26n` 在 `1 epoch` smoke test 下训练完成
  - 训练结果已生成 `best.pt / last.pt / results.csv / args.yaml`
  - `requirements.lock` 与 `vendor/wheels/` 已同步更新
- Not tested:
  - Oracle 检测主流程
  - Oracle 结果回流联调
  - 内网人脸库同步 / 重建 / 识别联调
- Known broken:
  - 当前没有发现新的明确坏点

## Next Direct Instruction For Codex

```text
先读取项目根目录的 SESSION_HANDOFF.md 和 WORKLOG.md，再继续训练模块。优先做训练结果管理和模型发布，不要回退到 mockup 阶段。
```
