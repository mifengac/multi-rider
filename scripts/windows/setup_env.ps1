param(
    [string]$PythonVersion = "3.11",
    [string]$Wheelhouse = "",
    [switch]$Offline
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $ProjectRoot

$LogDir = Join-Path $ProjectRoot "runtime\logs"
$ConfigDir = Join-Path $ProjectRoot "runtime\config"
$DataDir = Join-Path $ProjectRoot "runtime\data"
$ModelDir = Join-Path $ProjectRoot "runtime\models"
New-Item -ItemType Directory -Force -Path $LogDir,$ConfigDir,$DataDir,$ModelDir | Out-Null
$LogPath = Join-Path $LogDir "setup.log"

function Write-Log($Message) {
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Write-Host $line
    Add-Content -Path $LogPath -Value $line -Encoding UTF8
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv 未安装或不在 PATH 中，请先运行 scripts/windows/install_uv.ps1"
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Log "creating virtual environment with Python $PythonVersion"
    & uv venv .venv --python $PythonVersion 2>&1 | Tee-Object -FilePath $LogPath -Append
} else {
    Write-Log ".venv already exists, skip venv creation"
}

if ($Offline) {
    if (-not $Wheelhouse) {
        throw "离线安装需要传入 -Wheelhouse wheelhouse目录"
    }
    $ResolvedWheelhouse = Resolve-Path $Wheelhouse
    Write-Log "installing dependencies from wheelhouse: $ResolvedWheelhouse"
    & uv pip install --python ".venv\Scripts\python.exe" --no-index --find-links $ResolvedWheelhouse -r requirements.txt 2>&1 | Tee-Object -FilePath $LogPath -Append
} else {
    Write-Log "installing dependencies from requirements.txt"
    & uv pip install --python ".venv\Scripts\python.exe" -r requirements.txt 2>&1 | Tee-Object -FilePath $LogPath -Append
}

$ExampleEnv = Join-Path $ConfigDir "app.env.example"
$EnvFile = Join-Path $ConfigDir "app.env"
if ((Test-Path $ExampleEnv) -and -not (Test-Path $EnvFile)) {
    Copy-Item -LiteralPath $ExampleEnv -Destination $EnvFile
    Write-Log "created runtime/config/app.env from example"
}

Write-Log "initializing local SQLite tables"
& ".venv\Scripts\python.exe" -c "from shared.db.sqlite import init_db; init_db(); print('sqlite initialized')" 2>&1 | Tee-Object -FilePath $LogPath -Append
Write-Log "setup finished"

