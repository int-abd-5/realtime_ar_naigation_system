from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from .colmap_text_model import ColmapCamera, ColmapImage, read_cameras_text, read_images_text, read_points3d_text


@dataclass
class VisualPose:
    x: float
    y: float
    z: float
    inliers: int
    total_corr: int
    image_id: int


@dataclass
class SessionVisualState:
    last_best_image_id: Optional[int] = None


class VisualPnPLocalizer:
    def __init__(
        self,
        model_dir: Path,
        database_path: Path,
        max_candidates: int = 12,
        min_inliers: int = 24,
        match_ratio: float = 0.78,
    ) -> None:
        self.model_dir = model_dir
        self.database_path = database_path
        self.max_candidates = max_candidates
        self.min_inliers = min_inliers
        self.match_ratio = match_ratio
        self._sessions: dict[str, SessionVisualState] = {}

        self.cameras: dict[int, ColmapCamera] = {}
        self.images: dict[int, ColmapImage] = {}
        self.points3d: dict[int, tuple[float, float, float]] = {}
        self.descriptors: dict[int, np.ndarray] = {}
        self.sorted_image_ids: list[int] = []
        self.camera_matrix: Optional[np.ndarray] = None
        self.dist_coeffs: Optional[np.ndarray] = None
        self.ready: bool = False
        self.reason_not_ready: str = ""

        self.bf = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)
        self.sift = self._create_sift()

        self._load()

    def _create_sift(self):
        try:
            return cv2.SIFT_create(nfeatures=4096, descriptorType=cv2.CV_8U)
        except Exception:
            return cv2.SIFT_create(nfeatures=4096)

    def _load(self) -> None:
        cameras_txt = self.model_dir / "cameras.txt"
        images_txt = self.model_dir / "images.txt"
        points_txt = self.model_dir / "points3D.txt"
        if not cameras_txt.exists() or not images_txt.exists() or not points_txt.exists():
            self.reason_not_ready = f"Missing model text files in {self.model_dir}"
            return
        if not self.database_path.exists():
            self.reason_not_ready = f"Missing COLMAP database at {self.database_path}"
            return

        self.cameras = read_cameras_text(cameras_txt)
        self.images = read_images_text(images_txt)
        self.points3d = read_points3d_text(points_txt)
        self.descriptors = self._load_descriptors_sqlite(self.database_path)

        valid_ids = []
        for image_id, im in self.images.items():
            desc = self.descriptors.get(image_id)
            if desc is None or desc.size == 0:
                continue
            if len(im.point3d_ids) == 0:
                continue
            valid_ids.append(image_id)
        self.sorted_image_ids = sorted(valid_ids)

        if not self.sorted_image_ids:
            self.reason_not_ready = "No valid image descriptors matched with model images."
            return

        first_img = self.images[self.sorted_image_ids[0]]
        cam = self.cameras.get(first_img.camera_id)
        if cam is None:
            self.reason_not_ready = "Camera missing for first model image."
            return
        self.camera_matrix, self.dist_coeffs = self._camera_to_opencv(cam)
        self.ready = True

    def _camera_to_opencv(self, cam: ColmapCamera) -> tuple[np.ndarray, np.ndarray]:
        model = cam.model.upper()
        p = cam.params
        if model == "SIMPLE_PINHOLE":
            f, cx, cy = p[0], p[1], p[2]
            fx = fy = f
            dist = np.zeros((4, 1), dtype=np.float64)
        elif model == "PINHOLE":
            fx, fy, cx, cy = p[0], p[1], p[2], p[3]
            dist = np.zeros((4, 1), dtype=np.float64)
        elif model == "SIMPLE_RADIAL":
            f, cx, cy, k1 = p[0], p[1], p[2], p[3]
            fx = fy = f
            dist = np.array([[k1], [0.0], [0.0], [0.0]], dtype=np.float64)
        elif model == "RADIAL":
            f, cx, cy, k1, k2 = p[0], p[1], p[2], p[3], p[4]
            fx = fy = f
            dist = np.array([[k1], [k2], [0.0], [0.0]], dtype=np.float64)
        elif model == "OPENCV":
            fx, fy, cx, cy, k1, k2, p1, p2 = p[:8]
            dist = np.array([[k1], [k2], [p1], [p2]], dtype=np.float64)
        else:
            # Fallback assumption for unhandled models.
            fx = fy = p[0]
            cx = p[1]
            cy = p[2]
            dist = np.zeros((4, 1), dtype=np.float64)
        k = np.array([[fx, 0.0, cx], [0.0, fy, cy], [0.0, 0.0, 1.0]], dtype=np.float64)
        return k, dist

    def _load_descriptors_sqlite(self, db_path: Path) -> dict[int, np.ndarray]:
        out: dict[int, np.ndarray] = {}
        conn = sqlite3.connect(str(db_path))
        try:
            cur = conn.cursor()
            cur.execute("SELECT image_id, rows, cols, data FROM descriptors")
            for image_id, rows, cols, data in cur.fetchall():
                if rows is None or cols is None or data is None or rows == 0 or cols == 0:
                    continue
                arr = np.frombuffer(data, dtype=np.uint8)
                try:
                    desc = arr.reshape((rows, cols))
                except Exception:
                    continue
                out[int(image_id)] = desc
        finally:
            conn.close()
        return out

    def _session_state(self, session_id: str) -> SessionVisualState:
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionVisualState()
        return self._sessions[session_id]

    def _candidate_ids(self, session_id: str) -> list[int]:
        state = self._session_state(session_id)
        ids = self.sorted_image_ids
        if not ids:
            return []

        chosen: list[int] = []
        seen = set()

        # Global anchors for relocalization when session is cold.
        stride = max(1, len(ids) // max(6, self.max_candidates))
        for i in range(0, len(ids), stride):
            img_id = ids[i]
            if img_id not in seen:
                seen.add(img_id)
                chosen.append(img_id)
            if len(chosen) >= self.max_candidates:
                break

        # Local window around last successful frame for temporal continuity.
        if state.last_best_image_id is not None and state.last_best_image_id in ids:
            center = ids.index(state.last_best_image_id)
            for offset in range(-15, 16):
                j = center + offset
                if j < 0 or j >= len(ids):
                    continue
                img_id = ids[j]
                if img_id not in seen:
                    seen.add(img_id)
                    chosen.append(img_id)
                if len(chosen) >= max(self.max_candidates * 2, 20):
                    break

        return chosen

    def _ensure_uint8_desc(self, desc: np.ndarray) -> np.ndarray:
        if desc.dtype == np.uint8:
            return desc
        clipped = np.clip(np.rint(desc), 0, 255).astype(np.uint8)
        return clipped

    def _extract_query_features(self, img_bgr: np.ndarray) -> tuple[list[cv2.KeyPoint], Optional[np.ndarray]]:
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        kps, desc = self.sift.detectAndCompute(gray, None)
        if desc is None or len(kps) == 0:
            return [], None

        # Keep strongest keypoints for speed/stability.
        if len(kps) > 1600:
            idx = sorted(range(len(kps)), key=lambda i: kps[i].response, reverse=True)[:1600]
            kps = [kps[i] for i in idx]
            desc = desc[idx]

        desc_u8 = self._ensure_uint8_desc(desc)
        return kps, desc_u8

    def localize(self, session_id: str, jpeg_bytes: bytes) -> Optional[VisualPose]:
        if not self.ready:
            return None

        arr = np.frombuffer(jpeg_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return None

        query_kps, query_desc = self._extract_query_features(img)
        if query_desc is None or len(query_kps) < 20:
            return None

        best_pose: Optional[VisualPose] = None
        best_score = -1

        for image_id in self._candidate_ids(session_id):
            map_desc = self.descriptors.get(image_id)
            model_im = self.images.get(image_id)
            if map_desc is None or model_im is None:
                continue
            if len(model_im.point3d_ids) == 0:
                continue

            matches = self.bf.knnMatch(query_desc, map_desc, k=2)
            good = []
            for pair in matches:
                if len(pair) < 2:
                    continue
                m, n = pair[0], pair[1]
                if m.distance < self.match_ratio * n.distance:
                    good.append(m)
            if len(good) < max(25, self.min_inliers):
                continue

            obj_pts = []
            img_pts = []
            for m in good:
                q_idx = int(m.queryIdx)
                t_idx = int(m.trainIdx)
                if t_idx >= len(model_im.point3d_ids):
                    continue
                p3d_id = model_im.point3d_ids[t_idx]
                if p3d_id == -1:
                    continue
                xyz = self.points3d.get(p3d_id)
                if xyz is None:
                    continue
                kp = query_kps[q_idx]
                obj_pts.append([xyz[0], xyz[1], xyz[2]])
                img_pts.append([kp.pt[0], kp.pt[1]])

            if len(obj_pts) < max(12, self.min_inliers):
                continue

            obj_np = np.asarray(obj_pts, dtype=np.float64)
            img_np = np.asarray(img_pts, dtype=np.float64)

            ok, rvec, tvec, inliers = cv2.solvePnPRansac(
                objectPoints=obj_np,
                imagePoints=img_np,
                cameraMatrix=self.camera_matrix,
                distCoeffs=self.dist_coeffs,
                iterationsCount=200,
                reprojectionError=6.0,
                confidence=0.999,
                flags=cv2.SOLVEPNP_ITERATIVE,
            )
            if not ok or inliers is None:
                continue

            inlier_count = int(len(inliers))
            if inlier_count < self.min_inliers:
                continue

            rmat, _ = cv2.Rodrigues(rvec)
            cam_center = -rmat.T @ tvec
            x, y, z = float(cam_center[0, 0]), float(cam_center[1, 0]), float(cam_center[2, 0])

            pose = VisualPose(
                x=x,
                y=y,
                z=z,
                inliers=inlier_count,
                total_corr=len(obj_pts),
                image_id=image_id,
            )
            if pose.inliers > best_score:
                best_score = pose.inliers
                best_pose = pose

        if best_pose is not None:
            self._session_state(session_id).last_best_image_id = best_pose.image_id
        return best_pose
