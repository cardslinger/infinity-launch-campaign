$ErrorActionPreference = 'SilentlyContinue'
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -ErrorAction SilentlyContinue
if (-not $root) { $root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path }
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$web = Join-Path $root 'web'
$portFile = Join-Path $root 'launch-port.txt'
$port = 8765
if (Test-Path $portFile) { $port = [int](Get-Content -LiteralPath $portFile -Raw) }
$py = (Get-Command py -ErrorAction SilentlyContinue)
if ($py) {
  Start-Process -WindowStyle Hidden -FilePath 'py' -ArgumentList @('-3','-m','http.server',"$port",'--bind','127.0.0.1') -WorkingDirectory $web
  Start-Sleep -Milliseconds 400
  Start-Process "http://127.0.0.1:$port/index.html"
} else {
  Start-Process (Join-Path $web 'index.html')
}
