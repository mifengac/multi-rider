$ErrorActionPreference = "Continue"
Set-Location "C:\Users\Administrator\Desktop\cursor\multi-rider"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$logPath = "C:\Users\Administrator\Desktop\cursor\multi-rider\docs\0520_debugV3\codex_run_round6_live.log"
$promptPath = "C:\Users\Administrator\Desktop\cursor\multi-rider\docs\0520_debugV3\codex_round6_prompt.txt"
$startTs = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
"=== codex round6 start at $startTs ===" | Out-File -FilePath $logPath -Encoding utf8
$promptText = Get-Content $promptPath -Raw -Encoding utf8
"--- prompt length: $($promptText.Length) chars ---" | Out-File -FilePath $logPath -Encoding utf8 -Append
$promptText | & codex exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check - *>&1 | Out-File -FilePath $logPath -Encoding utf8 -Append
$endTs = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
"=== codex round6 end at $endTs ===" | Out-File -FilePath $logPath -Encoding utf8 -Append
