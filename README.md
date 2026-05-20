# multi-rider

基于 Flask + YOLO 的图片/视频智能检测服务，面向内网（无互联网）部署。

## 功能概览

| Tab | 数据来源 | 典型用途 |
|---|---|---|
| **数据库检测** | Oracle 数据库按时间范围查询图片 URL，批量下载推理 | 定期筛查、飙车炸街告警图检索 |
| **本地上传检测** | 民警/用户上传 ZIP 图片包或 MP4/AVI/MOV 视频 | 现场视频快速比对、手头素材核查 |

两个 Tab 共享同一套模型和参数配置，检测结果均打包为 ZIP 供下载。

## 模型

| key | 文件 | 说明 |
|---|---|---|
| `general` | `model/yolo/production/yolov8s-worldv2.pt` | YOLO-World 开放词表，支持英文提示词（留空=自动检测） |
| `bczj` | `model/yolo/production/biaochezhajiev2.pt` | 私有训练模型，针对飙车炸街场景，支持类别索引过滤 |

> **注意**：模型文件不随仓库提交，需按类型放入 `model/yolo/production`、`model/yolo/foundation`、`model/insightface`、`model/assets`。

## 项目结构

```
multi-rider/
├── app.py                   # Flask 入口，注册各业务模块 Blueprint
├── requirements.txt         # 直接依赖
├── requirements.lock        # uv 生成的完整锁文件
├── wheels/                  # 内网离线安装使用的本地 wheel 包目录
├── modules/
│   ├── detection/           # 检测模块：数据库检测、本地上传、结果下载
│   ├── face/                # 人脸模块：人脸库、识别、身份核验
│   ├── dispatch/            # 下发模块：认证、队列、短信、任务下发
│   ├── dashboard/           # 未成年人管控态势、预警、排名 API
│   ├── graph/               # 人员/案件关系图谱 API
│   ├── profile/             # 个人画像、轨迹、时间轴 API
│   ├── score/               # 风险评分、趋势、重算 API
│   └── training/            # 训练模块：数据集、预标注、训练、模型注册
├── shared/
│   ├── config/              # 全局配置与环境变量加载
│   ├── db/                  # SQLite / Oracle 等共享存储与数据库接入
│   ├── inference/           # YOLO 模型加载与批量推理
│   ├── ownership/           # 会话归属 / 访问隔离
│   └── utils/               # 通用工具函数
├── templates/
│   ├── index.html           # 工作台壳层
│   └── modules/             # 按模块拆分的页面片段与页面模板
├── static/
│   ├── modules/             # 按模块拆分的前端脚本
│   ├── shared/              # 共享前端脚本
│   ├── src/tailwind.css     # Tailwind 输入文件，汇总自定义组件样式
│   └── dist/tailwind.css    # npm 构建后的生产 CSS，页面离线引用
├── package.json             # Tailwind/PostCSS 构建脚本
├── tailwind.config.js       # Tailwind v3 配置，目标 Chrome 88+
├── docs/                    # 方案文档、交接记录、设计稿、辅助脚本
├── scripts/sql/             # KingBase 迁移脚本
├── docker-compose.yml       # 唯一权威 Compose 配置（内网运行已导入镜像）
├── ops/
│   ├── Dockerfile           # Linux Docker 镜像构建定义
│   └── app.env.example      # 环境变量模板
├── model/                   # 模型文件（不入库）
├── output/                  # 推理结果 ZIP 输出目录
├── upload_tmp/              # 视频上传临时目录（推理后自动清理）
└── instantclient_11_2/      # Oracle Instant Client（不入库，Windows/Linux 版本不同）
```

## 代码导航

- 检测相关后端：`modules/detection/`
- 人脸识别与身份核验：`modules/face/`
- 任务下发与短信：`modules/dispatch/`
- 训练、预标注、模型注册：`modules/training/`
- 未成年人管控态势：`modules/dashboard/`
- 风险评分、画像与图谱：`modules/score/`、`modules/profile/`、`modules/graph/`
- 全局配置与环境变量：`shared/config/config.py`
- 共享数据库接入：`shared/db/`
- 参数校验：`shared/validators.py`
- 共享推理能力：`shared/inference/infer_service.py`
- 工作台页面壳层：`templates/index.html`
- 模块页面模板：`templates/modules/`
- 模块前端脚本：`static/modules/`
- 运维与部署材料：`ops/`
- 部署指南与 API 手册：`docs/DEPLOYMENT.md`、`docs/API.md`
- 方案、交接、设计稿：`docs/`

