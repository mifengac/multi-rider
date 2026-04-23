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
├── requirements.txt         # 直接依赖
├── requirements.lock        # uv 生成的完整锁文件
├── wheels/                  # 内网离线安装使用的本地 wheel 包目录
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

> 如果事先已下载 `.whl` 文件，可用 `uv pip install .\wheels\torch-*.whl` 离线安装。

> 完整的 Windows 10 内网离线安装说明见 `docs/OFFLINE_INSTALL_WINDOWS10.md`。离线 wheel 默认放在项目根目录下的 `wheels/`。

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
python app.py
```

服务默认监听 `0.0.0.0:5001`，浏览器访问：

```
http://localhost:5001/
```

局域网内其他设备通过本机 IP 访问：

```
http://本机IP:5001/
```

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

## 部署方式二：Linux + Docker（内网服务器）

适用于 CentOS / Debian / Ubuntu 等 Linux 内网服务器，推荐生产环境使用。

推荐使用项目根目录新增的 `compose.yaml` + `.env` 同目录启动，不再要求把配置放到 `/opt`。

### 快速结论

1. 当前仓库内的 `instantclient_11_2/` 已切换为 Linux x86_64 版共享库，可直接打入 Linux Docker 镜像。
2. Docker 镜像默认启用 `python-oracledb` thick mode；如需切回 thin mode，可在 `.env` 中把 `ORACLE_USE_THICK_MODE=false`。
3. 离线部署建议直接参考 [docs/OFFLINE_DEPLOY_CENTOS_STREAM10.md](docs/OFFLINE_DEPLOY_CENTOS_STREAM10.md)。

### 最小部署步骤

```bash
# 联网构建机
docker build --platform linux/amd64 -f ops/Dockerfile -t multi-rider:centos-stream10 .
docker save -o multi-rider-centos-stream10.tar multi-rider:centos-stream10

# 内网主机（与 compose.yaml/.env 放在同一目录）
sudo docker load -i multi-rider-centos-stream10.tar
cp .env.example .env
mkdir -p data/output data/upload_tmp data/face_data data/datasets data/train_runs
[ -f data/jobs.sqlite3 ] || touch data/jobs.sqlite3
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

| 对比项 | Windows 10 直接运行 | Linux Docker |
|---|---|---|
| 环境要求 | Python 3.10 + uv | Docker |
| Instant Client | Windows `.dll` 版 | 镜像内已包含 Linux `.so` 版 |
| 适合场景 | 临时演示、开发调试 | 生产部署、长期运行 |
| 开机自启 | 任务计划程序 / NSSM | `--restart unless-stopped` |
| 数据持久化 | 本地目录 | 宿主机目录挂载 |
| 升级方式 | 拉取代码重启 | 重建镜像替换容器 |
