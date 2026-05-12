from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class MapLoader:
    def __init__(self, map_config_path: Path) -> None:
        self.map_config_path = map_config_path
        self.project_root = map_config_path.parent.parent
        self.map_config = self._load_map_config()

    def _load_map_config(self) -> dict:
        if not self.map_config_path.exists():
            return {
                "active_map": "unknown",
                "fused_ply": "",
                "mesh_ply": "",
                "coordinate_frame": "colmap_world",
            }
        return json.loads(self.map_config_path.read_text(encoding="utf-8"))

    def _resolve_map_path(self, path_val: str) -> Path:
        p = Path(path_val)
        if p.is_absolute():
            return p
        return (self.project_root / p).resolve()

    def _ply_header_info(self, ply_path: Path) -> dict[str, Any]:
        if not ply_path.exists():
            return {"exists": False}

        vertex_count = None
        face_count = None
        with ply_path.open("rb") as f:
            while True:
                line = f.readline()
                if not line:
                    break
                txt = line.decode("latin-1", errors="ignore").strip()
                if txt.startswith("element vertex"):
                    try:
                        vertex_count = int(txt.split()[2])
                    except Exception:
                        vertex_count = None
                elif txt.startswith("element face"):
                    try:
                        face_count = int(txt.split()[2])
                    except Exception:
                        face_count = None
                elif txt == "end_header":
                    break
        return {
            "exists": True,
            "vertex_count": vertex_count,
            "face_count": face_count,
            "bytes": ply_path.stat().st_size,
        }

    def summary(self) -> dict:
        fused_rel = self.map_config.get("fused_ply", "")
        mesh_rel = self.map_config.get("mesh_ply", "")
        fused_abs = self._resolve_map_path(fused_rel) if fused_rel else None
        mesh_abs = self._resolve_map_path(mesh_rel) if mesh_rel else None

        return {
            "active_map": self.map_config.get("active_map", "unknown"),
            "fused_ply": fused_rel,
            "mesh_ply": mesh_rel,
            "fused_ply_info": self._ply_header_info(fused_abs) if fused_abs else {"exists": False},
            "mesh_ply_info": self._ply_header_info(mesh_abs) if mesh_abs else {"exists": False},
            "coordinate_frame": self.map_config.get("coordinate_frame", "colmap_world"),
            "notes": self.map_config.get("notes", ""),
        }
