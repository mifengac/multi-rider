param(
    [string]$OfflineUvPath = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$LogDir = Join-Path $ProjectRoot "runtime\logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$LogPath = Join-Path $LogDir "install_uv.log"

function Write-Log($Message) {
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Write-Host $line
    Add-Content -Path $LogPath -Value $line -Encoding UTF8
}

if (Get-Command uv -ErrorAction SilentlyContinue) {
    Write-Log "uv already available: $((uv --version) -join ' ')"
    exit 0
}

$TargetDir = Join-Path $env:USERPROFILE ".local\bin"
New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null

if ($OfflineUvPath) {
    $ResolvedUv = Resolve-Path $OfflineUvPath
    Copy-Item -LiteralPath $ResolvedUv -Destination (Join-Path $TargetDir "uv.exe") -Force
    Write-Log "uv copied from offline package: $ResolvedUv"
} else {
    Write-Log "installing uv from official installer"
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
}

$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($UserPath -notlike "*$TargetDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$UserPath;$TargetDir", "User")
    Write-Log "added uv target dir to user PATH: $TargetDir"
}

Write-Log "uv installation finished. Reopen PowerShell if uv is still not found."

