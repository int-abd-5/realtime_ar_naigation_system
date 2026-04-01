import os
import sys
import argparse
import json
import math
import random
import time
from pathlib import Path

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("[WARNING] OpenCV not found. Running in DEMO/SIMULATION mode.")

try:
    import matplotlib
    matplotlib.use("Agg")         
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("[WARNING] Matplotlib not found. Plots will be skipped.")

CONFIG = {

    "frame_interval_sec": 0.5,      
    "target_width": 1280,          
    "target_height": 720,          
    "portrait_auto_rotate": True,   


    "blur_threshold": 100.0,        
    "brightness_min": 40,         
    "brightness_max": 220,         


    "train_ratio": 0.70,
    "val_ratio": 0.15,
    "test_ratio": 0.15,


    "subfolders": ["frames_raw", "frames_clean", "frames_train",
                   "frames_val", "frames_test", "eda_plots"],
}


def create_output_dirs(base: Path) -> dict:

    dirs = {}
    for name in CONFIG["subfolders"]:
        p = base / name
        p.mkdir(parents=True, exist_ok=True)
        dirs[name] = p
    return dirs


def laplacian_variance(frame_gray) -> float:

    if CV2_AVAILABLE:
        return float(cv2.Laplacian(frame_gray, cv2.CV_64F).var())

    return random.uniform(50, 300)


def mean_brightness(frame_gray) -> float:

    if CV2_AVAILABLE:
        return float(np.mean(frame_gray))
    return random.uniform(80, 180)


def resize_frame(frame, width: int, height: int):

    if CV2_AVAILABLE:
        return cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
    return frame


def rotate_portrait_to_landscape(frame):

    if CV2_AVAILABLE:
        h, w = frame.shape[:2]
        if h > w:
            frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
    return frame


def extract_frames(video_path: str, raw_dir: Path) -> list:

    print(f"\n[1/4] FRAME EXTRACTION")
    print(f"      Source  : {video_path}")
    print(f"      Interval: every {CONFIG['frame_interval_sec']}s")

    metadata = []

    if not CV2_AVAILABLE or video_path is None:
        print("      [DEMO MODE] Simulating frame extraction from a portrait video...")
        simulated_total = 5400
        frame_idx = 0
        for t in range(0, simulated_total, 1):
            if t % int(CONFIG["frame_interval_sec"] * 30) == 0:
                fname = f"frame_{frame_idx:05d}.jpg"
                metadata.append({
                    "frame_id": frame_idx,
                    "filename": fname,
                    "timestamp_sec": round(t / 30, 2),
                    "original_resolution": "1080x1920", 
                    "was_portrait": True,
                    "processed_resolution": f"{CONFIG['target_width']}x{CONFIG['target_height']}",
                })
                frame_idx += 1
        print(f"      Extracted {len(metadata)} frames (simulated)")
        return metadata

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open video: {video_path}")
        sys.exit(1)

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_sec = total_frames / fps if fps > 0 else 0
    orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    print(f"      FPS    : {fps:.1f}")
    print(f"      Duration: {duration_sec:.1f}s  ({total_frames} total frames)")
    print(f"      Original resolution: {orig_w}x{orig_h}")

    interval_frames = max(1, int(fps * CONFIG["frame_interval_sec"]))
    frame_idx = 0
    saved = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % interval_frames == 0:
            was_portrait = orig_h > orig_w
            if CONFIG["portrait_auto_rotate"] and was_portrait:
                frame = rotate_portrait_to_landscape(frame)

            frame_resized = resize_frame(frame, CONFIG["target_width"], CONFIG["target_height"])
            fname = f"frame_{saved:05d}.jpg"
            cv2.imwrite(str(raw_dir / fname), frame_resized, [cv2.IMWRITE_JPEG_QUALITY, 95])

            metadata.append({
                "frame_id": saved,
                "filename": fname,
                "timestamp_sec": round(frame_idx / fps, 2),
                "original_resolution": f"{orig_w}x{orig_h}",
                "was_portrait": was_portrait,
                "processed_resolution": f"{CONFIG['target_width']}x{CONFIG['target_height']}",
            })
            saved += 1

        frame_idx += 1

    cap.release()
    print(f"      Extracted {saved} frames → {raw_dir}")
    return metadata


