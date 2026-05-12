$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
$configPath = Join-Path $repo "config\pipeline_config.json"
$cfg = Get-Content $configPath -Raw | ConvertFrom-Json

$colmap = $cfg.colmap_path
$dbPath = Join-Path $repo "colmap_workspace\database.db"
$imgPath = Join-Path $repo "colmap_workspace\images"
$sparsePath = Join-Path $repo "colmap_workspace\sparse"
$logDir = Join-Path $repo "outputs\logs"
$logFile = Join-Path $logDir "colmap_sparse.log"

New-Item -ItemType Directory -Force -Path $logDir | Out-Null
New-Item -ItemType Directory -Force -Path $sparsePath | Out-Null
if (Test-Path $dbPath) { Remove-Item -Force $dbPath }
Get-ChildItem -Path $sparsePath -Directory -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

Write-Output "Running feature_extractor..." | Tee-Object -FilePath $logFile -Append
& $colmap feature_extractor `
  --database_path $dbPath `
  --image_path $imgPath `
  --ImageReader.camera_model $cfg.camera_model `
  --ImageReader.single_camera $cfg.single_camera `
  --FeatureExtraction.use_gpu 0 `
  --FeatureExtraction.max_image_size 2000 `
  --FeatureExtraction.num_threads -1 2>&1 | Tee-Object -FilePath $logFile -Append

Write-Output "Running sequential_matcher..." | Tee-Object -FilePath $logFile -Append
& $colmap sequential_matcher `
  --database_path $dbPath `
  --FeatureMatching.use_gpu 0 `
  --FeatureMatching.guided_matching 1 `
  --FeatureMatching.num_threads -1 `
  --SequentialMatching.overlap 20 `
  --SequentialMatching.quadratic_overlap 1 `
  --SequentialMatching.loop_detection 1 `
  --SequentialMatching.loop_detection_num_images 80 `
  --SequentialMatching.num_threads -1 2>&1 | Tee-Object -FilePath $logFile -Append

Write-Output "Running mapper..." | Tee-Object -FilePath $logFile -Append
& $colmap mapper `
  --database_path $dbPath `
  --image_path $imgPath `
  --output_path $sparsePath `
  --Mapper.num_threads -1 `
  --Mapper.ba_global_function_tolerance 1e-6 2>&1 | Tee-Object -FilePath $logFile -Append

Write-Output "COLMAP sparse run complete." | Tee-Object -FilePath $logFile -Append
