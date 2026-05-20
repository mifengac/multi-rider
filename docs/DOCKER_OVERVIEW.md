# Docker 文件总览与离线部署流程

本文说明 multi-rider 的 Docker 构建、发布和内网运行关系。当前策略是：镜像内包含应用代码、Python 依赖、Oracle Instant Client 和已构建的 Tailwind CSS；模型文件不进入镜像，运行时由 `docker-compose.yml` 挂载。

## 一、Docker 相关文件职责

| 文件/目录 | 职责 | 关系与注意事项 |
|---|---|---|
| `ops/Dockerfile` | 唯一镜像构建入口 | 联网构建机使用 `docker build -f ops/Dockerfile ...`。保留 `static/dist/tailwind.css` 与 Oracle Instant Client 检查；不检查 `.pt` / `.onnx` 模型文件。 |
| `docker-compose.yml` | 唯一权威 Compose 配置 | 内网服务器只用已 `docker load` 的镜像启动；配置 `pull_policy: never`，不包含 `build:`，默认镜像为 `${MULTI_RIDER_IMAGE:-multi-rider:latest}`。 |
| `.dockerignore` | 控制构建上下文 | 排除运行数据、tar 包、测试目录、`node_modules/` 和模型二进制；保留 `model/README.md` 作为目录说明。 |
| `app.env` | 内网运行配置文件 | 由 `.env.example` 或 `ops/app.env.example` 复制后填写；`docker-compose.yml` 默认读取 `${APP_ENV_FILE:-./app.env}`。 |
| `model/` | 运行时模型挂载目录 | 不打入镜像，默认通过 `${MULTI_RIDER_MODEL_ROOT:-./model}:/app/model` 挂载；需包含 `yolo/production`、`yolo/foundation`、`insightface`、`assets` 等子目录。 |
| `instantclient_11_2/` | Oracle Thick Mode 客户端 | Linux x86_64 版本必须在构建前放入仓库根目录；`ops/Dockerfile` 默认检查 `libclntsh.so.11.1`、`libnnz11.so`、`libociei.so`。 |
| `static/dist/` | 生产前端静态 CSS 输出 | `static/dist/tailwind.css` 必须在构建前由 `npm install && npm run build:css` 生成，并打入镜像。 |

已删除的冲突入口：

- 根目录 `Dockerfile`：曾是不完整镜像定义，容易被 Compose 默认误用。
- `compose.yaml`：曾与 `docker-compose.yml` 的镜像、环境文件和挂载策略冲突。

## 二、从零构建可发布镜像

在联网构建机执行：

```bash
git checkout <目标分支>
git pull
```

准备 Linux x86_64 Oracle Instant Client：

```bash
ls instantclient_11_2/libclntsh.so.11.1
ls instantclient_11_2/libnnz11.so
ls instantclient_11_2/libociei.so
```

构建 Tailwind CSS：

```bash
npm install
npm run build:css
ls static/dist/tailwind.css
```

构建并导出镜像：

```bash
docker build --platform linux/amd64 -f ops/Dockerfile -t multi-rider:latest .
docker save -o multi-rider-latest.tar multi-rider:latest
```

建议发布包至少包含：

```text
multi-rider-latest.tar
docker-compose.yml
.env.example
docs/DEPLOY_INTRANET.md
model/                     # 若内网服务器没有同版本模型目录
```

## 三、内网服务器收到 tar 后的部署步骤

导入镜像：

```bash
docker load -i multi-rider-latest.tar
docker images | grep multi-rider
```

准备目录：

```bash
mkdir -p /opt/multi-rider
cd /opt/multi-rider
mkdir -p runtime/data runtime/output runtime/face_data runtime/datasets runtime/train_runs runtime/upload_tmp model
```

放置运行文件：

```text
/opt/multi-rider/docker-compose.yml
/opt/multi-rider/app.env
/opt/multi-rider/model/...
```

配置环境：

```bash
cp .env.example app.env
vim app.env
```

关键项：

```bash
MULTI_RIDER_IMAGE=multi-rider:latest
MULTI_RIDER_MODEL_ROOT=./model
FLASK_SECRET_KEY=<随机长字符串>
YOLO_TELEMETRY=false
```

启动服务：

```bash
APP_ENV_FILE=./app.env docker compose -f docker-compose.yml up -d
docker compose -f docker-compose.yml ps
docker compose -f docker-compose.yml logs -f web
```

验证：

```bash
curl http://localhost:5001/healthz
```

## 四、常见问题排查

| 常见错误 | 根因 | 修复 |
|---|---|---|
| Docker build 报 `Missing model/...` | 使用了旧版 `ops/Dockerfile` 或误用了根目录旧 `Dockerfile`，仍在构建阶段检查外置模型 | 更新到当前版本；确认根目录没有 `Dockerfile`，并用 `docker build -f ops/Dockerfile ...` 构建。 |
| Docker build 报 `Missing built Tailwind CSS at static/dist/tailwind.css` | 构建镜像前未生成生产 CSS，或 `.dockerignore` 没有保留该文件 | 在联网构建机执行 `npm install && npm run build:css`，确认 `static/dist/tailwind.css` 存在后重新构建。 |
| 容器日志提示 `scripts/run_migrations.py not in image, skipping migrations` | 镜像来自旧版 Dockerfile，未执行 `COPY scripts ./scripts`；当前 Compose 会跳过迁移并继续启动 | 用当前 `ops/Dockerfile` 重新构建镜像；确认构建日志包含 `COPY scripts ./scripts`。 |
| `image not found` / `pull access denied` | `docker-compose.yml` 需要的 `MULTI_RIDER_IMAGE` 与 `docker load` 后的实际 tag 不一致；内网又不能拉取镜像 | 执行 `docker images | grep multi-rider`，把实际 `REPOSITORY:TAG` 写入 `app.env` 的 `MULTI_RIDER_IMAGE`，或用 `docker tag` 改成 `multi-rider:latest`。 |
| Compose 尝试 build，出现 `failed to read dockerfile` 或 `transferring dockerfile: 2B` | 部署目录残留旧版 Compose，包含 `build:` 或默认寻找根目录 `Dockerfile` | 用当前 `docker-compose.yml` 覆盖部署目录；确认 `docker compose -f docker-compose.yml config` 输出中没有 `build:`。 |
