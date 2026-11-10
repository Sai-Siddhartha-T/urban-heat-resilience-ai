$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$workDir = Join-Path $repoRoot 'work'
New-Item -ItemType Directory -Force -Path (Join-Path $workDir 'npm-cache') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $workDir 'pip-cache') | Out-Null

$env:npm_config_cache = Join-Path $repoRoot 'work/npm-cache'
$env:PIP_CACHE_DIR = Join-Path $repoRoot 'work/pip-cache'

if (-not (Test-Path '.venv')) {
    python -m venv .venv
}

.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
npm --prefix frontend ci
npm --prefix frontend run build
if (-not (Test-Path '.env')) {
    Copy-Item .env.example .env
}

$env:PYTHONPATH = Join-Path $repoRoot 'backend'
$env:MPLCONFIGDIR = Join-Path $repoRoot 'work/matplotlib'
New-Item -ItemType Directory -Force -Path $env:MPLCONFIGDIR | Out-Null

& .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
