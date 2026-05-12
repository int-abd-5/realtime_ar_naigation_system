from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build backend visual map package from COLMAP outputs.")
    parser.add_argument("--model-dir", required=True, help="Directory containing cameras.txt/images.txt/points3D.txt")
    parser.add_argument("--database", required=True, help="Path to COLMAP database.db")
    parser.add_argument("--images", required=True, help="Path to original COLMAP images directory")
    parser.add_argument(
        "--out-dir",
        default=r"C:\Users\Abdul\Desktop\ai_proj_indoor_navigation_v2\backend\data\visual_map",
        help="Output visual map package dir",
    )
    args = parser.parse_args()

    model_dir = Path(args.model_dir).resolve()
    db_path = Path(args.database).resolve()
    images_dir = Path(args.images).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_model = out_dir / "model"
    out_images = out_dir / "images"

    for f in ["cameras.txt", "images.txt", "points3D.txt"]:
        if not (model_dir / f).exists():
            raise FileNotFoundError(f"Missing {f} in {model_dir}")
    if not db_path.exists():
        raise FileNotFoundError(f"Missing database: {db_path}")
    if not images_dir.exists():
        raise FileNotFoundError(f"Missing images dir: {images_dir}")

    out_dir.mkdir(parents=True, exist_ok=True)
    if out_model.exists():
        shutil.rmtree(out_model)
    out_model.mkdir(parents=True, exist_ok=True)

    for f in ["cameras.txt", "images.txt", "points3D.txt"]:
        shutil.copy2(model_dir / f, out_model / f)
    shutil.copy2(db_path, out_dir / "database.db")

    # Keep a lightweight image copy for debugging/inspection in backend package.
    if out_images.exists():
        shutil.rmtree(out_images)
    shutil.copytree(images_dir, out_images)

    print("Visual map package ready:")
    print(" model:", out_model)
    print(" db   :", out_dir / "database.db")
    print(" images:", out_images)


if __name__ == "__main__":
    main()
