# Commit Split Guide

> 用途：给本次阅读友好型重构提供可直接执行的提交边界，避免把本地环境文件或无关改动混进去。

## First Rule

- 不要提交本地 .env
- 不要提交 .mcp
- 根目录下当前未跟踪的 .env.example 不是本次重构必需文件，除非你明确要把它作为仓库配置模板引入，否则不要一起提交

## Recommended Option A

- 用一个提交完成本次结构重构
- 适合你想保留完整迁移历史，不强调文档与代码分离时使用

### Suggested Message

- refactor: reorganize project structure for readability

### Suggested Scope

- app.py
- modules
- shared
- templates/modules
- static/modules
- static/shared
- ops
- docs
- README.md
- .gitignore
- 旧 routes、service、db、utils、旧模板、旧脚本、旧根目录文档的删除

## Recommended Option B

- 用两个提交拆开结构迁移和文档收尾
- 适合你后续要回看“代码怎么搬的”和“文档怎么补的”时使用

### Commit 1

- 消息：refactor: regroup codebase into modules and shared layers
- 范围：
- app.py
- .gitignore
- modules
- shared
- templates/modules
- static/modules
- static/shared
- ops
- 旧 routes、service、db、utils、旧模板、旧脚本、旧 Dockerfile、旧 deploy 目录相关删除

### Commit 2

- 消息：docs: refresh README and handoff after structure refactor
- 范围：
- README.md
- docs/handoff/REFACTOR_SUMMARY.md
- docs/handoff/SESSION_HANDOFF.md
- docs/handoff/WORKLOG.md
- docs/handoff/HANDOFF_CHECKLIST.md
- docs/handoff/REGRESSION_CHECKLIST.md
- docs/handoff/COMMIT_SPLIT_GUIDE.md
- docs/notes、docs/mockups、docs/tools 中本轮整理后的文档目录迁移

## Staging Hint

- 提交前先运行 git status --short
- 如果要拆提交，先 stage 结构目录和旧目录删除，再单独 stage README 与 handoff 文档
- 如果发现根目录 .env.example 还在未跟踪列表，先决定是否保留；默认建议排除

## Review Focus Before Commit

- app.py 是否仍从新路径导入 Blueprint
- templates/index.html 是否只引用新模板和新脚本路径
- shared/config/config.py 是否已改成新的 BASE_DIR 计算
- README 是否完全切到新目录结构
- handoff 文档是否不再引用旧仓库路径和旧分支名

## Exact Commands For Current Workspace

- 下面命令基于 2026-03-30 当前工作区状态编写，目标是把“结构迁移”与“文档/交接更新”拆成两个提交。
- 默认仍然不要提交根目录未跟踪的 `.env.example`。
- 如果执行过程中又出现新的本地文件，先重新跑一次 `git status --short --untracked-files=all`，不要直接混进提交。

### Step 0

```powershell
git status --short --untracked-files=all
```

### Commit 1 Exact Scope

- 目标：只提交结构重组、代码迁移、模板/静态资源迁移、部署文件迁移，以及对应旧路径删除。
- 建议消息：`refactor: regroup codebase into modules and shared layers`

```powershell
git add app.py templates/index.html .gitignore
git add -A modules shared ops
git add -A templates/modules static/modules static/shared
git add -A db routes service utils
git add -A config.py Dockerfile deploy app.env.example
git add -A templates/history.html templates/history_detail.html templates/train_model_registry.html templates/train_report.html templates/index
git add -A static/js/index-page
git add -A face_library.sql
git status --short --untracked-files=all
```

- 这一步 stage 后，预期会看到：`modules/`、`shared/`、`ops/`、`templates/modules/`、`static/modules/`、`static/shared/`、`app.py`、`templates/index.html`、`.gitignore`，以及旧 `db/`、`routes/`、`service/`、`utils/`、旧模板和旧脚本删除被纳入暂存区。
- 这一步不应包含：`README.md`、`docs/`、根目录那些被搬到 `docs/notes/` / `docs/mockups/` / `docs/tools/` / `docs/handoff/` 的文档。

### Commit 2 Exact Scope

- 目标：只提交 README、交接文档、说明文档迁移和辅助脚本迁移。
- 建议消息：`docs: refresh README and handoff after structure refactor`

```powershell
git add README.md
git add -A docs
git add -A 0323_dev_list.md 0324_introduce_project.md 0324_local_upload_test_report.md 0324_reflective_vest_prompt_test_table.md
git add -A 0325_face_recognition_identity_integration.md 0325_face_recognition_identity_integration_translate.md 0325_model_directory_strategy.md 0325_train_module_checklist.md
git add -A 0326_task_dispatch_checklist.md 0328-smart-policing-demo-video-script-opening-and-modules.md 2026-03-26_train_module_test_findings.md
git add -A bczj.md json-csv.md design-mockup.html _append_smart_policing_slides.py
git add -A HANDOFF_CHECKLIST.md SESSION_HANDOFF.md SPEECH_SCRIPT_WITH_TIMECODES.md WORKLOG.md
git status --short --untracked-files=all
```

- 这一步 stage 后，默认只应剩下根目录 `.env.example` 仍未跟踪。
- 如果还剩别的未暂存内容，说明工作区又混入了新文件，需要先判断是否属于本轮重构。

### Commit Execution

```powershell
git commit -m "refactor: regroup codebase into modules and shared layers"
git commit -m "docs: refresh README and handoff after structure refactor"
```

### Safety Check

- 第一个提交前，重点看 `git diff --cached --stat` 是否只覆盖代码与结构迁移。
- 第二个提交前，重点看 `git diff --cached --stat` 是否只覆盖 `README.md` 和 `docs/`。
- 如果你不想拆两次提交，也可以把上面两步的 `git add` 全部执行完，再统一提交一次。

## After Commit

- 立即跑一次最小启动验证
- 再按 docs/handoff/REGRESSION_CHECKLIST.md 回归四条主链路