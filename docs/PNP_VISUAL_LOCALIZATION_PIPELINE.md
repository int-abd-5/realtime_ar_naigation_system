## Goal
Add realtime visual geolocation using COLMAP map assets:
- 2D query features from live camera frame
- 2D-3D correspondences using COLMAP descriptors + sparse model
- `solvePnPRansac` for camera pose
- fallback to dead-reckoning when visual pose fails

## What this backend now supports
- `NAV_LOCALIZATION_MODE=visual`:
  only visual PnP localization (falls back to dead-reckoning if visual pose fails in current frame).
- `NAV_LOCALIZATION_MODE=hybrid`:
  tries visual PnP every frame, otherwise dead-reckoning fallback.
- `NAV_LOCALIZATION_MODE=mock`:
  dead-reckoning only.

---

## Required map package (must exist locally)
Place these under:
`C:\Users\Abdul\Desktop\ai_proj_indoor_navigation_v2\backend\data\visual_map`

Required:
- `model/cameras.txt`
- `model/images.txt`
- `model/points3D.txt`
- `database.db`
- `images/` (same image set used for COLMAP)

---

## Colab: export the required files (one-time)
Run after choosing your best sparse model (for example `best_id=0`):

```python
from pathlib import Path
import shutil

ws = Path("/content/colmap_workspace")
best_id = "0"  # change if needed
sparse_best = ws / "sparse_bridge" / best_id
images = ws / "images_bridge"  # or ws / "images"
db = ws / "database_bridge.db" # or ws / "database.db"

export = Path("/content/drive/MyDrive/colmap_v2_visual_package")
if export.exists():
    shutil.rmtree(export)
(export / "model").mkdir(parents=True, exist_ok=True)

# convert bin model to text using pycolmap
import pycolmap
rec = pycolmap.Reconstruction(str(sparse_best))
rec.write(str(export / "model"))  # writes cameras.bin/images.bin/points3D.bin
```

Then convert binaries to text:
```python
import pycolmap
from pathlib import Path

model_dir = Path("/content/drive/MyDrive/colmap_v2_visual_package/model")
rec = pycolmap.Reconstruction(str(model_dir))
rec.write_text(str(model_dir))
```

Copy DB and images:
```python
import shutil
from pathlib import Path

ws = Path("/content/colmap_workspace")
export = Path("/content/drive/MyDrive/colmap_v2_visual_package")

shutil.copy2(ws / "database_bridge.db", export / "database.db")  # or database.db
shutil.copytree(ws / "images_bridge", export / "images", dirs_exist_ok=True)
print("Exported visual package:", export)
```

---

## Local: build backend visual package
After downloading `colmap_v2_visual_package` to your PC:

```powershell
python C:\Users\Abdul\Desktop\ai_proj_indoor_navigation_v2\scripts\build_visual_map_package.py `
  --model-dir C:\path\to\colmap_v2_visual_package\model `
  --database C:\path\to\colmap_v2_visual_package\database.db `
  --images C:\path\to\colmap_v2_visual_package\images `
  --out-dir C:\Users\Abdul\Desktop\ai_proj_indoor_navigation_v2\backend\data\visual_map
```

---

## Run backend in visual/hybrid mode
```powershell
cd C:\Users\Abdul\Desktop\ai_proj_indoor_navigation_v2\backend
$env:NAV_LOCALIZATION_MODE="hybrid"
.\run_backend.ps1
```

Health check:
```powershell
curl http://127.0.0.1:8000/health
```

Expected fields:
- `visual_ready: true`
- empty `visual_reason_not_ready`

---

## Smoke test a single image
```powershell
cd C:\Users\Abdul\Desktop\ai_proj_indoor_navigation_v2\backend
.\.venv\Scripts\python.exe .\test_visual_localizer.py --mode hybrid --image C:\Users\Abdul\Desktop\ai_proj_indoor_navigation_v2\colmap_workspace\images\img_000300.jpg
```

If `visual_ready` is false, check missing paths in `/health` response.
