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
| `general` | `model/yolov8s-worldv2.pt` | YOLO-World 开放词表，支持英文提示词（留空=自动检测） |
| `bczj` | `model/biaochezhajiev2.pt` | 私有训练模型，针对飙车炸街场景，支持类别索引过滤 |

> **注意**：模型文件不随仓库提交，需手动放入 `model/` 目录。

## 项目结构

```
multi-rider/
├── app.py                   # Flask 入口，注册各业务模块 Blueprint
├── worker.py                # 后台任务 Worker 入口
├── docker-compose.yml       # Ubuntu Docker Compose 编排：Web + Worker
├── requirements.txt         # 直接依赖
├── requirements.lock        # uv 生成的完整锁文件
├── modules/
│   ├── detection/           # 检测模块：数据库检测、本地上传、结果下载
│   ├── face/                # 人脸模块：人脸库、识别、身份核验
│   ├── dispatch/            # 下发模块：认证、队列、短信、任务下发
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
│   └── tailwind.min.js      # Tailwind CSS 本地文件（内网无需 CDN）
├── docs/                    # 方案文档、交接记录、设计稿、辅助脚本
├── ops/
│   ├── Dockerfile           # Linux Docker 镜像定义
│   ├── app.env.example      # Windows 10 + uv 本地运行环境变量模板
│   └── app.env.ubuntu.example # Ubuntu 22 + Docker Compose 环境变量模板
├── model/                   # 模型文件（不入库）
├── output/                  # 推理结果 ZIP 输出目录
├── upload_tmp/              # 上传源文件暂存目录（Worker 完成后按历史清理策略删除）
└── instantclient_11_2/      # Oracle Instant Client（不入库，Windows/Linux 版本不同）
```

## 代码导航

- 检测相关后端：`modules/detection/`
- 人脸识别与身份核验：`modules/face/`
- 任务下发与短信：`modules/dispatch/`
- 训练、预标注、模型注册：`modules/training/`
- 全局配置与环境变量：`shared/config/config.py`
- 共享数据库接入：`shared/db/`
- 共享推理能力：`shared/inference/infer_service.py`
- 工作台页面壳层：`templates/index.html`
- 模块页面模板：`templates/modules/`
- 模块前端脚本：`static/modules/`
- 运维与部署材料：`ops/`
- 方案、交接、设计稿：`docs/`

## 运行目录维护

- `output/`：检测结果 ZIP 和 `_results/` 清单目录。需要保留历史结果时不要直接清空；如仅做演示，可定期删除旧任务目录与旧 ZIP。
- `upload_tmp/`：上传源文件暂存目录。为支持 Worker 重试，文件不会在任务结束瞬间删除，而是随旧任务清理策略统一删除。
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
| `TORCH_NUM_THREADS` | `0` | PyTorch CPU 线程数，`0` 表示不主动设置 |
| `OPENCV_NUM_THREADS` | `0` | OpenCV CPU 线程数，`0` 表示不主动设置 |
| `VIDEO_FRAME_INTERVAL` | `5` | 视频每隔 N 帧取一帧 |
| `MAX_UPLOAD_BYTES` | `524288000` (500 MB) | 上传文件大小上限 |
| `SQLITE_DB_PATH` | `./jobs.sqlite3` | SQLite 历史、任务状态与队列数据库 |
| `OUTPUT_DIR` | `./output` | 结果 ZIP 目录 |
| `DATASETS_DIR` | `./datasets` | 训练数据集目录 |
| `FACE_DATA_DIR` | `./face_data` | 人脸库照片、特征和缓存 |
| `TRAIN_RUNS_DIR` | `./train_runs` | 训练运行产物目录 |
| `YOLO_TELEMETRY` | `false` | **禁用 ultralytics 联网检测**（内网必须保持 false） |

---

## 部署方式一：Windows 10 直接运行（无 Docker）

适用于开发机、临时演示机，或没有 Docker 环境的内网 Windows 主机。

### 前提条件

- Python 3.12（推荐通过官网离线安装包安装，或使用已存在的 `.venv`）
- Oracle Instant Client **Windows 版**（`.dll` 文件），解压到 `instantclient_11_2`
  - 需包含 `oci.dll`、`oraocci11.dll`、`oraociei11.dll` 等
- 模型文件已放入 `model\`：`biaochezhajiev2.pt`、`yolov8s-worldv2.pt`
- `static\tailwind.min.js` 已存在（已包含在仓库）
- 建议使用 [uv](https://github.com/astral-sh/uv) 管理虚拟环境（也可用标准 `venv`）

### 1. 创建虚拟环境并安装依赖

```powershell
cd multi-rider

