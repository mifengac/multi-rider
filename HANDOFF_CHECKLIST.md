# End Of Day Handoff Checklist

> 用途：下班前 30 秒快速检查。  
> 原则：先保证代码可恢复，再保证上下文可接力。

## 30-Second Checklist

- [x] 已运行 `git status`
- [x] 已更新 `SESSION_HANDOFF.md`
- [x] 已更新 `WORKLOG.md`
- [x] 已确认当前分支写入 handoff
- [x] 已写清楚当前做到哪一步
- [x] 已写清楚下一步做什么
- [x] 已写清楚未测试项
- [x] 已写清楚风险项
- [x] 完成 `commit + push`

## Minimum Version

如果时间只够做最少动作，至少完成这 4 项：

- [x] `git status`
- [x] 保存代码变更
- [x] 更新 `SESSION_HANDOFF.md`
- [x] 写明下一步

## Copy-Paste Prompt

```text
先读取项目根目录的 SESSION_HANDOFF.md 和 WORKLOG.md，再继续当前任务。先总结当前状态、未完成事项、风险和下一步。
```
