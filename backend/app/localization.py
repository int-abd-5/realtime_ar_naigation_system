from __future__ import annotations

import base64
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .schemas import Position, Rotation
from .visual_localizer import VisualPnPLocalizer


@dataclass
class LocalizationResult:
    position: Position
    rotation: Rotation
    confidence: float


@dataclass
class SessionPose:
    x: float
    z: float
    last_ts: Optional[int]


class Localizer:
    def __init__(
        self,
        mode: str = "mock",
        visual_model_path: Optional[Path] = None,
        visual_database_path: Optional[Path] = None,
        visual_max_candidates: int = 12,
        visual_min_inliers: int = 24,
        visual_match_ratio: float = 0.78,
    ) -> None:
        self.mode = mode
        self._sessions: dict[str, SessionPose] = {}
        self.visual: Optional[VisualPnPLocalizer] = None

        if mode in ("visual", "hybrid") and visual_model_path is not None and visual_database_path is not None:
            self.visual = VisualPnPLocalizer(
                model_dir=visual_model_path,
                database_path=visual_database_path,
                max_candidates=visual_max_candidates,
                min_inliers=visual_min_inliers,
                match_ratio=visual_match_ratio,
            )

    @property
    def visual_ready(self) -> bool:
        return self.visual is not None and self.visual.ready

    @property
    def visual_reason_not_ready(self) -> str:
        if self.visual is None:
            return "visual localizer not initialized"
        return self.visual.reason_not_ready

    def _decode_jpeg_b64(self, payload: str) -> Optional[bytes]:
        try:
            return base64.b64decode(payload)
        except Exception:
            return None

    def reset_session(self, session_id: str, start_x: float, start_z: float) -> None:
        self._sessions[session_id] = SessionPose(x=start_x, z=start_z, last_ts=None)

    def _state(self, session_id: str) -> SessionPose:
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionPose(x=0.0, z=0.0, last_ts=None)
        return self._sessions[session_id]

    def _dead_reckoning(self, session_id: str, heading_deg: Optional[float], timestamp_ms: int) -> LocalizationResult:
        state = self._state(session_id)
        if state.last_ts is None:
            state.last_ts = timestamp_ms
        dt = max(0.0, (timestamp_ms - state.last_ts) / 1000.0)
        state.last_ts = timestamp_ms

        if heading_deg is None:
            heading_deg = 0.0

        speed_mps = 0.40
        rad = math.radians(float(heading_deg))
        state.x += float(math.sin(rad) * speed_mps * dt)
        state.z += float(math.cos(rad) * speed_mps * dt)

        half = rad / 2.0
        qy = float(math.sin(half))
        qw = float(math.cos(half))
        return LocalizationResult(
            position=Position(x=state.x, y=0.0, z=state.z),
            rotation=Rotation(qx=0.0, qy=qy, qz=0.0, qw=qw),
            confidence=0.25,
        )

    def _hold_position(self, session_id: str, heading_deg: Optional[float], timestamp_ms: int) -> LocalizationResult:
        state = self._state(session_id)
        state.last_ts = timestamp_ms
        heading = 0.0 if heading_deg is None else float(heading_deg)
        rad = math.radians(heading)
        half = rad / 2.0
        return LocalizationResult(
            position=Position(x=state.x, y=0.0, z=state.z),
            rotation=Rotation(qx=0.0, qy=float(math.sin(half)), qz=0.0, qw=float(math.cos(half))),
            confidence=0.25,
        )

    def localize(
        self, session_id: str, jpeg_b64: str, heading_deg: Optional[float], timestamp_ms: int
    ) -> LocalizationResult:
        raw = self._decode_jpeg_b64(jpeg_b64)

        if self.mode == "visual" and self.visual_ready and raw is not None:
            pose = self.visual.localize(session_id=session_id, jpeg_bytes=raw)
            if pose is not None:
                state = self._state(session_id)
                state.x = pose.x
                state.z = pose.z
                state.last_ts = timestamp_ms

                # Keep yaw aligned to phone heading for stable arrow orientation.
                heading = 0.0 if heading_deg is None else float(heading_deg)
                rad = math.radians(heading)
                half = rad / 2.0
                return LocalizationResult(
                    position=Position(x=pose.x, y=pose.y, z=pose.z),
                    rotation=Rotation(qx=0.0, qy=float(math.sin(half)), qz=0.0, qw=float(math.cos(half))),
                    confidence=min(0.99, 0.55 + 0.02 * pose.inliers),
                )
            return self._hold_position(session_id, heading_deg, timestamp_ms)

        if self.mode == "hybrid" and self.visual_ready and raw is not None:
            pose = self.visual.localize(session_id=session_id, jpeg_bytes=raw)
            if pose is not None:
                state = self._state(session_id)
                state.x = pose.x
                state.z = pose.z
                state.last_ts = timestamp_ms
                heading = 0.0 if heading_deg is None else float(heading_deg)
                rad = math.radians(heading)
                half = rad / 2.0
                return LocalizationResult(
                    position=Position(x=pose.x, y=pose.y, z=pose.z),
                    rotation=Rotation(qx=0.0, qy=float(math.sin(half)), qz=0.0, qw=float(math.cos(half))),
                    confidence=min(0.98, 0.52 + 0.02 * pose.inliers),
                )
            return self._hold_position(session_id, heading_deg, timestamp_ms)

        # Default path (mock or visual unavailable)
        dr = self._dead_reckoning(session_id, heading_deg, timestamp_ms)
        payload_kb = (len(raw) / 1024.0) if raw is not None else 0.0
        dr.confidence = max(dr.confidence, max(0.15, min(0.90, payload_kb / 140.0)))
        return dr
