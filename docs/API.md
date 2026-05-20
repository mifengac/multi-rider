# API 参考手册

## 认证

系统面向内网部署，业务 API 当前不做额外鉴权；页面层使用本地登录态控制访问。

## 健康检查

| 方法 | 路径 | 参数 | 返回 | 说明 |
| --- | --- | --- | --- | --- |
| GET | `/api/health` | - | `{status, db, scheduler, timestamp}` | 部署健康检查 |
| GET | `/healthz` | - | `{ok, checks}` | 本地运行依赖检查 |
| GET | `/livez` | - | `{ok, service}` | 进程存活检查 |

## 图谱 `/api/graph`

| 方法 | 路径 | 参数 | 返回 | 说明 |
| --- | --- | --- | --- | --- |
| GET | `/person/<zjhm>` | `depth=1-3`, `relations=`, `time_range=1m|3m|6m|1y` | `{nodes, edges}` | 人物子图 |
| GET | `/case/<ajbh>` | `depth=1-3` | `{nodes, edges}` | 案件子图 |
| POST | `/expand` | `{node_id, node_type, direction}` | `{nodes, edges}` | 节点扩展 |
| GET | `/search` | `keyword=`, `type=` | `{results}` | 节点搜索 |
| GET | `/paths` | `from=`, `to=`, `max_hops=1-6` | `{found, path, hops}` | 最短路径 |

## 评分 `/api/score`

| 方法 | 路径 | 参数 | 返回 | 说明 |
| --- | --- | --- | --- | --- |
| GET | `/<zjhm>` | - | `{total_score, risk_level, dim_*}` | 个人评分 |
| GET | `/list` | `min_score=0-100`, `max_score=0-100`, `risk_level=`, `area_code=`, `page=1`, `size=20`, `sort=asc|desc` | `{total, page, size, items}` | 高风险列表 |
| GET | `/trend/<zjhm>` | `months=1-60` | `{zjhm, months, points}` | 评分趋势 |
| POST | `/recalculate` | `{zjhm}` 或 `{zjhm:"all"}` | `{status, result|message}` | 触发重算 |
| POST | `/batch-recalculate` | - | `{status, message}` | 全量重算 |

## 画像 `/api/profile`

| 方法 | 路径 | 参数 | 返回 | 说明 |
| --- | --- | --- | --- | --- |
| GET | `/<zjhm>` | - | `{basic, score, cases, behaviors, relations, suggestions, trajectory}` | 完整画像 |
| GET | `/<zjhm>/trajectory` | `days=1-365` | `{recent, hotspots, time_pattern, last_seen}` | 轨迹详情 |
| GET | `/<zjhm>/timeline` | - | `{items}` | 事件时间轴 |
| GET | `/<zjhm>/photo` | - | `{zp, zp_source}` | 人口照片 |

## 态势面板 `/api/dashboard`

| 方法 | 路径 | 参数 | 返回 | 说明 |
| --- | --- | --- | --- | --- |
| GET | `/summary` | - | `{total_persons, high_risk_count, month_cases, avg_score, *_prev, *_change_pct}` | 核心指标 |
| GET | `/trend` | `months=1-60`, `metric=cases|persons|score` | `{metric, months, points}` | 月度趋势 |
| GET | `/distribution` | `dim=case_type|risk_level|area|age|gender|source` | `{dimension, items}` | 分布统计 |
| GET | `/heatmap` | `days=1-365` | `{days, items}` | 热力图数据 |
| GET | `/alerts` | `limit=1-100` | `{items}` | 预警列表 |
| GET | `/alerts/stream` | - | `text/event-stream` | SSE 实时预警 |
| POST | `/alerts/<id>/read` | - | `{success}` | 标记已读 |
| POST | `/alerts/<id>/handle` | `{status}` | `{success}` | 处理预警 |
| POST | `/alerts/scan` | - | `{result}` | 手动触发规则扫描 |
| POST | `/dispatch/from-person` | `{zjhm}` | `{ok, zjhm, redirect}` | 画像/预警派发跳转 |
| GET | `/ranking` | `by=area|school`, `metric=case_count|risk_count` | `{by, metric, items}` | 辖区/学校排名 |

## AI 研判 `/api/ai`

