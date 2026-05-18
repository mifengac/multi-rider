# 0518 Codex 工作交接

> 仅记录本轮和 Codex 的对话与落地工作，不包含之前和 Claude Code 的聊天记录。

## 当前目标

用户已经把 Claude 设计好的静态页面放在 `docs/claude design/`，但这套设计缺少原“工作台”里的五个操作模块：

- 数据巡检
- 本地素材
- 任务下发
- 模型训练
- 系统诊断

本轮目标是补齐这五个模块的静态设计，方便后续再迁入正式 Flask 页面。

## 已确认的设计方案

采用“方案 B”：

- 顶部主导航保留现有分析视图：
  - 态势总览
  - 个人画像
  - 关系图谱
  - AI 研判
- 顶部新增一级页签：
  - 工作台
- 工作台内部使用左侧二级导航承载五个模块：
  - 数据巡检
  - 本地素材
  - 任务下发
  - 模型训练
  - 系统诊断

设计理由：

- 顶部不被九个入口挤满。
- 分析视图和操作工作流分层清楚。
- 更贴近当前项目真实工作台结构。
- 后续还能继续扩展人脸库、统计、审计等操作模块。

## 已修改文件

### `docs/claude design/index.html`

已完成：

- 顶部导航新增 `工作台` 页签。
- 新增 `page-workbench` 页面容器。
- 引入 `js/workbench.js`。

### `docs/claude design/js/workbench.js`

新增文件，负责工作台静态原型。

已包含：

- `WorkbenchPage` 页面模块。
- 左侧二级导航。
- 五个子模块切换逻辑。
- 每个模块的标题、说明、KPI、主操作区、队列/记录区。
- 闭环流转展示。

五个模块当前内容：

- `数据巡检`：数据库巡检参数、预设模板、任务进度、命中结果入口。
- `本地素材`：素材上传、模型参数、抽帧/识别进度、结果图流转。
- `任务下发`：待下发队列、任务草稿、平台 payload、短信预览、下发记录。
- `模型训练`：数据集、样本导入、标注/复核、训练任务、模型发布。
- `系统诊断`：队列健康、Worker 状态、错误任务、服务检查、修复建议。

### `docs/claude design/css/styles.css`

已补充工作台样式：

- `.workbench-layout`
- `.workbench-sidebar`
- `.workbench-main`
- `.workbench-module-header`
- `.workbench-kpi-row`
- `.workbench-grid`
- `.workbench-card`
- `.workbench-field-grid`
- `.workbench-result-list`
- `.workbench-flow`
- `.workbench-table`
- 颜色状态类：`tone-cyan`、`tone-amber`、`tone-red`、`tone-green`、`tone-purple`

也补了窄屏适配：

- `@media (max-width: 1100px)`
- `@media (max-width: 760px)`

窄屏下：

- 工作台内容改为单列。
- KPI 改为两列。
- 顶部导航压缩标题、隐藏右侧时钟，确保能看到 `工作台` 入口。

### `docs/claude design/js/icons.js`

新增图标：

- `briefcase`
- `database`
- `upload`
- `settings`

### `docs/claude design/js/utils.js`

已更新 `PageManager` 的标题映射：

- `workbench: '工作台'`

## 验证记录

### 结构检查

已用 Node 脚本检查以下内容存在：

- `data-page="workbench"`
- `page-workbench`
- `js/workbench.js`
- `工作台`
- `数据巡检`
- `本地素材`
- `任务下发`
- `模型训练`
- `系统诊断`
- `@media (max-width: 1100px)`
- `@media (max-width: 760px)`

结果：

```text
Workbench prototype pieces present
```

### JS 语法检查

已运行：

```powershell
node --check "C:\Users\Administrator\Desktop\cursor\multi-rider\docs\claude design\js\workbench.js"
node --check "C:\Users\Administrator\Desktop\cursor\multi-rider\docs\claude design\js\utils.js"
node --check "C:\Users\Administrator\Desktop\cursor\multi-rider\docs\claude design\js\icons.js"
```

结果：

- 三个命令均退出码为 `0`。
- 未输出语法错误。

### 浏览器验证

本地静态服务：

```text
http://127.0.0.1:8765/index.html
```

浏览器中已确认：

- 页面可打开。
- 顶部 `工作台` 入口可见。
- 点击 `工作台` 后进入工作台页面。
- `数据巡检` 默认展示正常。
- 窄视口下工作台不再明显挤压，按钮和卡片能收进视口。

## 当前注意事项

1. 当前只落地了 `docs/claude design/` 静态原型。
2. 没有迁入正式 Flask 模板：
   - `templates/`
   - `static/`
   - `modules/`
3. 没有改正式路由和接口。
4. `docs/claude design/` 当前在 Git 状态里显示为未跟踪目录。
5. 本轮过程中创建过 `.superpowers` 临时预览文件，后面已删除临时 HTML；最终交接只需要关注 `docs/claude design/` 和本文件。

## 建议后续工作

### 1. 先检查静态原型

在项目根目录启动静态服务：

```powershell
cd "C:\Users\Administrator\Desktop\cursor\multi-rider\docs\claude design"
python -m http.server 8765 --bind 127.0.0.1
```

浏览器打开：

```text
http://127.0.0.1:8765/index.html
```

重点检查：

- 顶部五个主入口是否符合预期。
- 工作台五个子模块文案是否需要调整。
- 窄屏和宽屏下布局是否都能接受。

### 2. 再决定是否迁入正式页面

如果静态原型确认无误，再把这套结构迁入正式应用：

- 统一 `base_sentinel.html` 或类似基础模板。
- 把 `docs/claude design/css/styles.css` 中可复用部分迁入正式静态样式。
- 把 `workbench.js` 拆到正式 `static/modules/...` 或按现有项目模块接入。
- 对接现有模块：
  - `templates/modules/detection/_oracle_tab.html`
  - `templates/modules/detection/_upload_tab.html`
  - `templates/modules/dispatch/_dispatch_tab.html`
  - `templates/modules/training/_train_tab.html`
  - `templates/modules/diagnostics/_task_queue_tab.html`

### 3. 正式迁入时建议保留的结构

推荐正式页面继续保持：

```text
顶部主导航
  态势总览
  个人画像
  关系图谱
  AI 研判
  工作台

工作台内部
  左侧二级导航
    数据巡检
    本地素材
    任务下发
    模型训练
    系统诊断
  右侧模块内容
```

这样迁入时风险最低，也方便逐个模块替换静态数据为真实接口。