## 未成年人管控中枢模块

本轮补齐了上线运维所需资产：

- 数据库迁移：`scripts/run_migrations.py` 按顺序执行 `scripts/sql/v*.sql`，初始化 `jcgkzx_monitor.wcnr_alert` 与 `wcnr_score_history`。
- API 文档：`docs/API.md` 列出图谱、评分、画像、态势面板、检测、人脸、派发、训练和诊断端点。
- 部署文档：`docs/DEPLOYMENT.md` 说明 KingBase、调度器、Docker 和健康检查配置。
- 健康检查：`GET /api/health` 返回 KingBase 与调度器状态。

## 前端样式构建

项目使用 `tailwindcss@3.4.17`，原因是 Tailwind v4 官方要求 Chrome 111+，而本项目要求 Chrome 88+。Tailwind 不在浏览器里运行，开发或构建机通过 npm 预编译出 `static/dist/tailwind.css`，Flask 页面只引用这个静态 CSS 文件。

```powershell
npm install
npm run build:css
```

日常改模板或 class 后需要重新执行 `npm run build:css`。Docker 离线部署只需要打包已经生成的 `static/dist/tailwind.css`，运行容器时不需要 Node.js 或 npm。

## 运行目录维护

- `output/`：检测结果 ZIP 和 `_results/` 清单目录。需要保留历史结果时不要直接清空；如仅做演示，可定期删除旧任务目录与旧 ZIP。
- `upload_tmp/`：上传过程中的临时目录。正常结束后会自动清理；若异常中断后残留，可手动清空。
- `logs/`：启动器和运行日志。当前仓库里常见的是 `app.stdout.log`、`app.stderr.log`；可按时间轮转或定期删除旧日志。
- `train_runs/`：训练运行输出目录。仅在实际训练后产生内容，通常体积较大，建议按任务完成情况归档或清理。
- `datasets/`：训练数据集目录。这里是业务数据，不应像缓存目录那样随意清空。
- `jobs.sqlite3`：SQLite 历史与任务状态库。删除会丢失历史记录、训练任务记录和数据集元信息，清理前应先备份。

## 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `ORACLE_HOST` | `oracledb.example.com` | Oracle 服务器 IP |
| `ORACLE_PORT` | `1521` | Oracle 端口 |
| `ORACLE_SERVICE` | `yfgxpt` | Oracle 服务名 |
| `ORACLE_USER` | `yfzagk` | 数据库用户名 |
| `ORACLE_PASSWORD` | *(必须修改)* | 数据库密码 |
| `FLASK_SECRET_KEY` | *(必须修改)* | Flask Session 密钥 |
| `MODEL_DEFAULT` | `general` | 启动时预热的模型 |
| `CONF_THRESH` | `0.8` | 默认置信度阈值 |
| `MAX_WORKERS` | `8` | 并发下载线程数 |
| `BATCH_SIZE` | `8` | YOLO 推理批大小 |
| `IMGSZ` | `640` | 推理输入尺寸 |
| `VIDEO_FRAME_INTERVAL` | `5` | 视频每隔 N 帧取一帧 |
| `MAX_UPLOAD_BYTES` | `524288000` (500 MB) | 上传文件大小上限 |
| `OUTPUT_DIR` | `./output` | 结果 ZIP 目录 |
| `YOLO_TELEMETRY` | `false` | **禁用 ultralytics 联网检测**（内网必须保持 false） |
| `KINGBASE_HOST` | *(必须修改)* | KingBase V8 主机 |
| `KINGBASE_PORT` | `54321` | KingBase V8 端口 |
| `KINGBASE_DB` | *(必须修改)* | KingBase 数据库名 |
| `KINGBASE_USER` | *(必须修改)* | KingBase 用户名 |
| `KINGBASE_PASSWORD` | *(必须修改)* | KingBase 密码 |
| `KINGBASE_SCHEMA` | `ywdata` | 业务数据 schema |
| `JCGKZX_MONITOR_SCHEMA` | `jcgkzx_monitor` | 聚合层 schema |
| `WCNR_SCHEDULER_ENABLED` | `1` | 是否启动评分/预警调度器 |
| `WCNR_SCHEDULER_BATCH_HOUR` | `3` | 日批评分小时 |
| `WCNR_SCHEDULER_ALERT_SCAN_MINUTES` | `5` | 预警规则扫描间隔 |

数据库初始化：

```powershell
uv run python scripts/run_migrations.py
```

---

## 部署方式一：Windows 10 Docker（内网服务器）