| 方法 | 路径 | 参数 | 返回 | 说明 |
| --- | --- | --- | --- | --- |
| POST | `/chat` | `{message, history, mode}` | `text/event-stream` | 通用/RAG 对话 |
| POST | `/analyze/person` | `{zjhm}` | `text/event-stream` | 个人研判 |
| POST | `/analyze/serial` | `{months}` | `text/event-stream` | 侵财串并分析 |

## 检测与结果

| 方法 | 路径 | 参数 | 返回 | 说明 |
| --- | --- | --- | --- | --- |
| GET/POST | `/` | 表单参数 | HTML | 工作台首页 |
| GET/POST/OPTIONS | `/start` | `kssj`, `jssj`, `hours`, `model_key`, `conf`, `batch_size`, `imgsz`, `classes` | `{ok, job_id, total}` | 数据库图片检测 |
| GET | `/progress/<job_id>` | - | `{ok, job}` | 数据库检测进度 |
| POST | `/cancel/<job_id>` | - | `{ok}` | 取消数据库检测 |
| GET | `/jobs` | - | `{ok, running_count, running}` | 当前运行任务 |
| GET | `/history` | `limit=` | `{ok, jobs}` | 历史任务 |
| GET | `/history/<job_id>` | - | `{ok, job, items}` | 历史详情 |
| GET | `/download/<job_id>` | - | ZIP/HTML | 下载结果 |
| GET | `/download/<job_id>/<part>` | - | ZIP | 下载分片 |
| GET | `/summary/<job_id>` | - | text/plain | 下载摘要 |
| POST | `/upload/start` | multipart file 与检测参数 | `{ok, job_id}` | 上传 ZIP/视频检测 |
| GET | `/upload/progress/<job_id>` | - | `{ok, job}` | 上传检测进度 |
| POST | `/upload/cancel/<job_id>` | - | `{ok}` | 取消上传检测 |
| GET | `/upload/download/<job_id>` | - | ZIP | 下载上传检测结果 |
| GET | `/api/dashboard/stats` | - | `{ok, today_matched, pending_dispatch}` | 工作台头部统计 |

## 人脸 `/face`

| 方法 | 路径 | 参数 | 返回 | 说明 |
| --- | --- | --- | --- | --- |
| GET | `/results/<job_id>` | - | `{ok, job, items, identity_summary}` | 检测结果列表 |
| GET | `/results/<job_id>/asset/<asset_id>` | - | image | 结果图片 |
| GET | `/library/status` | - | `{ok, library, task}` | 人脸库状态 |
| GET | `/library/photo/<person_id>` | - | image | 人脸库照片 |
| GET | `/library/persons` | `page`, `page_size`, `keyword` | `{ok, items, total}` | 人脸库人员 |
| GET | `/library/tasks` | - | `{ok, tasks}` | 人脸库任务列表 |
| POST | `/library/rebuild` | - | `{ok, started, task}` | 重建特征库 |
| POST | `/library/sync` | - | `{ok, started, task}` | 同步人脸库 |
| GET | `/library/task/<task_id>` | - | `{ok, task}` | 人脸库任务详情 |
| POST | `/identify` | `{job_id, asset_ids, top_k}` | `{ok, items, identity_summary, dispatch_flow}` | 身份识别 |

## 派发 `/dispatch`

| 方法 | 路径 | 参数 | 返回 | 说明 |
| --- | --- | --- | --- | --- |
| GET | `/auth/status` | - | `{ok, auth, config}` | 任务平台认证状态 |
| POST | `/auth/login` | `{username, password}` | `{ok, auth}` | 登录任务平台 |
| GET | `/queue` | - | `{ok, auth, items, history, defaults}` | 派发队列 |
| GET | `/queue/<queue_id>` | - | `{ok, item, sms_preview}` | 队列详情 |
| POST | `/queue/refresh-region` | `{queue_ids}` | `{ok, updated, skipped, items}` | 重查属地 |
| POST | `/preview` | `{queue_ids, overrides, payload_items, payload_mode}` | `{ok, items}` | 生成下发草稿 |
| POST | `/send` | `{queue_ids, overrides, payload_items, payload_mode}` | `{ok, count, items}` | 下发任务 |
| POST | `/sms/preview` | `{queue_id, template, mobile, overrides}` | `{ok, preview}` | 短信预览 |
| POST | `/sms/send` | `{queue_ids, template, mobile, overrides}` | `{ok, items}` | 发送短信 |

## 训练 `/train`

