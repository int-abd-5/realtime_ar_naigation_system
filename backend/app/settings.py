from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    localization_mode: str
    map_config_path: Path
    nodes_json_path: Path
    edges_json_path: Path
    visual_model_path: Path
    visual_database_path: Path
    visual_images_path: Path
    visual_max_candidates: int
    visual_min_inliers: int
    visual_match_ratio: float


def load_settings() -> Settings:
    app_dir = Path(__file__).resolve().parent
    backend_dir = app_dir.parent
    default_map_config = (backend_dir.parent / "config" / "map_config.json").resolve()
    default_nodes = (backend_dir / "data" / "navigation" / "nodes.json").resolve()
    default_edges = (backend_dir / "data" / "navigation" / "edges.json").resolve()
    default_visual_model = (backend_dir / "data" / "visual_map" / "model").resolve()
    default_visual_db = (backend_dir / "data" / "visual_map" / "database.db").resolve()
    default_visual_images = (backend_dir / "data" / "visual_map" / "images").resolve()

    return Settings(
        host=_env("NAV_BACKEND_HOST", "0.0.0.0"),
        port=int(_env("NAV_BACKEND_PORT", "8000")),
        localization_mode=_env("NAV_LOCALIZATION_MODE", "hybrid"),
        map_config_path=Path(_env("NAV_MAP_CONFIG", str(default_map_config))).resolve(),
        nodes_json_path=Path(_env("NAV_NODES_JSON", str(default_nodes))).resolve(),
        edges_json_path=Path(_env("NAV_EDGES_JSON", str(default_edges))).resolve(),
        visual_model_path=Path(_env("NAV_VISUAL_MODEL_PATH", str(default_visual_model))).resolve(),
        visual_database_path=Path(_env("NAV_VISUAL_DB_PATH", str(default_visual_db))).resolve(),
        visual_images_path=Path(_env("NAV_VISUAL_IMAGES_PATH", str(default_visual_images))).resolve(),
        visual_max_candidates=int(_env("NAV_VISUAL_MAX_CANDIDATES", "32")),
        visual_min_inliers=int(_env("NAV_VISUAL_MIN_INLIERS", "6")),
        visual_match_ratio=float(_env("NAV_VISUAL_MATCH_RATIO", "0.90")),
    )
