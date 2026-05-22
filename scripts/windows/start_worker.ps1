$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $ProjectRoot
$LogDir = Join-Path $ProjectRoot "runtime\logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    throw "未找到 .venv，请先运行 scripts/windows/setup_env.ps1"
}

$OutLog = Join-Path $LogDir "worker.stdout.log"
$ErrLog = Join-Path $LogDir "worker.stderr.log"
$PidFile = Join-Path $ProjectRoot "runtime\worker.pid"

if (Test-Path $PidFile) {
    $ExistingPid = Get-Content $PidFile -ErrorAction SilentlyContinue
    if ($ExistingPid -and (Get-Process -Id $ExistingPid -ErrorAction SilentlyContinue)) {
        Write-Host "Worker 已在运行，PID=$ExistingPid"
        exit 0
    }
}

$Process = Start-Process -FilePath $Python -ArgumentList "worker.py" -WorkingDirectory $ProjectRoot -RedirectStandardOutput $OutLog -RedirectStandardError $ErrLog -PassThru -WindowStyle Hidden
Set-Content -Path $PidFile -Value $Process.Id -Encoding UTF8
Write-Host "Worker 已启动，PID=$($Process.Id)"
Write-Host "日志：$OutLog / $ErrLog"