| 方法 | 路径 | 参数 | 返回 | 说明 |
| --- | --- | --- | --- | --- |
| GET | `/datasets` | - | `{ok, items, summary}` | 数据集列表 |
| POST | `/datasets` | `{name, notes, class_names}` | `{ok, dataset}` | 新建数据集 |
| GET | `/datasets/<dataset_id>` | - | `{ok, dataset}` | 数据集详情 |
| GET | `/datasets/<dataset_id>/assets` | - | `{ok, items}` | 数据集素材 |
| GET | `/datasets/<dataset_id>/assets/<asset_id>` | - | image | 数据集素材文件 |
| GET | `/datasets/<dataset_id>/assets/<asset_id>/annotation` | - | `{ok, annotation}` | 读取标注 |
| POST | `/datasets/<dataset_id>/assets/<asset_id>/annotation` | 标注 JSON | `{ok}` | 保存标注 |
| POST | `/datasets/<dataset_id>/assets/<asset_id>/review` | `{review_status}` | `{ok}` | 审核标注 |
| POST | `/datasets/<dataset_id>/import-zip` | multipart ZIP | `{ok, imported}` | 导入 ZIP |
| POST | `/datasets/<dataset_id>/import-results` | `{job_id, asset_ids}` | `{ok, imported}` | 从检测结果导入 |
| POST | `/datasets/<dataset_id>/auto-annotate` | 自动标注参数 | `{ok, updated}` | 同步自动标注 |
| POST | `/datasets/<dataset_id>/auto-annotate-jobs` | 自动标注参数 | `{ok, job_id}` | 异步自动标注 |
| GET | `/auto-annotate-jobs` | `limit=` | `{ok, items}` | 自动标注任务列表 |
| GET | `/auto-annotate-jobs/<job_id>` | - | `{ok, job}` | 自动标注任务详情 |
| GET | `/jobs` | `limit=` | `{ok, items}` | 训练任务列表 |
| POST | `/jobs` | 训练参数 | `{ok, job_id}` | 启动训练 |
| GET | `/jobs/<job_id>` | - | `{ok, job}` | 训练任务详情 |
| GET | `/jobs/<job_id>/report` | - | `{ok, report}` | 训练报告 |
| GET | `/jobs/<job_id>/artifacts/<filename>` | - | file | 下载训练产物 |
| POST | `/jobs/<job_id>/publish` | - | `{ok, model}` | 发布 best 模型 |
| GET | `/models` | - | `{ok, models, slots, registry_options}` | 模型注册表 |
| POST | `/models/<model_name>/metadata` | 元数据 | `{ok, model}` | 更新模型元数据 |
| POST | `/model-slots/<slot_key>` | `{model_name}` | `{ok, slot}` | 设置部署槽 |
| POST | `/model-slots/<slot_key>/rollback` | - | `{ok, slot}` | 回滚部署槽 |

## 诊断与页面

| 方法 | 路径 | 参数 | 返回 | 说明 |
| --- | --- | --- | --- | --- |
| GET | `/diagnostics/task-queue` | `task_type`, `status`, `limit` | `{ok, totals, tasks, health}` | 任务队列诊断 |
| GET | `/dashboard` | - | HTML | 态势总览页 |
| GET | `/profile` | `zjhm=` | HTML | 画像查询页 |
| GET | `/profile/<zjhm>` | - | HTML | 个人画像页 |
| GET | `/graph` | `zjhm=` | HTML | 关系图谱页 |
| GET | `/ai-analyst` | - | HTML | AI 研判页 |
| GET | `/workbench` | - | HTML | 工作台页 |
| GET | `/history-page` | - | HTML | 历史任务页 |
| GET | `/history-page/<job_id>` | - | HTML | 历史任务详情页 |
| GET | `/train/model-registry-page` | - | HTML | 模型注册页面 |
| GET | `/train/jobs/<job_id>/report-page` | - | HTML | 训练报告页面 |

## 错误响应

JSON API 错误统一返回可机器识别的 `error` 字段，部分端点同时返回 `message` 或 `ok=false`：

```json
{
  "error": "invalid_zjhm",
  "message": "证件号格式不正确"
}
```

| 状态码 | 说明 |
| --- | --- |
| 400 | 参数错误 |
| 404 | 资源不存在 |
| 413 | 上传文件过大 |
| 500 | 服务端错误，多为外部数据库、模型或文件系统异常 |
