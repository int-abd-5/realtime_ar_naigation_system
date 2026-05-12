from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

from .navigation import NavigationGraph
from .schemas import NavigationUpdate, Position, Rotation, SessionState


@dataclass
class NavSession:
    session_id: str
    destination_id: str
    current_node: Optional[str] = None
    next_node: Optional[str] = None
    path: list[str] = field(default_factory=list)
    path_index: int = 0
    instruction: str = "RELOCALIZING"
    distance_m: Optional[float] = None
    confidence: float = 0.0
    pending_node: Optional[str] = None
    pending_node_hits: int = 0
    last_instruction_change_ms: int = 0


class SessionManager:
    NODE_SWITCH_MIN_CONFIDENCE = 0.60
    NODE_SWITCH_CONFIRM_FRAMES = 2
    INSTRUCTION_HOLD_MS = 1200

    def __init__(self, graph: NavigationGraph) -> None:
        self.graph = graph
        self.sessions: dict[str, NavSession] = {}

    def start_session(self, destination_id: str, start_node_id: Optional[str]) -> NavSession:
        sid = str(uuid.uuid4())
        s = NavSession(session_id=sid, destination_id=destination_id, current_node=start_node_id)
        self.sessions[sid] = s
        return s

    def get(self, session_id: str) -> NavSession:
        return self.sessions[session_id]

    def set_destination(self, session_id: str, destination_id: str) -> NavSession:
        s = self.sessions[session_id]
        s.destination_id = destination_id
        s.path = []
        s.path_index = 0
        s.instruction = "RELOCALIZING"
        s.next_node = None
        s.distance_m = None
        s.last_instruction_change_ms = int(time.time() * 1000)
        return s

    def _stable_node(self, s: NavSession, candidate: Optional[str], confidence: float) -> Optional[str]:
        if candidate is None:
            return s.current_node

        if s.current_node is None:
            s.current_node = candidate
            s.pending_node = None
            s.pending_node_hits = 0
            return s.current_node

        if candidate == s.current_node:
            s.pending_node = None
            s.pending_node_hits = 0
            return s.current_node

        if confidence < self.NODE_SWITCH_MIN_CONFIDENCE:
            return s.current_node

        if s.pending_node != candidate:
            s.pending_node = candidate
            s.pending_node_hits = 1
            return s.current_node

        s.pending_node_hits += 1
        if s.pending_node_hits >= self.NODE_SWITCH_CONFIRM_FRAMES:
            s.current_node = candidate
            s.pending_node = None
            s.pending_node_hits = 0
        return s.current_node

    def _debounced_instruction(
        self,
        s: NavSession,
        now_ms: int,
        proposed_instruction: str,
        proposed_next_node: Optional[str],
    ) -> tuple[str, Optional[str]]:
        if s.last_instruction_change_ms == 0:
            s.last_instruction_change_ms = now_ms
            return proposed_instruction, proposed_next_node

        if proposed_instruction == s.instruction:
            return proposed_instruction, proposed_next_node

        if proposed_instruction == "ARRIVED":
            s.last_instruction_change_ms = now_ms
            return proposed_instruction, proposed_next_node

        if now_ms - s.last_instruction_change_ms < self.INSTRUCTION_HOLD_MS:
            return s.instruction, s.next_node

        s.last_instruction_change_ms = now_ms
        return proposed_instruction, proposed_next_node

    def update_navigation(
        self, session_id: str, position: Position, rotation: Rotation, confidence: float, heading_deg: float
    ) -> NavigationUpdate:
        s = self.sessions[session_id]
        now_ms = int(time.time() * 1000)
        nearest = self.graph.nearest_node(position.x, position.z)
        stable_node = self._stable_node(s, nearest, confidence)
        s.confidence = confidence

        next_node = None
        instruction = "RELOCALIZING"
        distance_m = None

        if stable_node and s.destination_id in self.graph.nodes:
            try:
                s.path, s.distance_m = self.graph.astar(stable_node, s.destination_id)
                s.path_index = 0
                instruction, next_node = self.graph.next_instruction(heading_deg, s.path, s.path_index)
                instruction, next_node = self._debounced_instruction(
                    s=s,
                    now_ms=now_ms,
                    proposed_instruction=instruction,
                    proposed_next_node=next_node,
                )
                distance_m = s.distance_m
            except Exception:
                instruction = "RELOCALIZING"
                next_node = None
                distance_m = None

        s.instruction = instruction
        s.next_node = next_node
        s.distance_m = distance_m

        return NavigationUpdate(
            pose=position,
            rotation=rotation,
            confidence=confidence,
            nearest_node=stable_node,
            next_node=next_node,
            instruction=instruction,
            distance_m=distance_m,
            target_label=s.destination_id,
        )

    def state(self, session_id: str) -> SessionState:
        s = self.sessions[session_id]
        return SessionState(
            session_id=s.session_id,
            destination_id=s.destination_id,
            current_node=s.current_node,
            next_node=s.next_node,
            instruction=s.instruction,
            distance_m=s.distance_m,
            confidence=s.confidence,
        )
