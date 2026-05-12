from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class ColmapCamera:
    camera_id: int
    model: str
    width: int
    height: int
    params: list[float]


@dataclass
class ColmapImage:
    image_id: int
    qvec: tuple[float, float, float, float]
    tvec: tuple[float, float, float]
    camera_id: int
    name: str
    point3d_ids: list[int]


def _non_comment_lines(path: Path) -> list[str]:
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        lines.append(s)
    return lines


def read_cameras_text(path: Path) -> dict[int, ColmapCamera]:
    cameras: dict[int, ColmapCamera] = {}
    for line in _non_comment_lines(path):
        tokens = line.split()
        if len(tokens) < 5:
            continue
        cam_id = int(tokens[0])
        model = tokens[1]
        width = int(tokens[2])
        height = int(tokens[3])
        params = [float(x) for x in tokens[4:]]
        cameras[cam_id] = ColmapCamera(
            camera_id=cam_id,
            model=model,
            width=width,
            height=height,
            params=params,
        )
    return cameras


def read_images_text(path: Path) -> dict[int, ColmapImage]:
    raw_lines = path.read_text(encoding="utf-8").splitlines()
    lines = [ln.strip() for ln in raw_lines if ln.strip() and not ln.strip().startswith("#")]

    images: dict[int, ColmapImage] = {}
    i = 0
    while i + 1 < len(lines):
        header = lines[i].split()
        if len(header) < 10:
            i += 1
            continue
        image_id = int(header[0])
        qvec = (float(header[1]), float(header[2]), float(header[3]), float(header[4]))
        tvec = (float(header[5]), float(header[6]), float(header[7]))
        camera_id = int(header[8])
        name = header[9]

        points_line = lines[i + 1].split()
        point3d_ids: list[int] = []
        # POINTS2D triplets: X, Y, POINT3D_ID
        for j in range(2, len(points_line), 3):
            try:
                point3d_ids.append(int(points_line[j]))
            except Exception:
                point3d_ids.append(-1)

        images[image_id] = ColmapImage(
            image_id=image_id,
            qvec=qvec,
            tvec=tvec,
            camera_id=camera_id,
            name=name,
            point3d_ids=point3d_ids,
        )
        i += 2
    return images


def read_points3d_text(path: Path) -> dict[int, tuple[float, float, float]]:
    points: dict[int, tuple[float, float, float]] = {}
    for line in _non_comment_lines(path):
        tokens = line.split()
        if len(tokens) < 4:
            continue
        pid = int(tokens[0])
        xyz = (float(tokens[1]), float(tokens[2]), float(tokens[3]))
        points[pid] = xyz
    return points
