import argparse
import json
import shutil
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Copy cleaned frames into colmap_workspace/images.")
    parser.add_argument("--input", type=Path, default=Path("data/frames_clean"))
    parser.add_argument("--output", type=Path, default=Path("colmap_workspace/images"))
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    for p in args.output.glob("*.jpg"):
        p.unlink()

    files = sorted(args.input.glob("frame_*.jpg"))
    for i, src in enumerate(files):
        dst = args.output / f"img_{i:06d}.jpg"
        shutil.copy2(src, dst)

    summary = {
        "input_frames": len(files),
        "output_frames": len(list(args.output.glob('img_*.jpg'))),
        "output_dir": str(args.output),
    }
    Path("outputs/qc").mkdir(parents=True, exist_ok=True)
    Path("outputs/qc/prepare_colmap_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