适用于 Windows 10 内网服务器，统一使用 Docker 部署，不再使用本机 Python 直接运行。

### 前提条件

- Windows 10 已安装并启用 Docker Desktop 或兼容的 Docker 环境
- 建议启用 Linux 容器模式，使用项目提供的 `docker-compose.yml` 启动
- 模型文件已按分类放入 `model/`：`model/yolo/production/biaochezhajiev2.pt`、`model/yolo/production/yolov8s-worldv2.pt`
- `static/dist/tailwind.css` 已存在；如修改过模板 class，在构建机上执行 `npm run build:css` 后再带入内网
- 共享数据目录、结果目录和 `jobs.sqlite3` 需按 Docker 挂载方式持久化

### 1. 准备镜像和配置

```powershell
cd multi-rider
cp .env.example app.env
```

根据实际环境修改 `app.env` 中的数据库、模型和目录配置；内网环境下保持 `YOLO_TELEMETRY=false`。

### 2. 启动服务

```powershell
docker compose up -d
```

服务默认监听 `0.0.0.0:5001`，浏览器访问：

```
http://localhost:5001/
```

局域网内其他设备通过本机 IP 访问：

```
http://本机IP:5001/
```

### 3. 常用运维命令

```powershell
docker compose ps
docker compose logs -f
docker compose restart
docker compose down
```

### 注意事项

- Windows 10 这里是 Docker 宿主机，不是 Python 直跑环境
- 防火墙需放通 5001 端口（入站规则），局域网其他设备才能访问
- `output/`、`upload_tmp/`、`train_runs/` 等目录应通过宿主机挂载保留数据

---

## 部署方式二：CentOS Stream 10 Docker（内网服务器）

适用于 CentOS Stream 10 内网服务器，统一使用 Docker 部署，推荐生产环境使用。

推荐使用项目根目录的 `docker-compose.yml` + `app.env` 同目录启动，不再要求把配置放到 `/opt`。

### 快速结论

1. 当前仓库内的 `instantclient_11_2/` 已切换为 Linux x86_64 版共享库，可直接打入 Linux Docker 镜像。
2. 当前仓库默认按 `python-oracledb` thick mode 运行；构建镜像前需先把 Linux x86_64 Instant Client 共享库放入 `instantclient_11_2/`，其中至少包含 `libclntsh.so.11.1`、`libnnz11.so`、`libociei.so`。
3. 模型文件不打入镜像，内网运行时由 `docker-compose.yml` 默认挂载同目录的 `./model`。
4. 离线部署建议直接参考 [docs/OFFLINE_DEPLOY_CENTOS_STREAM10.md](docs/OFFLINE_DEPLOY_CENTOS_STREAM10.md)。

### 最小部署步骤

```bash
# 联网构建机
npm install
npm run build:css
docker build --platform linux/amd64 -f ops/Dockerfile -t multi-rider:latest .
docker save -o multi-rider-latest.tar multi-rider:latest

# 内网主机（与 docker-compose.yml/app.env 放在同一目录）
sudo docker load -i multi-rider-latest.tar
cp .env.example app.env
mkdir -p runtime/data runtime/output runtime/face_data runtime/datasets runtime/train_runs runtime/upload_tmp model
[ -f runtime/data/jobs.sqlite3 ] || touch runtime/data/jobs.sqlite3
sudo docker compose up -d
```

访问地址：`http://服务器IP:5001/`

### 常用运维命令

```bash
sudo docker compose ps
sudo docker compose logs -f
sudo docker compose restart
sudo docker compose down
```

### 防火墙

```bash
# CentOS / RHEL（firewalld）
sudo firewall-cmd --permanent --add-port=5001/tcp
sudo firewall-cmd --reload

# Ubuntu / Debian（ufw）
sudo ufw allow 5001/tcp
```

---

## 两种部署方式对比

| 对比项 | Windows 10 Docker | CentOS Stream 10 Docker |
|---|---|---|
| 环境要求 | Docker Desktop 或兼容 Docker 环境 | Docker |
| 宿主机角色 | Windows 10 内网服务器 | CentOS Stream 10 内网服务器 |
| Instant Client | 由容器镜像提供 Linux `.so` 版 | 由容器镜像提供 Linux `.so` 版 |
| 适合场景 | 内网部署、统一容器化管理 | 生产部署、长期运行 |
| 开机自启 | Docker 自动重启策略 | `--restart unless-stopped` |
| 数据持久化 | 宿主机目录挂载 | 宿主机目录挂载 |
| 升级方式 | 替换镜像并重启容器 | 重建镜像替换容器 |
