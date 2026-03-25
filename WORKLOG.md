# Worklog

> 用途：记录项目推进过程，重点写“做了什么、为什么、下一步做什么”。

## Template

### YYYY-MM-DD HH:MM

- Device:
- Branch:
- Goal:
- Done:
  - 
  - 
- Files:
  - 
  - 
- Decision:
  - 
- Risk:
  - 
- Next:
  - 

---

## Entries

### 2026-03-25 22:45

- Device: office
- Branch: `codex/face-identity-integration`
- Goal: 完成训练模块第一阶段设计，并在换电脑前把交接文件落地
- Done:
  - 新增训练模块开发清单，明确 `YOLO26` 为主训练路线，`YOLO-World` 为预标注路线
  - 重建 `design-mockup.html`，加入 `Train` 页签原型
  - 删除 `yoloe-26n-seg.pt`、`yoloe-26s-seg.pt`，默认通用模型切到 `yolov8s-worldv2.pt`
  - 新建 `SESSION_HANDOFF.md`、`WORKLOG.md`、`HANDOFF_CHECKLIST.md`
  - 调整 `.gitignore`，避免把本地数据和离线大文件推上远程
- Files:
  - `config.py`
  - `design-mockup.html`
  - `0325_train_module_checklist.md`
  - `0325_model_directory_strategy.md`
  - `.gitignore`
  - `SESSION_HANDOFF.md`
  - `WORKLOG.md`
  - `HANDOFF_CHECKLIST.md`
- Decision:
  - 先不重排 `model/` 目录物理路径，只先做规范文档和默认模型切换，避免打断当前运行配置
- Risk:
  - 训练模块目前还是设计态，没有真实后端和前端实现
  - 仓库里已有部分较大改动，需要后续继续回归验证
- Next:
  - 下一台电脑接手后，优先实现 `Train` 页面的真实路由和“数据集管理”骨架
