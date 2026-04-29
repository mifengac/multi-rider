# Windows 10 内网离线安装说明

本文档适用于将当前项目整体带入内网 Windows 10 机器后进行离线安装和启动。

## 适用前提

- 目标机器为 Windows 10 x64
- Python 版本为 3.12 x64
- 当前项目根目录已经包含 `wheels\` 离线依赖目录
- 当前项目根目录的 `wheels\` 下已经包含 `clip-1.0-py3-none-any.whl`
- `instantclient_11_2\` 为 Windows 版 Oracle Instant Client 11.2
- `model\` 下已经放好所需模型文件

## 需要一并带入内网的内容

建议直接拷贝整个项目目录，至少要包含以下内容：

- 项目源码
- `wheels\`
- `instantclient_11_2\`
- `model\`
- `static\dist\tailwind.css`
- `requirements.txt`
- `requirements-dev.txt`
- `requirements.lock`

说明：

- `CLIP\` 源码目录不是运行必须项，真正安装时使用的是 `wheels\clip-1.0-py3-none-any.whl`
- 如果只需要运行，不需要测试，可不安装 `requirements-dev.txt`
- 前端样式已由联网构建机用 npm 预编译到 `static\dist\tailwind.css`，内网运行机器不需要 Node.js。

## 目录检查

进入项目根目录后，先确认以下关键文件存在：

```powershell
Get-ChildItem .\wheels\clip-1.0-py3-none-any.whl
Get-ChildItem .\wheels\*.whl | Select-Object -First 5
Get-ChildItem .\requirements.txt
Get-ChildItem .\requirements.lock
Get-ChildItem .\instantclient_11_2
Get-ChildItem .\model
```

## 创建虚拟环境

推荐使用 `uv`：

```powershell
uv venv .venv --python 3.12
```

如果目标机器没有 `uv`，也可以使用标准 `venv`：

```powershell
py -3.12 -m venv .venv
```

## 离线安装依赖

### 方案一：安装运行环境

```powershell
uv pip install --python .\.venv\Scripts\python.exe --no-index --find-links .\wheels -r requirements.txt
```

### 方案二：安装开发和测试环境

```powershell
uv pip install --python .\.venv\Scripts\python.exe --no-index --find-links .\wheels -r requirements-dev.txt
```

### 方案三：严格按锁文件安装运行环境

```powershell
uv pip install --python .\.venv\Scripts\python.exe --no-index --find-links .\wheels -r requirements.lock
```

说明：

- `requirements.txt` 已经引用本地 `wheels\clip-1.0-py3-none-any.whl`
- `requirements-dev.txt` 会先包含 `requirements.txt`，再安装 `pytest`
- `requirements.lock` 适合需要固定版本的部署场景

如果不用 `uv`，也可使用 `pip`：

```powershell
.\.venv\Scripts\python.exe -m pip install --no-index --find-links .\wheels -r requirements.txt
```

## Oracle Instant Client 检查

`instantclient_11_2\` 必须是 Windows 版本，并至少包含以下 DLL：

- `oci.dll`
- `oraocci11.dll`
- `oraociei11.dll`

项目默认通过 `ORACLE_IC_DIR=.\instantclient_11_2` 加载客户端库。

## 模型文件检查

建议至少确认以下文件存在：

- `model\biaochezhajiev2.pt`
- `model\yolov8s-worldv2.pt`
- `model\mobileclip_blt.ts`
- `model\ViT-B-32.pt`
- `model\det_10g.onnx`
- `model\w600k_r50.onnx`

## 环境变量配置

可以直接参考 `ops\app.env.example`。在 PowerShell 中，至少建议设置或确认以下变量：

```powershell
$env:YOLO_TELEMETRY   = "false"
$env:ORACLE_HOST      = "10.45.100.147"
$env:ORACLE_PORT      = "1521"
$env:ORACLE_SERVICE   = "yfgxpt"
$env:ORACLE_USER      = "yfzagk"
$env:ORACLE_PASSWORD  = "请改成实际密码"
$env:FLASK_SECRET_KEY = "请改成随机字符串"
```

如果只做本机验证，通常还会临时关闭部分外部依赖：

```powershell
$env:FACE_SQL_ENABLED   = "false"
$env:DISPATCH_MOCK_MODE = "true"
```

## 运行测试

如果已经安装 `requirements-dev.txt`，可以先跑一遍测试：

```powershell
$env:FACE_SQL_ENABLED   = "false"
$env:DISPATCH_MOCK_MODE = "true"
$env:YOLO_TELEMETRY     = "false"
.\.venv\Scripts\python.exe -m pytest
```

## 启动服务

```powershell
.\.venv\Scripts\python.exe .\app.py
```

默认访问地址：

```text
http://localhost:5001/
```

## `worker.py` 是什么

`worker.py` 是一个独立的后台任务进程，用来轮询 SQLite 中的 `task_queue` 表，并把较重的任务放到 Flask Web 进程之外执行。

它的设计目标是：

- 避免长任务阻塞 Web 进程
- 让任务在 Web 进程重启后仍可继续被消费
- 支持把不同类型的重任务拆到不同进程里跑

当前 `worker.py` 内置支持的任务类型有：

- `train`
- `auto_annotate`
- `face_library`

说明：

- `worker.py` 和 `app.py` 使用同一套项目配置，并共享同一个 SQLite 数据库文件
- 如果你额外设置了 `SQLITE_DB_PATH`，要确保 `app.py` 和 `worker.py` 指向同一个库文件
- 当前仓库默认的训练、批量预标注、人脸库任务，仍主要由 Web 进程内后台线程直接启动
- 所以按当前代码状态，`worker.py` 不是启动系统的硬性前置条件，而是独立任务队列模式的补充能力

## `worker.py` 如何使用

如果你希望单独运行任务消费者，请在项目根目录打开第二个 PowerShell 窗口执行：

### 消费全部任务类型

```powershell
.\.venv\Scripts\python.exe .\worker.py
```

### 只消费训练任务

```powershell
.\.venv\Scripts\python.exe .\worker.py --type train
```

### 只消费批量预标注任务

```powershell
.\.venv\Scripts\python.exe .\worker.py --type auto_annotate
```

### 只消费人脸库任务

```powershell
.\.venv\Scripts\python.exe .\worker.py --type face_library
```

### 调整空闲轮询间隔

```powershell
.\.venv\Scripts\python.exe .\worker.py --interval 5
```

上面的 `--interval 5` 表示空闲时每 5 秒轮询一次任务队列。

## `worker.py` 的推荐使用方式

如果你准备采用“Web 服务 + 独立任务进程”的方式运行，建议顺序如下：

1. 在第一个终端启动 `app.py`
2. 在第二个终端启动 `worker.py`
3. 确保两个进程使用同一份环境变量配置
4. 需要拆分负载时，可再额外启动不同 `--type` 的 worker

例如：

```powershell
# 终端 1
.\.venv\Scripts\python.exe .\app.py

