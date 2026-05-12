import argparse
import json
from pathlib import Path

import cv2


def load_config(config_path: Path) -> dict:
    return json.loads(config_path.read_text(encoding="utf-8"))


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract frames from source video at target FPS.")
    parser.add_argument("--config", type=Path, default=Path("config/pipeline_config.json"))
    parser.add_argument("--input", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=Path("data/frames_raw"))
    args = parser.parse_args()

    config = load_config(args.config)
    video_path = args.input or Path(config["video_path"])
    out_dir = args.out
    sample_fps = float(config.get("frame_sample_fps", 1.0))
    resize_w = int(config.get("resize_width", 1920))
    resize_h = int(config.get("resize_height", 1080))

    ensure_dir(out_dir)
    for p in out_dir.glob("frame_*.jpg"):
        p.unlink()

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open video: {video_path}")

    native_fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_sec = total_frames / native_fps if native_fps > 0 else 0.0
    stride = max(1, int(round(native_fps / sample_fps)))

    saved = 0
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % stride == 0:
            h, w = frame.shape[:2]
            if h > w:
                frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
            frame = cv2.resize(frame, (resize_w, resize_h), interpolation=cv2.INTER_AREA)
            out_file = out_dir / f"frame_{saved:06d}.jpg"
            cv2.imwrite(str(out_file), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            saved += 1
        idx += 1

    cap.release()

    summary = {
        "video_path": str(video_path),
        "native_fps": native_fps,
        "duration_sec": duration_sec,
        "total_frames": total_frames,
        "sample_fps": sample_fps,
        "stride": stride,
        "saved_frames": saved,
    }
    Path("outputs/qc").mkdir(parents=True, exist_ok=True)
    Path("outputs/qc/extract_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
