# Indoor Floor V2 Runbook

## 1) Extract frames from video
```powershell
python scripts\01_extract_frames.py
```

## 2) Filter frames
```powershell
python scripts\02_filter_frames.py
```

## 3) Copy cleaned frames to COLMAP image folder
```powershell
python scripts\03_prepare_colmap_images.py
```

## 4) Run sparse COLMAP reconstruction
```powershell
powershell -ExecutionPolicy Bypass -File scripts\04_run_colmap_sparse.ps1
```

## 5) Analyze sparse models
```powershell
powershell -ExecutionPolicy Bypass -File scripts\05_analyze_sparse.ps1
```

## Output files
- `outputs/qc/extract_summary.json`
- `outputs/qc/filter_summary.json`
- `outputs/qc/prepare_colmap_summary.json`
- `outputs/logs/colmap_sparse.log`
- `outputs/qc/sparse_metrics.txt`
