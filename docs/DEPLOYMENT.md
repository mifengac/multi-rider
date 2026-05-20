# 部署指南

## 前置要求

- Python 3.12 与 `uv`
- KingBase V8，或 PostgreSQL 兼容数据库
- 4GB+ 内存，2 核 CPU
- 已准备模型文件、`static/dist/tailwind.css` 与内网离线 wheel 包

## 快速启动

### 1. 配置环境

```bash
cp .env.example .env
```

编辑 `.env`，至少填写 KingBase、模型路径、输出目录和 Flask 密钥：

```bash
KINGBASE_HOST=127.0.0.1
KINGBASE_PORT=54321
KINGBASE_DB=security
KINGBASE_USER=CHANGE_ME
KINGBASE_PASSWORD=CHANGE_ME
KINGBASE_SCHEMA=ywdata
JCGKZX_MONITOR_SCHEMA=jcgkzx_monitor
FLASK_SECRET_KEY=CHANGE_ME_TO_A_RANDOM_SECRET
APP_HOST=0.0.0.0
APP_PORT=5001
```

### 2. 初始化数据库

```bash
uv run python scripts/run_migrations.py
```

迁移脚本按 `scripts/sql/v*.sql` 文件名排序执行，当前包含：

- `scripts/sql/v1_0_init_tables.sql`
- `scripts/sql/v1_1_sample_data.sql`

脚本使用 `CREATE ... IF NOT EXISTS` 与 `ON CONFLICT DO NOTHING`，可重复执行。

### 3. 启动服务

```bash
uv run python app.py
```

访问：

- 工作台：`http://localhost:5001/`
- 态势总览：`http://localhost:5001/dashboard`
- 健康检查：`http://localhost:5001/api/health`

如需使用 5000 端口，将 `.env` 中 `APP_PORT=5000`，并同步调整容器端口映射。

## 配置说明

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `KINGBASE_HOST` | `localhost` | KingBase 主机 |
| `KINGBASE_PORT` | `54321` | KingBase 端口 |
| `KINGBASE_DB` | - | 数据库名，必填 |
| `KINGBASE_USER` | - | 数据库用户，必填 |
| `KINGBASE_PASSWORD` | - | 数据库密码，必填 |
| `KINGBASE_SCHEMA` | `ywdata` | 业务库默认 schema |
| `JCGKZX_MONITOR_SCHEMA` | `jcgkzx_monitor` | 聚合层 schema |
| `WCNR_SCHEDULER_ENABLED` | `1` | 启用未成年人评分/预警调度器；测试可设 `0` |
| `WCNR_SCHEDULER_BATCH_HOUR` | `3` | 日批评分小时 |
| `WCNR_SCHEDULER_DECAY_DOM` | `1` | 月衰减日期 |
| `WCNR_SCHEDULER_ALERT_SCAN_MINUTES` | `5` | 预警规则扫描间隔 |
| `WCNR_SCHEDULER_INCREMENTAL_MINUTES` | `10` | 增量评分扫描间隔 |
| `FLASK_ENV` | `production` | Flask 运行环境 |
| `DEBUG` | `0` | 生产环境保持关闭 |

## Docker 部署

构建并启动：

```bash
docker compose -f docker-compose.yml up --build -d web worker
```

`web` 容器启动时会先执行：

```bash
python scripts/run_migrations.py && python app.py
```

如部署环境使用外部 KingBase，只需在 `app.env` 或 `.env` 中配置 `KINGBASE_*` 变量；不要求 compose 内置 KingBase 容器。

## 离线安装

在有网络环境准备 wheel 包后，内网机器执行：

```bash
pip install --no-index --find-links ./wheels -r requirements.txt
```

已有 `uv` 环境时：

```bash
uv pip install --python .venv/Scripts/python.exe --no-index --find-links ./wheels -r requirements.txt
```

## 监控与维护

### 健康检查

```bash
curl http://localhost:5001/api/health
```

返回示例：

```json
{
  "status": "ok",
  "db": "connected",
  "scheduler": "running",
  "timestamp": "2026-05-20T00:00:00.000000"
}
```

`status=degraded` 通常表示 KingBase 不可连接；先检查 `KINGBASE_*` 配置、网络连通性和数据库权限。

### 日志

- Flask 与调度器日志输出到标准输出/标准错误。
- Docker 部署使用 `docker logs multi-rider-web` 查看 Web 日志。
- 任务历史和训练数据依赖 `jobs.sqlite3`、`output/`、`datasets/`、`train_runs/`，清理前先备份。

### 常用命令

```bash
uv run pytest -q
uv run python -c "import app"
uv run python scripts/run_migrations.py
```
