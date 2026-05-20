# 内网离线部署指南

> 适用场景：在有网络的电脑打包 Docker 镜像，通过 U 盘/内网传输至无网络的内网服务器部署。

---

## 一、前置条件

| 项目 | 要求 |
|------|------|
| 打包机（互联网） | Docker Desktop 已安装，能拉取 Docker Hub 镜像 |
| 部署机（内网） | Docker + Docker Compose 已安装，Linux（CentOS/Ubuntu）|
| 模型文件 | 内网运行目录提供 `model/`，或通过 `MULTI_RIDER_MODEL_ROOT` 指向模型目录 |
| Oracle Instant Client | `instantclient_11_2/` Linux 版（libclntsh.so.11.1） |
| Tailwind CSS | 构建镜像前必须执行 `npm install && npm run build:css` 生成 `static/dist/tailwind.css` |

---

## 二、互联网电脑：打包镜像

### 第 1 步：拉取代码，确认文件齐全

```bash
git checkout feature/ai-analyst-rag
git pull

# 确认关键构建文件存在
ls instantclient_11_2/libclntsh.so.11.1
ls instantclient_11_2/libnnz11.so
ls instantclient_11_2/libociei.so
```

### 第 2 步：构建 Tailwind CSS（必须在 docker build 前执行）

```bash
npm install
npm run build:css
ls static/dist/tailwind.css
```

> `static/dist/tailwind.css` 必须打入镜像；内网运行容器时不安装 Node.js，也不现场构建 Tailwind。

### 第 3 步：构建镜像

```bash
docker build --platform linux/amd64 -t multi-rider:latest -f ops/Dockerfile .
```

> 首次构建约需 10-20 分钟（主要是下载 PyTorch CPU 版本）。

### 第 4 步：导出镜像为文件

```bash
docker save multi-rider:latest | gzip > multi-rider-latest.tar.gz

# 确认文件大小（正常约 5-8 GB）
ls -lh multi-rider-latest.tar.gz
```

### 第 5 步：拷贝到 U 盘或内网传输

将以下文件一起拷贝：
```
multi-rider-latest.tar.gz   ← 镜像文件
docker-compose.yml           ← Compose 配置
.env.example                 ← 环境变量模板（下一步按此创建 app.env）
model/                       ← 运行时模型目录（若内网服务器已有同版本模型，可不重复拷贝）
docs/DEPLOY_INTRANET.md      ← 本文档
```

---

## 三、内网服务器：导入并启动

### 第 1 步：导入镜像

```bash
# 将 .tar.gz 传到服务器后执行
docker load < multi-rider-latest.tar.gz

# 确认镜像已导入
docker images | grep multi-rider
```

### 第 2 步：准备运行目录

```bash
mkdir -p /opt/multi-rider
cd /opt/multi-rider

# 将 docker-compose.yml 放到这里
# 创建运行时数据目录和默认模型挂载目录
mkdir -p runtime/data runtime/output runtime/face_data runtime/datasets runtime/train_runs runtime/upload_tmp model
```

将模型文件放入 `/opt/multi-rider/model`，保持 `model/yolo/production`、`model/yolo/foundation`、`model/insightface`、`model/assets` 这类目录结构；如果模型在其他目录，在 `app.env` 中设置 `MULTI_RIDER_MODEL_ROOT=/实际/model/目录`。

### 第 3 步：配置环境变量

```bash
cp .env.example app.env
vim app.env   # 按下面说明填写
```

**必填项清单（重点）：**

```bash
# Flask 安全密钥（随机字符串，不能用默认值）
FLASK_SECRET_KEY=换成一个随机长字符串

# Oracle 业务数据库（原有配置，不变）
ORACLE_HOST=10.45.100.147
ORACLE_PASSWORD=实际密码

# KingBase 管控业务库（新增）
KINGBASE_HOST=10.2.x.x          # KingBase 数据库 IP
KINGBASE_PORT=54321
KINGBASE_DB=security             # 数据库名
KINGBASE_USER=实际用户名
KINGBASE_PASSWORD=实际密码

# 锐智 AI 平台（新增）
RUIZHI_API_KEY=sk-1cac5cc...    # 你已有的 API Key
RUIZHI_BASE_URL=https://10.2.164.106/v2
RUIZHI_KB_NAME=wcnr_qincai_law  # 知识库名（首次用后改为实际名称）
```

### 第 4 步：启动服务

