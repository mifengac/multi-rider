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
├── app.py                   # Flask 入口，注册 Blueprint
├── config.py                # 全局配置（环境变量覆盖）
├── requirements.txt         # 直接依赖
├── requirements.lock        # uv 生成的完整锁文件
├── Dockerfile               # Linux Docker 镜像定义
├── db/
│   ├── oracle.py            # Oracle 连接与 SQL 构建
│   └── sqlite.py            # SQLite 任务历史持久化
├── routes/
│   ├── job_routes.py        # /  /start  /progress  /cancel  /jobs  /history
│   ├── file_routes.py       # /download/<job_id>
│   └── upload_routes.py     # /upload/start  /upload/progress  /upload/download
├── service/
│   ├── infer_service.py     # YOLO 模型加载与批量推理
│   ├── job_service.py       # Oracle 任务生命周期（内存 + SQLite）
│   └── upload_job_service.py# 上传任务生命周期（ZIP 解析、视频帧提取）
├── utils/
│   └── helpers.py           # 时间/文件名工具函数
├── templates/
│   ├── index.html           # 主页（双 Tab）
│   └── history.html         # 历史记录页
├── static/
│   └── tailwind.min.js      # Tailwind CSS 本地文件（内网无需 CDN）
├── model/                   # 模型文件（不入库）
├── output/                  # 推理结果 ZIP 输出目录
├── upload_tmp/              # 视频上传临时目录（推理后自动清理）
├── instantclient_11_2/      # Oracle Instant Client（不入库，Windows/Linux 版本不同）
└── deploy/
    └── app.env.example      # 环境变量模板
```

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

- Python 3.10 或以上（推荐通过官网离线安装包安装）
- Oracle Instant Client **Windows 版**（`.dll` 文件），解压到 `instantclient_11_2\`
  - 需包含 `oci.dll`、`oraocci11.dll`、`oraociei11.dll` 等
- 模型文件已放入 `model\`：`biaochezhajiev2.pt`、`yolov8s-worldv2.pt`
- `static\tailwind.min.js` 已存在（已包含在仓库）
- 建议使用 [uv](https://github.com/astral-sh/uv) 管理虚拟环境（也可用标准 `venv`）

### 1. 创建虚拟环境并安装依赖

```powershell
cd multi-rider

# 使用 uv（推荐）
uv venv .venv
.venv\Scripts\Activate.ps1
uv pip install -r requirements.txt

# 单独安装 torch CPU 版（从 PyTorch 官方离线包安装）
uv pip install torch==2.8.0+cpu torchvision==0.23.0+cpu `
    --index-url https://download.pytorch.org/whl/cpu
```

> 如果事先已下载 `.whl` 文件，可用 `uv pip install ./torch-*.whl` 离线安装。

### 2. 配置环境变量

在 PowerShell 中临时设置（每次启动前执行），或写入系统环境变量：

```powershell
$env:YOLO_TELEMETRY   = "false"
$env:ORACLE_HOST      = "oracledb.example.com"
$env:ORACLE_PASSWORD  = "你的数据库密码"
$env:FLASK_SECRET_KEY = "改成随机字符串"
# 其他变量按需修改，不设置则使用 config.py 中的默认值
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

### 前提条件（构建机，需能访问互联网或清华镜像源）

1. `model/biaochezhajiev2.pt` 和 `model/yolov8s-worldv2.pt` 已放入 `model/`
2. Oracle Instant Client **Linux 版**（`.so` 文件），解压到 `instantclient_11_2/`
   - 需包含 `libclntsh.so.11.1`
3. `static/tailwind.min.js` 已存在（已包含在仓库）
4. 构建机已安装 Docker

### 1. 构建镜像并导出

```bash
cd multi-rider

docker build -t multi-rider:latest .

# 导出为 tar 供离线传输
docker save -o multi-rider_latest.tar multi-rider:latest
sha256sum multi-rider_latest.tar > multi-rider_latest.tar.sha256
```

构建说明：
- 基础镜像 `python:3.10-slim-bullseye`，APT 使用清华镜像源
- torch/torchvision 使用 CPU-only wheel（PyTorch 官方 whl 索引）
- 其余依赖来自 `requirements.lock`（清华 PyPI 源）
- 构建时自动检查模型文件和 Instant Client，缺失则报错退出

### 2. 传输到内网服务器

将以下文件拷贝到内网服务器（U 盘或内网文件共享）：

```
multi-rider_latest.tar
multi-rider_latest.tar.sha256
deploy/app.env.example
```

### 3. 在内网服务器上部署

```bash
# 校验文件完整性
sha256sum -c multi-rider_latest.tar.sha256

# 导入镜像
sudo docker load -i multi-rider_latest.tar

# 准备目录和配置文件
sudo mkdir -p /opt/multi-rider/output /opt/multi-rider/upload_tmp
sudo cp app.env.example /opt/multi-rider/app.env
sudo vi /opt/multi-rider/app.env
# 至少修改以下两项：
#   ORACLE_PASSWORD=你的数据库密码
#   FLASK_SECRET_KEY=改成随机字符串

# 启动容器
sudo docker run -d \
  --name multi-rider \
  --restart unless-stopped \
  -p 5001:5001 \
  --env-file /opt/multi-rider/app.env \
  -v /opt/multi-rider/output:/app/output \
  multi-rider:latest
```

访问地址：

```
http://服务器IP:5001/
```

### 4. 更新容器

```bash
# 导入新镜像后
sudo docker stop multi-rider
sudo docker rm multi-rider
# 重新执行 docker run 命令
```

### 5. 常用运维命令

```bash
sudo docker ps                    # 查看容器状态
sudo docker logs -f multi-rider   # 查看实时日志
sudo docker restart multi-rider   # 重启容器
sudo docker stop multi-rider      # 停止容器
sudo docker rm -f multi-rider     # 删除容器
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
- `output/` 挂载到宿主机，容器重建后历史 ZIP 不丢失
- 上传任务进度存于容器内存，容器重启后运行中的上传任务状态会丢失
- `YOLO_TELEMETRY=false` 已在 Dockerfile ENV 中预设，无需手动添加

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
