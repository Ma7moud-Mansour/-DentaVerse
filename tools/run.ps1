param([switch]$Vision, [switch]$Bluetooth)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$runtime = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $runtime)) { throw 'Run tools/setup.ps1 first.' }
if (-not (Test-Path -LiteralPath (Join-Path $projectRoot 'frontend\dist\index.html'))) { throw 'Build the frontend first with tools/setup.ps1.' }
if ($Vision -and -not (Test-Path -LiteralPath (Join-Path $projectRoot 'models\pose_landmarker_lite.task'))) { throw 'Run tools/setup.ps1 -WithVision first.' }
$children = @()
$runLogDir = Join-Path $projectRoot '.review\runtime'
New-Item -ItemType Directory -Force -Path $runLogDir | Out-Null
Push-Location -LiteralPath $projectRoot
try {
    if ($Bluetooth) {
        $children += Start-Process -FilePath $runtime -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -ArgumentList @('-m','backend.workers.bluetooth') -RedirectStandardOutput (Join-Path $runLogDir 'bluetooth.out.log') -RedirectStandardError (Join-Path $runLogDir 'bluetooth.err.log')
    }
    if ($Vision) {
        $children += Start-Process -FilePath $runtime -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -ArgumentList @('-m','backend.workers.vision') -RedirectStandardOutput (Join-Path $runLogDir 'vision.out.log') -RedirectStandardError (Join-Path $runLogDir 'vision.err.log')
    }
    Write-Host 'Open http://127.0.0.1:8000 . Press Ctrl+C to stop this local session.'
    & $runtime -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
} finally {
    foreach ($child in $children) { if (-not $child.HasExited) { Stop-Process -Id $child.Id -ErrorAction SilentlyContinue } }
    Pop-Location
}