# 使用 uv（推荐）
uv venv .venv --python 3.12
uv pip install --python .\.venv\Scripts\python.exe -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
uv pip install --python .\.venv\Scripts\python.exe -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements-dev.txt

# 单独安装 torch CPU 版（从 PyTorch 官方离线包安装）
uv pip install --python .\.venv\Scripts\python.exe torch==2.8.0+cpu torchvision==0.23.0+cpu `
    --index-url https://download.pytorch.org/whl/cpu
```

> 如果事先已下载 `.whl` 文件，可用 `uv pip install ./torch-*.whl` 离线安装。

### 1.1 运行测试

```powershell
$env:FACE_SQL_ENABLED = "false"
$env:DISPATCH_MOCK_MODE = "true"
$env:YOLO_TELEMETRY = "false"
uv pip install --python .\.venv\Scripts\python.exe -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```

### 2. 配置环境变量

在 PowerShell 中临时设置（每次启动前执行），或写入系统环境变量：

```powershell
$env:YOLO_TELEMETRY   = "false"
$env:ORACLE_HOST      = "oracledb.example.com"
$env:ORACLE_PASSWORD  = "你的数据库密码"
$env:FLASK_SECRET_KEY = "改成随机字符串"
# 其他变量按需修改，不设置则使用 shared/config/config.py 中的默认值
```

### 3. 启动服务

```powershell
.\.venv\Scripts\python.exe app.py
```

训练、批量预标注和人脸库同步/重建任务采用独立 Worker 执行。另开一个 PowerShell 窗口，启动：

```powershell
.\.venv\Scripts\python.exe worker.py
```

如需只处理某一类任务，可按类型启动：

```powershell
.\.venv\Scripts\python.exe worker.py --type detection
.\.venv\Scripts\python.exe worker.py --type upload
.\.venv\Scripts\python.exe worker.py --type train
.\.venv\Scripts\python.exe worker.py --type auto_annotate
.\.venv\Scripts\python.exe worker.py --type face_library
```

未启动 Worker 时，数据库检测、本地上传检测、训练、批量预标注和人脸库任务会停留在 `queued`，这是预期状态。

服务默认监听 `0.0.0.0:5001`，浏览器访问：

```
http://localhost:5001/
```

局域网内其他设备通过本机 IP 访问：

```
http://本机IP:5001/
```

健康检查：

```
http://localhost:5001/healthz
```

返回 `200` 表示 SQLite、输出目录、模型文件和任务队列状态正常；返回 `503` 表示至少一项检查失败。

任务队列诊断：

```
http://localhost:5001/diagnostics/task-queue
```

该接口和工作台里的“任务队列诊断”页只读展示 Worker 队列状态、陈旧运行任务和最近任务列表，不会重置、重试或删除任务。

### 4. 开机自启（可选）

可使用 Windows 任务计划程序，创建"系统启动时"触发的任务，操作为：

```
程序：C:\path\to\multi-rider\.venv\Scripts\python.exe
参数：C:\path\to\multi-rider\app.py
起始位置：C:\path\to\multi-rider
```