# 终端 2
.\.venv\Scripts\python.exe .\worker.py --type train

# 终端 3
.\.venv\Scripts\python.exe .\worker.py --type face_library
```

`worker.py` 支持 `Ctrl+C` 正常退出。收到退出信号后，会尽量先完成当前正在处理的任务，再结束进程。

## 常见问题

### 1. 提示找不到 `clip`

检查 `wheels\` 目录下是否存在 `clip-1.0-py3-none-any.whl`，并确认安装命令使用了 `--find-links .\wheels`。

### 2. 提示找不到 Oracle DLL

检查 `instantclient_11_2\` 是否为 Windows 版，并确认其中包含 `oci.dll` 等必需文件。

### 3. 提示模型文件不存在

检查 `model\` 目录是否完整，尤其是 YOLO、CLIP 和人脸识别相关模型文件。

### 4. 内网机器不能联网

这是预期场景。安装时不要使用在线源，直接使用本文中的 `--no-index --find-links .\wheels` 命令即可。

### 5. 启动了 `app.py` 还要不要启动 `worker.py`

按当前仓库实现，通常不是必须的，因为现有训练、批量预标注和人脸库任务默认仍可由 Web 进程内后台线程启动。

只有在你明确要使用独立任务队列消费模式，或者后续把任务提交逻辑改为写入 `task_queue` 后，才需要长期单独启动 `worker.py`。

## 推荐安装顺序

1. 拷贝整个项目目录到目标机器
2. 检查 `instantclient_11_2\` 和 `model\`
3. 创建 `.venv`
4. 执行离线依赖安装
5. 配置环境变量
6. 运行测试
7. 启动 `app.py`
