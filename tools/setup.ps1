param([switch]$WithVision)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $projectRoot
try {
    if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
        python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Create the environment with Python 3.12, then retry.' }
    }
    $requirements = if ($WithVision) { 'backend\requirements.txt' } else { 'backend\requirements-core.txt' }
    & '.\.venv\Scripts\python.exe' -m pip install --timeout 180 -r $requirements
    if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
    if ($WithVision) {
        & '.\.venv\Scripts\python.exe' tools/download_pose_model.py
        if ($LASTEXITCODE -ne 0) { throw 'Pose model download failed.' }
        & '.\.venv\Scripts\python.exe' tools/download_hand_model.py
        if ($LASTEXITCODE -ne 0) { throw 'Hand model download failed.' }
    }
    Push-Location -LiteralPath frontend
    try {
        # Recent Node versions can use the Windows certificate store without disabling TLS checks.
        $previousSystemCa = $env:NODE_USE_SYSTEM_CA
        $env:NODE_USE_SYSTEM_CA = '1'
        if (Test-Path -LiteralPath package-lock.json) { npm.cmd ci --no-audit --no-fund }
        else { npm.cmd install --no-audit --no-fund }
        if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
        npm.cmd run build
        if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
    } finally { $env:NODE_USE_SYSTEM_CA = $previousSystemCa; Pop-Location }
    Write-Host 'Setup complete. Run: powershell -File tools/run.ps1'
} finally { Pop-Location }
