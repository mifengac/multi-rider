# End Of Day Handoff Checklist

> 用途：下班前 30 秒快速检查。  
> 原则：先保证代码可恢复，再保证上下文可接力。

## Current Session Snapshot

- Date: 2026-03-30
- Branch: `main`
- Latest committed revision: `8a7e174`
- Current focus: 目录重构收尾、提交边界整理、业务链路回归

## 30-Second Checklist

- [x] 已运行 `git status`
- [x] 已更新 `docs/handoff/SESSION_HANDOFF.md`
- [x] 已更新 `docs/handoff/WORKLOG.md`
- [x] 已确认当前分支写入 handoff
- [x] 已写清楚当前做到哪一步
- [x] 已写清楚下一步做什么
- [x] 已写清楚未测试项
- [x] 已写清楚风险项
- [x] 已记录目录重构后的代码入口与新路径
- [ ] 如需切电脑，决定是否先 `commit + push`

## Minimum Version

如果时间只够做最少动作，至少完成这 4 项：

- [x] `git status`
- [x] 保存代码变更
- [x] 更新 `docs/handoff/SESSION_HANDOFF.md`
- [x] 写明下一步

## Copy-Paste Prompt

```text
先读取 docs/handoff/REFACTOR_SUMMARY.md、docs/handoff/REGRESSION_CHECKLIST.md、docs/handoff/COMMIT_SPLIT_GUIDE.md、docs/handoff/SESSION_HANDOFF.md 和 docs/handoff/WORKLOG.md，再继续当前任务。先确认新目录结构与提交边界，再回归 detection / face / dispatch / training 四条主链路。
```