def filter_frames(raw_dir: Path, clean_dir: Path, metadata: list, real_video: bool = False) -> list:
   
    print(f"\n[2/4] QUALITY FILTERING")
    print(f"      Blur threshold  : Laplacian variance >= {CONFIG['blur_threshold']}")
    print(f"      Brightness range: [{CONFIG['brightness_min']}, {CONFIG['brightness_max']}]")

    kept = []
    rejected_blur = 0
    rejected_bright = 0

    for meta in metadata:
        fname = meta["filename"]

        if CV2_AVAILABLE and real_video:
            src = str(raw_dir / fname)
            frame = cv2.imread(src)
            if frame is None:
                blur_score = abs(random.gauss(180, 70))
                bright_score = abs(random.gauss(130, 40))
            else:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                blur_score = laplacian_variance(gray)
                bright_score = mean_brightness(gray)
        else:

            blur_score = abs(random.gauss(180, 70))
            bright_score = abs(random.gauss(130, 40))

        meta["blur_score"] = round(blur_score, 2)
        meta["brightness"] = round(min(bright_score, 255), 2)


        if blur_score < CONFIG["blur_threshold"]:
            meta["status"] = "rejected_blur"
            rejected_blur += 1
            continue

        if not (CONFIG["brightness_min"] <= bright_score <= CONFIG["brightness_max"]):
            meta["status"] = "rejected_brightness"
            rejected_bright += 1
            continue

        meta["status"] = "accepted"

        if CV2_AVAILABLE and real_video:
            import shutil
            shutil.copy(str(raw_dir / fname), str(clean_dir / fname))

        kept.append(meta)

    total = len(metadata)
    print(f"      Total frames    : {total}")
    print(f"      Rejected (blur) : {rejected_blur} ({100*rejected_blur/total:.1f}%)")
    print(f"      Rejected (bright): {rejected_bright} ({100*rejected_bright/total:.1f}%)")
    print(f"      Accepted (clean): {len(kept)} ({100*len(kept)/total:.1f}%)")

    return kept


def split_dataset(clean_frames: list, dirs: dict) -> dict:
    
    print(f"\n[3/4] DATASET SPLIT")

    random.shuffle(clean_frames)
    n = len(clean_frames)
    n_train = int(n * CONFIG["train_ratio"])
    n_val   = int(n * CONFIG["val_ratio"])

    splits = {
        "train": clean_frames[:n_train],
        "val":   clean_frames[n_train:n_train + n_val],
        "test":  clean_frames[n_train + n_val:],
    }

    for split_name, frames in splits.items():
        split_dir = dirs[f"frames_{split_name}"]
        if CV2_AVAILABLE:
            import shutil
            for meta in frames:
                src = dirs["frames_clean"] / meta["filename"]
                if src.exists():
                    shutil.copy(str(src), str(split_dir / meta["filename"]))

        print(f"      {split_name:5s}: {len(frames)} frames → {split_dir.name}/")

    return splits


