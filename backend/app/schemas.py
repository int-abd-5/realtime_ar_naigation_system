from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class Position(BaseModel):
    x: float
    y: float
    z: float


class Rotation(BaseModel):
    qx: float
    qy: float
    qz: float
    qw: float


class PoseMock(BaseModel):
    timestamp: int
    position: Position
    rotation: Rotation
    targetLabel: str


class StartSessionRequest(BaseModel):
    destination_id: str = Field(..., description="Destination node ID")
    start_node_id: Optional[str] = Field(default=None, description="Optional starting node")


class DestinationUpdateRequest(BaseModel):
    destination_id: str


class SessionState(BaseModel):
    session_id: str
    destination_id: str
    current_node: Optional[str]
    next_node: Optional[str]
    instruction: str
    distance_m: Optional[float]
    confidence: float


class FrameMessage(BaseModel):
    type: Literal["frame"]
    timestamp_ms: int
    jpeg_b64: str
    heading_deg: Optional[float] = None


class NavigationUpdate(BaseModel):
    type: Literal["nav_update"] = "nav_update"
    pose: Position
    rotation: Rotation
    confidence: float
    nearest_node: Optional[str]
    next_node: Optional[str]
    instruction: str
    distance_m: Optional[float]
    target_label: str
