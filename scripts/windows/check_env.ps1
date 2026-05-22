$ErrorActionPreference = "Continue"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $ProjectRoot
$LogDir = Join-Path $ProjectRoot "runtime\logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$LogPath = Join-Path $LogDir "check_env.log"

function Write-Check($Name, $Ok, $Detail) {
    $status = if ($Ok) { "OK" } else { "FAIL" }
    $line = "[{0}] {1}: {2} - {3}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $status, $Name, $Detail
    Write-Host $line
    Add-Content -Path $LogPath -Value $line -Encoding UTF8
}

Write-Check "project_root" $true $ProjectRoot
Write-Check "uv" ([bool](Get-Command uv -ErrorAction SilentlyContinue)) ((uv --version 2>$null) -join " ")

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
Write-Check "python_venv" (Test-Path $Python) $Python

if (Test-Path $Python) {
    $Code = @"
import importlib
mods = ["flask", "cv2", "PIL", "onnxruntime", "ultralytics"]
for name in mods:
    try:
        importlib.import_module(name)
        print(f"OK {name}")
    except Exception as exc:
        print(f"FAIL {name}: {exc}")
from shared.health import get_health_report
print(get_health_report())
"@
    $Output = & $Python -c $Code 2>&1
    foreach ($line in $Output) {
        Add-Content -Path $LogPath -Value $line -Encoding UTF8
        Write-Host $line
    }
}

Write-Host "环境检查完成：$LogPath"

