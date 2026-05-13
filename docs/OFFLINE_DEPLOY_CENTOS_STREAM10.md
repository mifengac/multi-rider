# CentOS Stream 10 内网离线部署说明

本文档适用于将当前项目部署到无互联网的 CentOS Stream 10 主机。部署方式为：在可联网机器上构建镜像并导出 tar 包，在内网主机上通过 `docker load` 导入，再使用同目录下的 `compose.yaml` 和 `.env` 启动。

## 1. 结论先说

- 当前仓库内的 `instantclient_11_2/` 已替换为 **Linux x86_64 版 Oracle Instant Client 共享库**。
- 该目录包含 `libclntsh.so.11.1`、`libocci.so.11.1`、`libociei.so` 等 Linux `.so` 文件，可直接打入 Docker 镜像。
- 当前 Docker 镜像默认启用 `python-oracledb` thick mode，并通过 `ORACLE_IC_DIR=/app/instantclient_11_2` 使用这套客户端。
- 如后续需要回退到 thin mode，只需在同目录 `.env` 中把 `ORACLE_USE_THICK_MODE=false`。

## 2. 需要传输到内网主机的文件

最低需要传输以下文件到同一目录，例如 `~/multi-rider-deploy/`：

- `multi-rider-centos-stream10.tar`
- `neo4j-5.20-community.tar`
- `compose.yaml`
- `.env`
- `neo4j/plugins/`

如需保留历史数据或提前导入业务数据，再额外传输：

- `data/jobs.sqlite3`
- `data/face_data/`
- `data/datasets/`
- `data/train_runs/`
- `data/output/`

如需在内网继续替换或新增模型，也可以额外传输：

- `model/`

但按当前默认方案，镜像构建时已经把现有 `model/` 目录打入镜像，**首次部署不是必须再单独传 `model/`**。

## 3. 联网机器上打包镜像

以下命令在当前项目根目录执行。

### Windows PowerShell

```powershell
docker build --platform linux/amd64 -f ops/Dockerfile -t multi-rider:centos-stream10 .
docker save -o .\multi-rider-centos-stream10.tar multi-rider:centos-stream10
docker pull neo4j:5.20-community
docker save -o .\neo4j-5.20-community.tar neo4j:5.20-community
New-Item -ItemType Directory -Force -Path .\neo4j\plugins | Out-Null
docker run -d --name neo4j-plugin-preload `
    -e NEO4J_AUTH=neo4j/temp12345 `
    -e NEO4J_PLUGINS='["apoc", "graph-data-science"]' `
    -v ${PWD}\neo4j\plugins:/plugins `
    neo4j:5.20-community
docker logs -f neo4j-plugin-preload
docker stop neo4j-plugin-preload
docker rm neo4j-plugin-preload
Get-ChildItem .\neo4j\plugins
Get-FileHash .\multi-rider-centos-stream10.tar -Algorithm SHA256
```

### Linux Bash

```bash
docker build --platform linux/amd64 -f ops/Dockerfile -t multi-rider:centos-stream10 .
docker save -o ./multi-rider-centos-stream10.tar multi-rider:centos-stream10
docker pull neo4j:5.20-community
docker save -o ./neo4j-5.20-community.tar neo4j:5.20-community
mkdir -p ./neo4j/plugins
docker run -d --name neo4j-plugin-preload \
    -e NEO4J_AUTH=neo4j/temp12345 \
    -e NEO4J_PLUGINS='["apoc", "graph-data-science"]' \
    -v $(pwd)/neo4j/plugins:/plugins \
    neo4j:5.20-community
docker logs -f neo4j-plugin-preload
docker stop neo4j-plugin-preload
docker rm neo4j-plugin-preload
ls ./neo4j/plugins
sha256sum ./multi-rider-centos-stream10.tar
```

## 4. 内网主机目录建议

建议不要放到 `/opt`。直接放在当前用户有权限的目录，例如：

```bash
mkdir -p ~/multi-rider-deploy
cd ~/multi-rider-deploy
```

建议目录结构如下：

```text
multi-rider-deploy/
├── multi-rider-centos-stream10.tar
├── neo4j-5.20-community.tar
├── compose.yaml
├── .env
├── neo4j/
│   ├── plugins/
│   ├── data/
│   └── logs/
└── data/
    ├── jobs.sqlite3
    ├── output/
    ├── upload_tmp/
    ├── face_data/
    ├── datasets/
    └── train_runs/
```

