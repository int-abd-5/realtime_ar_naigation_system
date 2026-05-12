import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def load_config(config_path: Path) -> dict:
    return json.loads(config_path.read_text(encoding="utf-8"))


def brightness(gray: np.ndarray) -> float:
    return float(np.mean(gray))


def blur_score(gray: np.ndarray) -> float:
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def similarity_ssim(img_a_gray: np.ndarray, img_b_gray: np.ndarray) -> float:
    h, w = img_a_gray.shape
    a = cv2.resize(img_a_gray, (w // 4, h // 4), interpolation=cv2.INTER_AREA)
    b = cv2.resize(img_b_gray, (w // 4, h // 4), interpolation=cv2.INTER_AREA)
    c1 = (0.01 * 255) ** 2
    c2 = (0.03 * 255) ** 2
    mu_a = cv2.GaussianBlur(a.astype(np.float64), (11, 11), 1.5)
    mu_b = cv2.GaussianBlur(b.astype(np.float64), (11, 11), 1.5)
    sigma_a = cv2.GaussianBlur((a - mu_a) ** 2, (11, 11), 1.5)
    sigma_b = cv2.GaussianBlur((b - mu_b) ** 2, (11, 11), 1.5)
    sigma_ab = cv2.GaussianBlur((a - mu_a) * (b - mu_b), (11, 11), 1.5)
    ssim_map = ((2 * mu_a * mu_b + c1) * (2 * sigma_ab + c2)) / (
        (mu_a**2 + mu_b**2 + c1) * (sigma_a + sigma_b + c2)
    )
    return float(np.mean(ssim_map))


def main() -> None:
    parser = argparse.ArgumentParser(description="Filter extracted frames by blur/brightness/near-duplicate.")
    parser.add_argument("--config", type=Path, default=Path("config/pipeline_config.json"))
    parser.add_argument("--input", type=Path, default=Path("data/frames_raw"))
    parser.add_argument("--out", type=Path, default=Path("data/frames_clean"))
    args = parser.parse_args()

    config = load_config(args.config)
    blur_min = float(config.get("blur_threshold", 80.0))
    bright_min = float(config.get("brightness_min", 35.0))
    bright_max = float(config.get("brightness_max", 220.0))
    dedupe_threshold = float(config.get("dedupe_ssim_threshold", 0.985))

    args.out.mkdir(parents=True, exist_ok=True)
    for p in args.out.glob("frame_*.jpg"):
        p.unlink()

    records = []
    accepted = 0
    rejected_blur = 0
    rejected_brightness = 0
    rejected_duplicate = 0

    prev_kept_gray = None
    src_files = sorted(args.input.glob("frame_*.jpg"))

    for src in src_files:
        frame = cv2.imread(str(src))
        if frame is None:
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        b = brightness(gray)
        bl = blur_score(gray)

        decision = "accept"
        if bl < blur_min:
            decision = "reject_blur"
            rejected_blur += 1
        elif b < bright_min or b > bright_max:
            decision = "reject_brightness"
            rejected_brightness += 1
        elif prev_kept_gray is not None:
            ssim = similarity_ssim(prev_kept_gray, gray)
            if ssim >= dedupe_threshold:
                decision = "reject_duplicate"
                rejected_duplicate += 1
        else:
            ssim = None

        if decision == "accept":
            out_file = args.out / src.name
            cv2.imwrite(str(out_file), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            prev_kept_gray = gray
            accepted += 1
            ssim = None

        records.append(
            {
                "file": src.name,
                "brightness": round(b, 3),
                "blur": round(bl, 3),
                "decision": decision,
                "ssim_vs_prev_kept": None if ssim is None else round(ssim, 6),
            }
        )

    summary = {
        "input_frames": len(src_files),
        "accepted_frames": accepted,
        "rejected_blur": rejected_blur,
        "rejected_brightness": rejected_brightness,
        "rejected_duplicate": rejected_duplicate,
        "blur_threshold": blur_min,
        "brightness_min": bright_min,
        "brightness_max": bright_max,
        "dedupe_ssim_threshold": dedupe_threshold,
    }

    Path("outputs/qc").mkdir(parents=True, exist_ok=True)
    Path("outputs/qc/filter_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    Path("outputs/qc/filter_details.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
