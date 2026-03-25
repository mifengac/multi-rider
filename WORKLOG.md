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

### 2026-03-26 07:50

- Device: current machine before switching
- Branch: `codex/face-identity-integration`
- Goal: 继续落地训练模块第一阶段，并在换电脑前把 Train 当前状态和交接信息补齐
- Done:
  - 把 `Train` 从 mockup 推进到真实页面骨架，补上数据集创建、SQLite 落库和本地目录初始化
  - 实现 ZIP 导入流程，新增 `dataset_assets` 持久化、图片元数据记录、最近导入预览和图片访问接口
  - 将 [index.html](C:/Users/So/Desktop/project/multi-rider-repo/templates/index.html) 内联的大段业务 JS 抽到 [index-page.js](C:/Users/So/Desktop/project/multi-rider-repo/static/js/index-page.js)，模板只保留 bootstrap 配置
  - 本地完成两轮 smoke test：真实创建数据集、导入包含 2 张图片和 1 个非图片文件的 ZIP，并确认测试数据已清理
- Files:
  - `db/sqlite.py`
  - `routes/train_routes.py`
  - `service/dataset_service.py`
  - `templates/index.html`
  - `static/js/index-page.js`
  - `WORKLOG.md`
  - `SESSION_HANDOFF.md`
  - `HANDOFF_CHECKLIST.md`
- Decision:
  - 页面脚本先按“模板配置内联、业务逻辑外链”拆分，优先解决 `index.html` 过重的问题；这一轮不继续细拆成多份 feature 文件
  - 训练模块优先继续做“历史结果回流到数据集”，暂不提前碰训练任务编排和模型发布
- Risk:
  - [index-page.js](C:/Users/So/Desktop/project/multi-rider-repo/static/js/index-page.js) 虽然已从模板中抽离，但文件仍然很大，后续还需要按功能继续拆
  - Oracle 检测链路和内网人脸库链路这次没有做全量回归，切到新电脑后仍要在对应环境重测
- Next:
  - 实现“历史结果加入数据集”，把已有 Oracle / Upload 检测结果回流到 `Train`
  - 继续补数据集内图片管理、标注入口和复核流程
  - 如后续继续改首页交互，再考虑把 [index-page.js](C:/Users/So/Desktop/project/multi-rider-repo/static/js/index-page.js) 按 `job/upload/train/face` 拆成多文件
