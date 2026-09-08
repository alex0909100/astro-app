$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$cloudflared = (Get-Command cloudflared -ErrorAction SilentlyContinue).Source
if (-not $cloudflared -and (Test-Path "C:\Program Files (x86)\cloudflared\cloudflared.exe")) {
  $cloudflared = "C:\Program Files (x86)\cloudflared\cloudflared.exe"
}
if (-not $cloudflared) {
  throw "cloudflared не найден. Установите его с https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
}
if (-not (Test-Path ".env")) {
  throw "Создайте файл .env на основе .env.example и укажите BOT_TOKEN."
}

$envLines = Get-Content ".env"
foreach ($line in $envLines) {
  if ($line -match "^\s*([^#=]+)=(.*)$") {
    [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
  }
}

$app = Start-Process python -ArgumentList "app.py" -PassThru -WindowStyle Minimized
$tunnelLog = Join-Path $PSScriptRoot ".cloudflared.log"
$tunnelErrorLog = Join-Path $PSScriptRoot ".cloudflared-error.log"
Remove-Item $tunnelLog -ErrorAction SilentlyContinue
Remove-Item $tunnelErrorLog -ErrorAction SilentlyContinue
$tunnel = Start-Process $cloudflared -ArgumentList "tunnel --protocol http2 --url http://127.0.0.1:$($env:PORT)" -RedirectStandardOutput $tunnelLog -RedirectStandardError $tunnelErrorLog -PassThru -WindowStyle Minimized

$publicUrl = $null
for ($attempt = 0; $attempt -lt 30 -and -not $publicUrl; $attempt++) {
  Start-Sleep -Seconds 1
  if ((Test-Path $tunnelLog) -or (Test-Path $tunnelErrorLog)) {
    $allTunnelOutput = ((Get-Content $tunnelLog -Raw -ErrorAction SilentlyContinue) + (Get-Content $tunnelErrorLog -Raw -ErrorAction SilentlyContinue))
    $match = [regex]::Match($allTunnelOutput, "https://[a-z0-9-]+\.trycloudflare\.com")
    if ($match.Success) { $publicUrl = $match.Value }
  }
}
if (-not $publicUrl) {
  Stop-Process -Id $tunnel.Id -Force
  Stop-Process -Id $app.Id -Force
  throw "Cloudflare Tunnel не выдал публичный URL. Проверьте .cloudflared.log."
}

Write-Host "Mini App URL: $publicUrl"
Write-Host "Откройте @BotFather -> Bot Settings -> Menu Button и укажите этот URL."
Write-Host "Запускаю бота. Для остановки нажмите Ctrl+C."
$env:WEB_APP_URL = $publicUrl
python bot.py

Stop-Process -Id $tunnel.Id -Force -ErrorAction SilentlyContinue
Stop-Process -Id $app.Id -Force -ErrorAction SilentlyContinue
