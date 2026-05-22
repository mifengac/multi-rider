# Windows 10 使用 uv 部署启动

本项目当前按 Python Web 应用直接部署，不制作 EXE。推荐在 Windows 10 64 位机器上使用 `uv` 创建虚拟环境、安装依赖，并用 PowerShell 脚本启动 Web 和 worker。

## 1. 准备组件

- Windows 10 64 位。
- PowerShell 5.1 或以上。
- uv。
- Microsoft Visual C++ Redistributable。
- Git，可选。
- FFmpeg，可选，用于视频处理场景。
- 项目模型文件，放入 `runtime/models/`。

## 2. 安装 uv

在线安装：

```powershell
scripts\windows\install_uv.ps1
```

离线安装：

```powershell
scripts\windows\install_uv.ps1 -OfflineUvPath D:\offline\uv.exe
```

## 3. 创建虚拟环境并安装依赖

在线安装：

```powershell
scripts\windows\setup_env.ps1
```

离线安装：

```powershell
scripts\windows\setup_env.ps1 -Offline -Wheelhouse D:\offline\wheelhouse
```

离线 wheelhouse 可在有网机器上生成：

```powershell
uv pip download -r requirements.txt -d wheelhouse
```

## 4. 配置

首次执行 `setup_env.ps1` 后会生成：

```text
runtime/config/app.env
```

按现场环境修改数据库、模型、端口等配置。不要把真实账号密码提交到代码仓库。

模型建议放在：

```text
runtime/models/
```

## 5. 启动

启动 Web：

```powershell
scripts\windows\start_app.ps1 -OpenBrowser
```

启动 worker：

```powershell
scripts\windows\start_worker.ps1
```

停止：

```powershell
scripts\windows\stop_app.ps1
```

日志位置：

```text
runtime/logs/
```

## 6. 检查环境

```powershell
scripts\windows\check_env.ps1
```

检查结果写入：

```text
runtime/logs/check_env.log
```

## 7. 验收

- `setup_env.ps1` 可重复执行。
- `check_env.ps1` 能识别 uv、Python、关键 Python 包。
- `start_app.ps1` 启动后首页可访问。
- `start_worker.ps1` 启动后任务队列可消费。
- 缺模型或数据库未配置时，页面/日志给出明确提示。

