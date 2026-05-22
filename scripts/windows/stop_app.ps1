$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$PidFiles = @(
    Join-Path $ProjectRoot "runtime\app.pid",
    Join-Path $ProjectRoot "runtime\worker.pid"
)

foreach ($PidFile in $PidFiles) {
    if (-not (Test-Path $PidFile)) {
        Write-Host "PID 文件不存在：$PidFile"
        continue
    }
    $PidValue = (Get-Content $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
    if (-not $PidValue) {
        Remove-Item -LiteralPath $PidFile -Force
        continue
    }
    $Process = Get-Process -Id $PidValue -ErrorAction SilentlyContinue
    if ($Process) {
        Write-Host "停止进程 PID=$PidValue"
        Stop-Process -Id $PidValue -Force
    } else {
        Write-Host "进程不存在，清理 PID 文件：$PidValue"
    }
    Remove-Item -LiteralPath $PidFile -Force
}

Write-Host "停止完成。"

