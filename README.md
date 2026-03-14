# multi_rider

这是一个基于 Flask + YOLO 的图片筛选服务：

- 按时间范围和小时段从 Oracle 查询图片 URL
- 下载图片并批量推理
- 保留满足置信度阈值的图片
- 将结果按日期写入 ZIP 并提供浏览器下载

注意：仓库默认**不提交大二进制运行文件**。以下内容需要你在本地自行放入对应目录后再构建镜像：

- `model/biaochezhajiev2.pt`
- Linux 版 Oracle Instant Client 文件，放到 `instantclient_11_2/`

本仓库已经补齐了面向内网 `CentOS Stream 10` 的离线部署交付物：

- `Dockerfile`: 使用清华 APT / PyPI 源构建 CPU 镜像
- `deploy/app.env.example`: 容器环境变量模板
- `deploy/load-and-run.sh`: 在内网服务器上导入镜像并启动容器

## 1. 在当前构建机打包并导出镜像

在仓库根目录执行：

```bash
mkdir -p dist
docker build -t multi-rider:20260313-cpu .
docker save -o dist/multi-rider_20260313_cpu.tar multi-rider:20260313-cpu
sha256sum dist/multi-rider_20260313_cpu.tar > dist/multi-rider_20260313_cpu.tar.sha256
```

构建说明：

- 基础镜像为 `python:3.10-slim-bullseye`
- APT 与普通 Python 包使用清华源
- `torch/torchvision` 使用 CPU-only wheel，避免打入 CUDA 依赖
- 其他 Python 依赖使用 `requirements.lock` 固定版本
- 当前默认构建为 CPU 镜像，适合大多数内网服务器
- 如果缺少模型文件或 Oracle Instant Client，构建会直接失败并给出提示

## 2. 需要交付到内网的文件

将以下内容复制到内网 `CentOS Stream 10` 服务器：

- `dist/multi-rider_20260313_cpu.tar`
- `dist/multi-rider_20260313_cpu.tar.sha256`
- `deploy/app.env.example`
- `deploy/load-and-run.sh`

建议将文件放到同一个目录，例如：

```bash
/opt/multi-rider-delivery/
```

## 3. 内网服务器部署步骤

前提：

- 内网服务器已经安装 Docker
- 具备 `sudo` 权限
- 服务器能够访问 Oracle 数据库地址

### 3.1 准备部署目录

```bash
mkdir -p /opt/multi-rider-delivery
```

将导出的镜像和 `deploy/` 目录拷贝到该目录。

### 3.2 首次生成环境文件

进入交付目录后执行：

```bash
cd /opt/multi-rider-delivery
sha256sum -c ./dist/multi-rider_20260313_cpu.tar.sha256
sudo bash deploy/load-and-run.sh ./dist/multi-rider_20260313_cpu.tar
```

首次执行时，脚本会：

- 创建 `/opt/multi-rider/conf/app.env`
- 创建 `/opt/multi-rider/output`
- 提示你先修改环境文件，不会直接启动服务

### 3.3 编辑环境文件

编辑：

```bash
sudo vi /opt/multi-rider/conf/app.env
```

至少要修改这两个值：

```env
ORACLE_PASSWORD=你的数据库密码
FLASK_SECRET_KEY=改成随机字符串
```

如果数据库地址、服务名、用户名与默认值不同，也一并修改。

### 3.4 启动容器

再次执行：

```bash
cd /opt/multi-rider-delivery
sudo bash deploy/load-and-run.sh ./dist/multi-rider_20260313_cpu.tar
```

脚本会自动：

- `docker load` 导入镜像
- 删除同名旧容器
- 以 `--restart unless-stopped` 方式启动新容器
- 将宿主机 `/opt/multi-rider/output` 挂载到容器 `/app/output`

默认访问地址：

```text
http://服务器IP:5001/
```

## 4. 常用运维命令

查看容器：

```bash
sudo docker ps
```

查看日志：

```bash
sudo docker logs -f multi-rider
```

停止容器：

```bash
sudo docker stop multi-rider
```

删除容器：

```bash
sudo docker rm -f multi-rider
```

## 5. 如果启用了防火墙

放通 5001 端口：

```bash
sudo firewall-cmd --permanent --add-port=5001/tcp
sudo firewall-cmd --reload
```

## 6. 部署注意事项

- 宿主机是 CentOS 没问题，容器内部运行的是 Debian 用户态
- 本地准备的 `instantclient_11_2` 必须是 Linux `.so` 版本
- 任务状态保存在进程内存中，容器重启后运行中的任务状态会丢失
- 筛选输出 ZIP 会保存在宿主机 `/opt/multi-rider/output`
- 当前镜像为 CPU-only，不需要 CUDA 库，也不需要 NVIDIA 运行时
- 如果后续有多台内网服务器，建议再接一个内网私有镜像仓库，避免手工分发 tar
