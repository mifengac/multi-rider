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

### 2026-03-25 22:45

- Device: office
- Branch: `codex/face-identity-integration`
- Goal: 完成训练模块第一阶段设计，并在换电脑前把交接文件落地
- Done:
  - 新增训练模块开发清单，明确 `YOLO26` 为主训练路线，`YOLO-World` 为预标注路线
  - 重建 `design-mockup.html`，加入 `Train` 页签原型
  - 删除 `yoloe-26n-seg.pt`、`yoloe-26s-seg.pt`
  - 新建 `SESSION_HANDOFF.md`、`WORKLOG.md`、`HANDOFF_CHECKLIST.md`
  - 调整 `.gitignore`，避免把本地数据和离线大文件推上仓库
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
  - `SESSION_HANDOFF.md`
  - `WORKLOG.md`
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
