import json
from pathlib import Path


def load_active_map(repo_root: str) -> dict:
    repo = Path(repo_root)
    config_path = repo / "config" / "map_config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))

    fused_path = repo / config["fused_ply"]
    mesh_path = repo / config["mesh_ply"]

    if not fused_path.exists():
        raise FileNotFoundError(f"Missing fused map file: {fused_path}")
    if not mesh_path.exists():
        raise FileNotFoundError(f"Missing mesh map file: {mesh_path}")

    return {
        "active_map": config["active_map"],
        "fused_ply": str(fused_path),
        "mesh_ply": str(mesh_path),
        "coordinate_frame": config.get("coordinate_frame", "colmap_world"),
    }
