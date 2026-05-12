from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


def ply_header_info(path: Path) -> dict[str, Any]:
    vertex_count = None
    face_count = None
    with path.open("rb") as f:
        while True:
            line = f.readline()
            if not line:
                break
            txt = line.decode("latin-1", errors="ignore").strip()
            if txt.startswith("element vertex"):
                vertex_count = int(txt.split()[2])
            elif txt.startswith("element face"):
                face_count = int(txt.split()[2])
            elif txt == "end_header":
                break
    return {
        "vertex_count": vertex_count,
        "face_count": face_count,
        "bytes": path.stat().st_size,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Copy latest PLY map assets into repo and refresh map_config.json")
    parser.add_argument("--fused", required=True, help="Path to fused_final.ply source file")
    parser.add_argument("--mesh", required=True, help="Path to mesh_final.ply source file")
    parser.add_argument("--map-name", default="floor_v2_half_floor_approved", help="active_map name")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    assets_maps = repo_root / "assets" / "maps"
    assets_maps.mkdir(parents=True, exist_ok=True)
    config_path = repo_root / "config" / "map_config.json"

    fused_src = Path(args.fused).resolve()
    mesh_src = Path(args.mesh).resolve()
    if not fused_src.exists():
        raise FileNotFoundError(f"Fused file not found: {fused_src}")
    if not mesh_src.exists():
        raise FileNotFoundError(f"Mesh file not found: {mesh_src}")

    fused_dst = assets_maps / "fused_final.ply"
    mesh_dst = assets_maps / "mesh_final.ply"
    shutil.copy2(fused_src, fused_dst)
    shutil.copy2(mesh_src, mesh_dst)

    map_config = {
        "active_map": args.map_name,
        "fused_ply": "assets/maps/fused_final.ply",
        "mesh_ply": "assets/maps/mesh_final.ply",
        "coordinate_frame": "colmap_world",
        "notes": "Teacher-approved half-floor coverage for demo",
        "fused_ply_info": ply_header_info(fused_dst),
        "mesh_ply_info": ply_header_info(mesh_dst),
    }
    config_path.write_text(json.dumps(map_config, indent=2), encoding="utf-8")

    print("Updated map assets and config:")
    print(" fused:", fused_dst)
    print(" mesh :", mesh_dst)
    print(" config:", config_path)


if __name__ == "__main__":
    main()
