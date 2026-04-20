# Sparse0 Workflow (Current Stable Baseline)

This project currently uses the `sparse0` map artifacts:

- `assets/maps/sparse0/fused_m0.ply`
- `assets/maps/sparse0/mesh_m0.ply`

## 1) Confirm map config

Check `config/map_config.json`:

```json
{
  "active_map": "sparse0",
  "fused_ply": "assets/maps/sparse0/fused_m0.ply",
  "mesh_ply": "assets/maps/sparse0/mesh_m0.ply",
  "coordinate_frame": "colmap_world"
}
```

## 2) Test map loader

```powershell
@'
from src.localization.map_loader import load_active_map
print(load_active_map(r"C:\Users\Abdul\Desktop\ai_proj_indoor_navigation"))
'@ | python -
```

## 3) Test route planner (node-to-node)

```powershell
python .\src\navigation\route_planner.py --start-node n0_entrance --goal-node n3_room_a
```

## 4) Test route planner (coordinate start)

```powershell
python .\src\navigation\route_planner.py --start-x 0.2 --start-y 0.1 --goal-node n4_room_b
```

## 5) Update graph for your real floor

Edit:

- `src/navigation/nodes.json`
- `src/navigation/edges.json`

Keep node IDs stable. Use meters for coordinates and distance-like values for edge `cost`.

## 6) Next integration target

Connect realtime localization output to planner:

- Localization output: current `(x, y)` in map coordinates
- Feed to planner using `--start-x` and `--start-y`
- Destination selected from node IDs
