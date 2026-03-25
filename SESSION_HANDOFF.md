# Session Handoff

> 用途：切换电脑前快速记录当前项目状态，保证下一台电脑可以直接继续。

## Current Status

- Date: 2026-03-25
- Device: office
- Branch: `codex/face-identity-integration`
- Last commit before this handoff: `8887b0d`
- Workspace path: `C:\Users\So\Desktop\project\multi-rider`

## What Was Finished

- 新增训练模块开发清单，明确了数据集、预标注、训练、评估和发布的第一版范围。
- 重建了 [design-mockup.html](C:/Users/So/Desktop/project/multi-rider/design-mockup.html)，加入 `Train` 页签原型。
- 删除了两个 `YOLOE` 权重，默认通用模型切换为 `yolov8s-worldv2.pt`。
- 新建了跨电脑协作用的 `SESSION_HANDOFF.md`、`WORKLOG.md`、`HANDOFF_CHECKLIST.md`。

## What Was Changed

- Files touched:
  - `config.py`
  - `design-mockup.html`
  - `deploy/app.env.example`
  - `Dockerfile`
  - `README.md`
  - `.gitignore`
  - `model/README.md`
  - `0325_train_module_checklist.md`
  - `0325_model_directory_strategy.md`
  - `SESSION_HANDOFF.md`
  - `WORKLOG.md`
  - `HANDOFF_CHECKLIST.md`
- Key behavior changes:
  - 通用模型默认路径改为 `model/yolov8s-worldv2.pt`
  - 上传模型列表优先级改为 `yolov8s-worldv2.pt`、`yolo26s.pt`、`yolo26n.pt`、`biaochezhajiev2.pt`
  - Docker 构建检查不再依赖 `YOLOE` 权重

## What Is In Progress

- Current task: 切换电脑前整理 handoff 并推送当前代码
- Current step: 更新交接文件、整理 `.gitignore`、提交并推送
- Current blocker: Oracle 和内网人脸库联调仍需在内网环境继续做

## What Still Needs To Be Done

1. 把 `Train` 模块从 mockup 落到真实路由和页面
2. 第一阶段优先实现数据集管理、ZIP 导入、历史结果加入数据集
3. 后续如需重整 `model/` 目录，再做一次受控迁移，不要直接移动现有运行路径

## Risks / Notes

- 当前仓库里有较多已修改代码，训练模块本身还没有真实实现
- 本次推送不应包含本地数据：`face_data/`、`test/`、`jobs.sqlite3`、`vendor/wheels.7z`
- `README.md` 历史上有编码问题，这次只做了必要替换，没有整体重写

## Commands To Resume

```powershell
git pull
git branch --show-current
git status
python app.py
```

## Verification Status

- Tested:
  - `config.py` 语法检查通过
  - `design-mockup.html` 已确认包含 `tabBtn-train`、`tab-train`、`yolo26n.pt`、`yolo26s.pt`
  - 默认 `general` 模型已解析为 `model/yolov8s-worldv2.pt`
- Not tested:
  - 训练模块目前只有文档和 mockup，没有真实路由和服务
  - Oracle 和内网人脸库联调未在这次 handoff 前重跑
- Known broken:
  - 无新的明确坏点，但训练模块尚未开始真实实现

## Next Direct Instruction For Codex

```text
先读取项目根目录的 SESSION_HANDOFF.md 和 WORKLOG.md，再继续当前任务。重点看 Current Status、What Was Finished、What Is In Progress、What Still Needs To Be Done。
```

## History Notes

- 本次 handoff 的重点是保证换电脑后可以继续接着做训练模块。
