from __future__ import annotations

import argparse
import base64
from pathlib import Path

from app.localization import Localizer


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test visual/hybrid localizer with one image frame.")
    parser.add_argument("--image", required=True, help="Query image path (jpg/png)")
    parser.add_argument("--mode", default="hybrid", choices=["mock", "hybrid", "visual"])
    parser.add_argument(
        "--model-path",
        default=r"C:\Users\Abdul\Desktop\ai_proj_indoor_navigation_v2\backend\data\visual_map\model",
    )
    parser.add_argument(
        "--db-path",
        default=r"C:\Users\Abdul\Desktop\ai_proj_indoor_navigation_v2\backend\data\visual_map\database.db",
    )
    args = parser.parse_args()

    image_path = Path(args.image).resolve()
    if not image_path.exists():
        raise FileNotFoundError(image_path)
    b64 = base64.b64encode(image_path.read_bytes()).decode("ascii")

    localizer = Localizer(
        mode=args.mode,
        visual_model_path=Path(args.model_path).resolve(),
        visual_database_path=Path(args.db_path).resolve(),
    )
    print("visual_ready:", localizer.visual_ready)
    if not localizer.visual_ready:
        print("reason:", localizer.visual_reason_not_ready)

    localizer.reset_session("test", start_x=0.0, start_z=0.0)
    res = localizer.localize(session_id="test", jpeg_b64=b64, heading_deg=45.0, timestamp_ms=1_000_000)
    print("pose:", res.position)
    print("confidence:", res.confidence)


if __name__ == "__main__":
    main()