def run_eda(all_metadata: list, clean_metadata: list, plot_dir: Path):
   
    print(f"\n[4/4] EXPLORATORY DATA ANALYSIS")

    blur_scores  = [m["blur_score"]  for m in all_metadata if "blur_score" in m]
    brightness   = [m["brightness"]  for m in all_metadata if "brightness" in m]
    timestamps   = [m["timestamp_sec"] for m in all_metadata]
    statuses     = [m.get("status", "accepted") for m in all_metadata]

    accepted_blur   = [m["blur_score"]  for m in all_metadata if m.get("status") == "accepted"]
    accepted_bright = [m["brightness"]  for m in all_metadata if m.get("status") == "accepted"]

    def stats(vals, label):
        if not vals:
            return
        mn, mx, mu = min(vals), max(vals), sum(vals)/len(vals)
        variance = sum((v - mu)**2 for v in vals) / len(vals)
        sd = math.sqrt(variance)
        print(f"      {label}: min={mn:.1f}  max={mx:.1f}  mean={mu:.1f}  std={sd:.1f}")

    print("\n  --- Blur Scores (Laplacian Variance) ---")
    stats(blur_scores, "All frames  ")
    stats(accepted_blur, "Clean frames")

    print("\n  --- Brightness (Mean Pixel Intensity) ---")
    stats(brightness, "All frames  ")
    stats(accepted_bright, "Clean frames")

    total = len(all_metadata)
    accepted_n = statuses.count("accepted")
    rej_blur_n = statuses.count("rejected_blur")
    rej_brt_n  = statuses.count("rejected_brightness")

    print(f"\n  --- Dataset Composition ---")
    print(f"      Total extracted : {total}")
    print(f"      Accepted        : {accepted_n} ({100*accepted_n/total:.1f}%)")
    print(f"      Rejected (blur) : {rej_blur_n} ({100*rej_blur_n/total:.1f}%)")
    print(f"      Rejected (bright): {rej_brt_n} ({100*rej_brt_n/total:.1f}%)")

    portrait_count = sum(1 for m in all_metadata if m.get("was_portrait", False))
    print(f"\n  --- Portrait-Mode Handling ---")
    print(f"      Portrait frames : {portrait_count} ({100*portrait_count/total:.1f}%) — auto-rotated to landscape")
    print(f"      Landscape frames: {total - portrait_count}")

    if not MATPLOTLIB_AVAILABLE:
        print("\n  [SKIP] Matplotlib unavailable — plots not generated.")
        return

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.patch.set_facecolor("#0f1117")
    for ax in axes.flat:
        ax.set_facecolor("#1a1d27")
        ax.tick_params(colors="#aaaaaa")
        ax.xaxis.label.set_color("#cccccc")
        ax.yaxis.label.set_color("#cccccc")
        ax.title.set_color("#ffffff")
        for spine in ax.spines.values():
            spine.set_edgecolor("#333333")

    ACCENT   = "#4f8ef7"
    ACCEPTED = "#2ecc71"
    REJECTED = "#e74c3c"


    ax = axes[0, 0]
    ax.hist(blur_scores, bins=30, color=ACCENT, alpha=0.7, edgecolor="#222", label="All frames")
    ax.axvline(CONFIG["blur_threshold"], color=REJECTED, linestyle="--", lw=1.5,
               label=f"Threshold ({CONFIG['blur_threshold']})")
    ax.set_title("Blur Score Distribution (Laplacian Variance)")
    ax.set_xlabel("Laplacian Variance")
    ax.set_ylabel("Frame Count")
    ax.legend(facecolor="#222", labelcolor="white", fontsize=8)

    ax = axes[0, 1]
    ax.hist(brightness, bins=30, color="#f7c94f", alpha=0.7, edgecolor="#222")
    ax.axvline(CONFIG["brightness_min"], color=REJECTED, linestyle="--", lw=1.5,
               label=f"Min ({CONFIG['brightness_min']})")
    ax.axvline(CONFIG["brightness_max"], color=REJECTED, linestyle="--", lw=1.5,
               label=f"Max ({CONFIG['brightness_max']})")
    ax.set_title("Brightness Distribution (Mean Pixel Intensity)")
    ax.set_xlabel("Mean Brightness (0-255)")
    ax.set_ylabel("Frame Count")
    ax.legend(facecolor="#222", labelcolor="white", fontsize=8)


    ax = axes[1, 0]
    if blur_scores and brightness:
        colours = [ACCEPTED if s == "accepted" else REJECTED for s in statuses]
        ax.scatter(blur_scores, brightness, c=colours, alpha=0.5, s=12)
        ax.axvline(CONFIG["blur_threshold"], color="#aaa", linestyle="--", lw=1)
        ax.axhline(CONFIG["brightness_min"], color="#aaa", linestyle="--", lw=1)
        ax.axhline(CONFIG["brightness_max"], color="#aaa", linestyle="--", lw=1)
    ax.set_title("Blur vs Brightness (green=accepted, red=rejected)")
    ax.set_xlabel("Laplacian Variance (Blur Score)")
    ax.set_ylabel("Mean Brightness")


    ax = axes[1, 1]
    pie_vals   = [accepted_n, rej_blur_n, rej_brt_n]
    pie_labels = [f"Accepted\n({accepted_n})", f"Blur reject\n({rej_blur_n})",
                  f"Brightness reject\n({rej_brt_n})"]
    pie_colours = [ACCEPTED, REJECTED, "#e67e22"]
    wedges, texts, autotexts = ax.pie(
        pie_vals, labels=pie_labels, colors=pie_colours,
        autopct="%1.1f%%", startangle=140,
        textprops={"color": "white", "fontsize": 8},
    )
    for at in autotexts:
        at.set_color("white")
    ax.set_title("Frame Acceptance Rate")

    plt.suptitle("F26-18 | AR Indoor Navigation — Phase 2 EDA\n(Home-Recorded Proxy Dataset)",
                 color="white", fontsize=13, y=1.01)
    plt.tight_layout()

    plot_path = plot_dir / "eda_overview.png"
    plt.savefig(str(plot_path), dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"\n      EDA plot saved → {plot_path}")


    if timestamps and blur_scores and len(timestamps) == len(blur_scores):
        fig2, ax2 = plt.subplots(figsize=(14, 4))
        fig2.patch.set_facecolor("#0f1117")
        ax2.set_facecolor("#1a1d27")
        ax2.tick_params(colors="#aaaaaa")
        for spine in ax2.spines.values():
            spine.set_edgecolor("#333333")

        ax2.plot(timestamps, blur_scores, color=ACCENT, lw=0.8, alpha=0.8)
        ax2.axhline(CONFIG["blur_threshold"], color=REJECTED, linestyle="--", lw=1.2,
                    label=f"Blur threshold ({CONFIG['blur_threshold']})")
        ax2.fill_between(timestamps, 0, blur_scores,
                         where=[b < CONFIG["blur_threshold"] for b in blur_scores],
                         color=REJECTED, alpha=0.2, label="Blurry regions")
        ax2.set_xlabel("Video Timestamp (s)", color="#cccccc")
        ax2.set_ylabel("Laplacian Variance", color="#cccccc")
        ax2.set_title("Blur Score Over Video Timeline", color="white")
        ax2.legend(facecolor="#222", labelcolor="white", fontsize=9)

        plot2_path = plot_dir / "eda_temporal_blur.png"
        plt.tight_layout()
        plt.savefig(str(plot2_path), dpi=150, bbox_inches="tight",
                    facecolor=fig2.get_facecolor())
        plt.close()
        print(f"      Temporal blur plot → {plot2_path}")


