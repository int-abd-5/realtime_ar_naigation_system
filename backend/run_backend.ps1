$ErrorActionPreference = "Stop"

$venv = ".venv"
if (-not (Test-Path $venv)) {
  python -m venv $venv
}

& "$venv\\Scripts\\python.exe" -m pip install --upgrade pip
& "$venv\\Scripts\\python.exe" -m pip install -r requirements.txt

if (-not $env:NAV_LOCALIZATION_MODE) { $env:NAV_LOCALIZATION_MODE = "hybrid" }
if (-not $env:NAV_BACKEND_HOST) { $env:NAV_BACKEND_HOST = "0.0.0.0" }
if (-not $env:NAV_BACKEND_PORT) { $env:NAV_BACKEND_PORT = "8000" }
if (-not $env:NAV_VISUAL_MAX_CANDIDATES) { $env:NAV_VISUAL_MAX_CANDIDATES = "32" }
if (-not $env:NAV_VISUAL_MIN_INLIERS) { $env:NAV_VISUAL_MIN_INLIERS = "6" }
if (-not $env:NAV_VISUAL_MATCH_RATIO) { $env:NAV_VISUAL_MATCH_RATIO = "0.90" }

& "$venv\\Scripts\\python.exe" -m uvicorn app.main:app --host $env:NAV_BACKEND_HOST --port $env:NAV_BACKEND_PORT --reload
