$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
$configPath = Join-Path $repo "config\pipeline_config.json"
$cfg = Get-Content $configPath -Raw | ConvertFrom-Json
$colmap = $cfg.colmap_path
$sparseRoot = Join-Path $repo "colmap_workspace\sparse"
$outQc = Join-Path $repo "outputs\qc\sparse_metrics.txt"
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $outQc) | Out-Null

if (-not (Test-Path $sparseRoot)) {
  throw "Sparse root not found: $sparseRoot"
}

if (Test-Path $outQc) { Remove-Item -Force $outQc }

$models = Get-ChildItem -Path $sparseRoot -Directory | Sort-Object Name
if ($models.Count -eq 0) {
  throw "No sparse models found in $sparseRoot"
}

foreach ($m in $models) {
  "===== Model $($m.Name) =====" | Tee-Object -FilePath $outQc -Append
  & $colmap model_analyzer --path $m.FullName 2>&1 | Tee-Object -FilePath $outQc -Append
  "" | Tee-Object -FilePath $outQc -Append
}

Write-Output "Wrote sparse metrics to $outQc"