## 5. 生成和修改 `.env`

项目根目录已经提供 `.env.example`，先复制一份：

```bash
cp .env.example .env
```

重点至少修改以下内容：

- `FLASK_SECRET_KEY`
- `ORACLE_HOST`
- `ORACLE_PORT`
- `ORACLE_SERVICE`
- `ORACLE_USER`
- `ORACLE_PASSWORD`
- `SMS_ORACLE_*`
- `KINGBASE_*`
- `NEO4J_PASSWORD`
- `NEO4J_AUTH`
- `DISPATCH_CLIENT_SECRET`
- `DISPATCH_SMS_PASSWORD`

说明：容器内应用访问 Neo4j 时应保持 `NEO4J_URI=bolt://neo4j:7687`，不要改成 `localhost`；`NEO4J_AUTH` 中的密码部分必须与 `NEO4J_PASSWORD` 保持一致。

如果当前内网部署仅用于演示，可先把以下变量改成更保守的值：

```dotenv
DISPATCH_MOCK_MODE=true
FACE_SQL_ENABLED=false
```

## 6. 内网主机导入镜像并启动

以下命令均在 `~/multi-rider-deploy` 目录执行。

### 6.1 导入镜像

```bash
sudo docker load -i multi-rider-centos-stream10.tar
sudo docker load -i neo4j-5.20-community.tar
```

### 6.2 准备数据目录

```bash
mkdir -p data/output data/upload_tmp data/face_data data/datasets data/train_runs
mkdir -p neo4j/data neo4j/logs neo4j/plugins
[ -f data/jobs.sqlite3 ] || touch data/jobs.sqlite3
```

如果你已经从联网机器复制了 `neo4j/plugins/`，这里不要覆盖该目录内容。

### 6.3 启动服务

```bash
sudo docker compose up -d
```

如果你的环境还是旧版独立命令，则改用：

```bash
sudo docker-compose up -d
```

### 6.4 查看运行状态

```bash
sudo docker compose ps
sudo docker compose logs -f
```

## 7. 停止、重启、升级

### 停止

```bash
sudo docker compose down
```

### 重启

```bash
sudo docker compose restart
```

### 用新镜像升级

把新的 `multi-rider-centos-stream10.tar` 覆盖到同目录后执行：

```bash
sudo docker load -i multi-rider-centos-stream10.tar
sudo docker compose up -d
```

## 8. 端口访问

默认端口为 `5001`。浏览器访问：

```text
http://服务器IP:5001/
```

如需直接访问 Neo4j Browser：

```text
http://服务器IP:7474/
```

如需从外部驱动或浏览器建立 Bolt 连接，还需要放通 `7687` 端口。

如果需要修改宿主机端口，可在 `.env` 中调整：

```dotenv
HOST_PORT=5001
NEO4J_HTTP_PORT=7474
NEO4J_BOLT_PORT=7687
```

## 9. 关于 Oracle Instant Client 的最终建议

### 当前仓库里的 `instantclient_11_2/`

当前目录已经是 Linux 共享库版本，至少包含：

- `libclntsh.so.11.1`
- `libnnz11.so`
- `libocci.so.11.1`
- `libociei.so`

本次重新打包的镜像会直接把该目录复制到容器内 `/app/instantclient_11_2`。

### 什么时候切回 thin mode

如果你在实际 Oracle 连通性测试中发现 thick mode 反而有兼容问题，可在 `.env` 中改为：

```dotenv
ORACLE_USE_THICK_MODE=false
```

然后重新执行：

```bash
sudo docker compose up -d
```

## 10. 额外提醒

- 当前 `model/` 目录里已有 `biaochezhajiev2.pt`、`yolov8s-worldv2.pt`、`det_10g.onnx`、`w600k_r50.onnx`，镜像构建会校验这 4 个文件。
- 如果后续要在内网使用 YOLO-World 的自定义文本提示词，建议额外准备 `mobileclip_blt.ts` 和 `ViT-B-32.pt`，否则自定义 prompt 相关能力可能退化或失败。
- 首次启动如果只是做演示，建议先关闭真实下发和人脸库 SQL 同步，等页面跑通后再逐项打开。
- `compose.yaml` 中的 Neo4j 服务默认从本地 `neo4j/plugins/` 读取 APOC/GDS 插件，这是为了适配内网离线环境；如果不预先准备该目录，图算法接口将无法运行。