```bash
cd /opt/multi-rider

# 关键：app.env 里 MULTI_RIDER_IMAGE 必须等于
# docker images | grep multi-rider 看到的 REPOSITORY:TAG（默认 multi-rider:latest）。
# 如果导入后实际 tag 是 multi-rider:offline-20260520，可：
#   echo "MULTI_RIDER_IMAGE=multi-rider:offline-20260520" >> app.env
# 或临时改 tag：
#   docker tag multi-rider:offline-20260520 multi-rider:latest

# 启动（后台运行）
APP_ENV_FILE=./app.env docker compose up -d

# 查看启动日志
docker compose logs -f web
```

> 注意：内网部署目录**不需要** Dockerfile 或源码，compose 已配置 `pull_policy: never` 且不再尝试 build，只用导入好的镜像。
> 如果遇到 `failed to read dockerfile: ... no such file or directory`，说明部署目录里残留了一份旧版 `docker-compose.yml`（带 `build:` 字段），用本仓库新版覆盖即可。

### 第 5 步：验证服务

```bash
# 健康检查
curl http://localhost:5001/healthz

# 预期返回：{"ok": true, ...}
```

浏览器访问：`http://服务器IP:5001`

---

## 四、首次启动后：初始化知识库

知识库需要在能访问锐智 AI 平台的环境中初始化。

```bash
# 在内网服务器上（需能访问锐智 AI 平台）
python scripts/test_kb.py \
  --api-key sk-你的key \
  --insecure \
  --kb-name wcnr_qincai_law

# 成功后把 KB_NAME 填入 app.env 的 RUIZHI_KB_NAME
```

---

## 五、初始化数据库表

首次部署时需在 KingBase 中建表：

```bash
# 在能访问 KingBase 的机器上执行
psql -h 10.2.x.x -p 54321 -U 用户名 -d security -f scripts/ddl_create_tables.sql

# 初始化人员底池（从 Oracle 数据同步）
psql -h 10.2.x.x -p 54321 -U 用户名 -d security -f scripts/etl_init_target_pool.sql
```

---

## 六、更新部署（后续版本）

```bash
# 互联网电脑：重新打包
git pull
npm install
npm run build:css
docker build --platform linux/amd64 -t multi-rider:latest -f ops/Dockerfile .
docker save multi-rider:latest | gzip > multi-rider-v$(date +%Y%m%d).tar.gz

# 内网服务器：替换镜像
docker compose down
docker load < multi-rider-v20260518.tar.gz
APP_ENV_FILE=./app.env docker compose up -d
```

---

## 七、常见问题

| 问题 | 原因 | 解决方法 |
|------|------|----------|
| 容器启动后提示模型文件不存在 | `docker-compose.yml` 挂载的 `model/` 目录缺文件，或 `MULTI_RIDER_MODEL_ROOT` 指向错误 | 在内网运行目录补齐模型文件，或修正 `app.env` 中的 `MULTI_RIDER_MODEL_ROOT` |
| `Missing built Tailwind CSS at static/dist/tailwind.css` | 构建镜像前未执行 Tailwind 构建 | 在联网构建机执行 `npm install && npm run build:css` 后重新 `docker build` |
| `Missing instantclient_11_2/libclntsh.so.11.1` | 缺少 Linux 版 Oracle 客户端 | 下载 Linux x86_64 版 Instant Client 11.2 |
| AI 研判无响应 | RUIZHI_API_KEY 未配置或网络不通 | 检查内网到锐智平台的连通性 |
| KingBase 连接失败 | 防火墙或账号问题 | 确认 54321 端口可达，账号权限正确 |
| 端口被占用 | 5001 端口已使用 | 修改 docker-compose.yml 中的 ports 映射 |
| `failed to read dockerfile` / `transferring dockerfile: 2B` | 部署目录用了旧版 `docker-compose.yml`（含 `build:`），且镜像 tag 不匹配触发了 build 回退 | 用本仓库新版 `docker-compose.yml`（无 `build:`、`pull_policy: never`）覆盖，并把 `MULTI_RIDER_IMAGE` 设成 `docker images` 实际看到的 tag |
| `image not found` / `pull access denied` | 镜像 tag 与 `MULTI_RIDER_IMAGE` 不一致 | `docker images \| grep multi-rider` 看 REPOSITORY:TAG，写回 `app.env` 的 `MULTI_RIDER_IMAGE` |

---

## 八、目录结构说明

```
/opt/multi-rider/
├── docker-compose.yml
├── app.env                  ← 实际配置（不要提交 git）
└── runtime/
    ├── data/                ← SQLite 数据库 + 输出文件
    ├── output/              ← 检测结果
    ├── face_data/           ← 人脸库数据
    ├── datasets/            ← 训练数据集
    ├── train_runs/          ← 训练输出
    └── upload_tmp/          ← 上传临时文件
```
