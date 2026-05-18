# 内网离线部署指南

> 适用场景：在有网络的电脑打包 Docker 镜像，通过 U 盘/内网传输至无网络的内网服务器部署。

---

## 一、前置条件

| 项目 | 要求 |
|------|------|
| 打包机（互联网） | Docker Desktop 已安装，能拉取 Docker Hub 镜像 |
| 部署机（内网） | Docker + Docker Compose 已安装，Linux（CentOS/Ubuntu）|
| 模型文件 | `model/` 目录下的 `.pt`、`.onnx` 文件齐全 |
| Oracle Instant Client | `instantclient_11_2/` Linux 版（libclntsh.so.11.1） |
| Tailwind CSS | 已在本地执行 `npm run build:css` 生成 `static/dist/tailwind.css` |

---

## 二、互联网电脑：打包镜像

### 第 1 步：拉取代码，确认文件齐全

```bash
git checkout feature/ai-analyst-rag
git pull

# 确认关键文件存在
ls model/biaochezhajiev2.pt
ls model/yolov8s-worldv2.pt
ls model/det_10g.onnx
ls model/w600k_r50.onnx
ls static/dist/tailwind.css          # 如果没有，运行: npm run build:css
ls instantclient_11_2/libclntsh.so.11.1
```

### 第 2 步：构建镜像

```bash
docker build -t multi-rider:latest -f ops/Dockerfile .
```

> 首次构建约需 10-20 分钟（主要是下载 PyTorch CPU 版本）。

### 第 3 步：导出镜像为文件

```bash
docker save multi-rider:latest | gzip > multi-rider-latest.tar.gz

# 确认文件大小（正常约 5-8 GB）
ls -lh multi-rider-latest.tar.gz
```

### 第 4 步：拷贝到 U 盘或内网传输

将以下文件一起拷贝：
```
multi-rider-latest.tar.gz   ← 镜像文件
docker-compose.yml           ← Compose 配置
.env.example                 ← 环境变量模板（下一步按此创建 app.env）
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
# 创建运行时数据目录
mkdir -p runtime/data runtime/output runtime/face_data runtime/datasets runtime/train_runs runtime/upload_tmp
```

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

# 启动（后台运行）
APP_ENV_FILE=./app.env docker compose up -d

# 查看启动日志
docker compose logs -f web
```

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
docker build -t multi-rider:latest -f ops/Dockerfile .
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
| `Missing model/xxx.pt` | 模型文件未放入 `model/` | 构建前确认所有模型文件存在 |
| `Missing instantclient_11_2/libclntsh.so.11.1` | 缺少 Linux 版 Oracle 客户端 | 下载 Linux x86_64 版 Instant Client 11.2 |
| AI 研判无响应 | RUIZHI_API_KEY 未配置或网络不通 | 检查内网到锐智平台的连通性 |
| KingBase 连接失败 | 防火墙或账号问题 | 确认 54321 端口可达，账号权限正确 |
| 端口被占用 | 5001 端口已使用 | 修改 docker-compose.yml 中的 ports 映射 |

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