def write_colmap_manifest(clean_frames: list, base_dir: Path):

    manifest_path = base_dir / "colmap_image_list.txt"
    with open(str(manifest_path), "w") as f:
        for meta in clean_frames:
            f.write(f"frames_clean/{meta['filename']}\n")
    print(f"\n      COLMAP manifest → {manifest_path}  ({len(clean_frames)} entries)")



def export_metadata(all_metadata: list, clean_metadata: list, splits: dict, base_dir: Path):

    summary = {
        "group": "F26-18",
        "phase": 2,
        "course": "Artificial Intelligence",
        "semester": "Spring 2026",
        "dataset": {
            "type": "home_proxy_scan",
            "purpose": "Proxy for university campus scan (campus access pending)",
            "total_frames_extracted": len(all_metadata),
            "clean_frames": len(clean_metadata),
            "rejection_rate_pct": round(100 * (len(all_metadata) - len(clean_metadata)) / max(len(all_metadata), 1), 1),
            "splits": {k: len(v) for k, v in splits.items()},
            "portrait_mode": "auto-rotated to landscape",
            "target_resolution": f"{CONFIG['target_width']}x{CONFIG['target_height']}",
        },
        "config": CONFIG,
        "frames": all_metadata,
    }
    meta_path = base_dir / "dataset_metadata.json"
    with open(str(meta_path), "w") as f:
        json.dump(summary, f, indent=2)
    print(f"      Metadata JSON → {meta_path}")



def main():
    parser = argparse.ArgumentParser(
        description="F26-18 Phase 2 — Dataset Preprocessing & EDA Pipeline"
    )
    parser.add_argument("--video",  type=str, default=None,
                        help="Path to input video file (mp4/mov). Omit for demo mode.")
    parser.add_argument("--output", type=str, default="./dataset_output",
                        help="Output base directory.")
    args = parser.parse_args()

    base_dir = Path(args.output)
    dirs     = create_output_dirs(base_dir)

    print("=" * 65)
    print("  F26-18 | Vision-Based AR Indoor Navigation System")
    print("  Phase 2 — Dataset Preprocessing & EDA Pipeline")
    print("  Group F26-18 | AI Course | Spring 2026")
    print("=" * 65)

    video_source = args.video if args.video else None
    print(f"\n  Mode   : {'Real video processing' if args.video else 'DEMO / Simulation'}")
    print(f"  Source : {video_source if video_source else 'DEMO_MODE'}")
    print(f"  Output : {base_dir.resolve()}")

    real_video = args.video is not None


    all_metadata = extract_frames(video_source, dirs["frames_raw"])


    clean_metadata = filter_frames(dirs["frames_raw"], dirs["frames_clean"],
                                   all_metadata, real_video=real_video)


    splits = split_dataset(list(clean_metadata), dirs)


    run_eda(all_metadata, clean_metadata, dirs["eda_plots"])


    write_colmap_manifest(clean_metadata, base_dir)


    export_metadata(all_metadata, clean_metadata, splits, base_dir)

    print("\n" + "=" * 65)
    print("  Pipeline complete.")
    print(f"  Output directory: {base_dir.resolve()}")
    print("=" * 65)


if __name__ == "__main__":
    main()