或使用 [NSSM](https://nssm.cc/) 将其注册为 Windows 服务。

### 注意事项

- `instantclient_11_2\` 必须是 **Windows `.dll`** 版本，不能用 Linux `.so` 版本
- 防火墙需放通 5001 端口（入站规则），局域网其他设备才能访问
- `output\` 目录下的 ZIP 文件需定期清理，默认无自动清理

---

## 部署方式二：Ubuntu 22 + Docker Compose（内网服务器）

适用于后续部署到 Ubuntu 22 内网服务器长期运行。推荐使用 Docker Compose 同时管理 Web 和 Worker，不再手工 `docker exec` 进入容器启动 Worker。

### 前提条件（构建机，需能访问互联网或清华镜像源）

1. `model/biaochezhajiev2.pt` 和 `model/yolov8s-worldv2.pt` 已放入 `model/`
2. Oracle Instant Client **Linux 版**（`.so` 文件），解压到 `instantclient_11_2/`
   - 需包含 `libclntsh.so.11.1`
3. `static/tailwind.min.js` 已存在（已包含在仓库）
4. 构建机已安装 Docker / Docker Compose

### 1. 构建镜像并导出

```bash
cd multi-rider

docker build -f ops/Dockerfile -t multi-rider:latest .

# 导出为 tar 供离线传输
docker save -o multi-rider_latest.tar multi-rider:latest
sha256sum multi-rider_latest.tar > multi-rider_latest.tar.sha256
```

构建说明：
- 基础镜像 `python:3.10-slim-bullseye`，APT 使用清华镜像源
- torch/torchvision 使用 CPU-only wheel（PyTorch 官方 whl 索引）
- 其余依赖来自 `requirements.lock`（清华 PyPI 源）
- 构建时自动检查模型文件和 Instant Client，缺失则报错退出
- 镜像内默认使用 Linux 路径：`/app/data`、`/app/output`、`/app/datasets`、`/app/face_data`、`/app/train_runs`、`/app/upload_tmp`

### 2. 传输到内网服务器

将以下文件拷贝到内网服务器（U 盘或内网文件共享）：

```
multi-rider_latest.tar
multi-rider_latest.tar.sha256
docker-compose.yml
ops/app.env.ubuntu.example
```

### 3. 在 Ubuntu 服务器上部署

```bash
# 校验文件完整性
sha256sum -c multi-rider_latest.tar.sha256

# 导入镜像
sudo docker load -i multi-rider_latest.tar

# 准备目录和配置文件
sudo mkdir -p /opt/multi-rider
sudo cp docker-compose.yml /opt/multi-rider/docker-compose.yml
sudo cp ops/app.env.ubuntu.example /opt/multi-rider/app.env
cd /opt/multi-rider
sudo vi /opt/multi-rider/app.env
# 至少修改以下几项：
#   ORACLE_PASSWORD=你的数据库密码
#   FLASK_SECRET_KEY=改成随机字符串
#   DISPATCH_CLIENT_SECRET=下发平台密钥
#   DISPATCH_SMS_PASSWORD=短信平台密码

# 一条命令启动 Web + Worker
sudo docker compose up -d
```

访问地址：

```
http://服务器IP:5001/
```

健康检查：

```
http://服务器IP:5001/healthz
```

任务队列诊断：

```
http://服务器IP:5001/diagnostics/task-queue
```

Compose 会启动两个容器：

| 容器 | 命令 | 作用 |
|---|---|---|
| `multi-rider-web` | `python app.py` | 页面和 API，只负责创建任务、查询状态 |
| `multi-rider-worker` | `python worker.py` | 执行数据库检测、本地上传检测、训练、批量预标注、人脸库任务 |

Worker 不需要进入容器手工运行；Compose 会自动启动并在异常退出后重启。

默认数据目录在 `/opt/multi-rider/runtime/`：

```
/opt/multi-rider/runtime/data/jobs.sqlite3
/opt/multi-rider/runtime/output/
/opt/multi-rider/runtime/datasets/
/opt/multi-rider/runtime/face_data/
/opt/multi-rider/runtime/train_runs/
/opt/multi-rider/runtime/upload_tmp/
```

### 4. 更新容器

```bash
# 导入新镜像后，在 /opt/multi-rider 下执行
sudo docker compose up -d
```

### 5. 常用运维命令

```bash
sudo docker compose ps              # 查看 Web / Worker 状态
sudo docker compose logs -f web      # 查看 Web 日志
sudo docker compose logs -f worker   # 查看 Worker 日志
sudo docker compose restart worker   # 单独重启 Worker
sudo docker compose restart web      # 单独重启 Web
sudo docker compose down             # 停止 Web + Worker
```

### 6. 防火墙

```bash
# CentOS / RHEL（firewalld）
sudo firewall-cmd --permanent --add-port=5001/tcp
sudo firewall-cmd --reload

# Ubuntu / Debian（ufw）
sudo ufw allow 5001/tcp
```

### 注意事项

- `instantclient_11_2/` 必须是 **Linux `.so`** 版本（容器内为 Debian 用户态）
- `runtime/` 挂载到宿主机，容器重建后 SQLite、历史 ZIP、数据集、人脸库和训练产物不丢失
- 上传检测任务状态已持久化到 SQLite；Worker 重启后会按队列状态继续处理或重试
- `YOLO_TELEMETRY=false` 已在 Dockerfile ENV 中预设，无需手动添加
- 16 核 CPU 无 GPU 环境建议先保持一个 Worker；训练任务最好放在低峰期运行

---

## 两种部署方式对比

| 对比项 | Windows 10 直接运行 | Linux Docker |
|---|---|---|
| 环境要求 | Python 3.10 + uv | Docker |
| Instant Client | Windows `.dll` 版 | Linux `.so` 版 |
| 适合场景 | 临时演示、开发调试 | 生产部署、长期运行 |
| 开机自启 | 任务计划程序 / NSSM | `--restart unless-stopped` |
| 数据持久化 | 本地目录 | 宿主机目录挂载 |
| 升级方式 | 拉取代码重启 | 重建镜像替换容器 |
