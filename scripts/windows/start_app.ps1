param(
    [switch]$OpenBrowser
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $ProjectRoot
$LogDir = Join-Path $ProjectRoot "runtime\logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    throw "未找到 .venv，请先运行 scripts/windows/setup_env.ps1"
}

$OutLog = Join-Path $LogDir "app.stdout.log"
$ErrLog = Join-Path $LogDir "app.stderr.log"
$PidFile = Join-Path $ProjectRoot "runtime\app.pid"

if (Test-Path $PidFile) {
    $ExistingPid = Get-Content $PidFile -ErrorAction SilentlyContinue
    if ($ExistingPid -and (Get-Process -Id $ExistingPid -ErrorAction SilentlyContinue)) {
        Write-Host "Web 服务已在运行，PID=$ExistingPid"
        exit 0
    }
}

$Process = Start-Process -FilePath $Python -ArgumentList "app.py" -WorkingDirectory $ProjectRoot -RedirectStandardOutput $OutLog -RedirectStandardError $ErrLog -PassThru -WindowStyle Hidden
Set-Content -Path $PidFile -Value $Process.Id -Encoding UTF8
Write-Host "Web 服务已启动，PID=$($Process.Id)"
Write-Host "日志：$OutLog / $ErrLog"
Write-Host "访问地址默认见 runtime/config/app.env 中 APP_HOST/APP_PORT，默认 http://127.0.0.1:5001"

if ($OpenBrowser) {
    Start-Process "http://127.0.0.1:5001"
}

