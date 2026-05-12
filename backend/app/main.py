from __future__ import annotations

import time
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect

from .localization import Localizer
from .map_loader import MapLoader
from .navigation import NavigationGraph
from .schemas import DestinationUpdateRequest, FrameMessage, PoseMock, StartSessionRequest
from .session_manager import SessionManager
from .settings import load_settings

settings = load_settings()
app = FastAPI(title="Indoor Navigation Backend", version="0.1.0")

map_loader = MapLoader(settings.map_config_path)
graph = NavigationGraph(settings.nodes_json_path, settings.edges_json_path)
session_manager = SessionManager(graph)
localizer = Localizer(
    mode=settings.localization_mode,
    visual_model_path=settings.visual_model_path,
    visual_database_path=settings.visual_database_path,
    visual_max_candidates=settings.visual_max_candidates,
    visual_min_inliers=settings.visual_min_inliers,
    visual_match_ratio=settings.visual_match_ratio,
)


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "mode": settings.localization_mode,
        "visual_ready": localizer.visual_ready,
        "visual_reason_not_ready": localizer.visual_reason_not_ready if not localizer.visual_ready else "",
    }


@app.get("/api/v1/map")
def map_summary() -> dict[str, Any]:
    return map_loader.summary()


@app.get("/api/v1/destinations")
def list_destinations() -> dict[str, Any]:
    destinations = []
    for node_id, node in graph.nodes.items():
        destinations.append(
            {
                "id": node_id,
                "name": node.name,
                "x": node.x,
                "z": node.z,
            }
        )
    return {"destinations": destinations}


@app.post("/api/v1/session/start")
def start_session(req: StartSessionRequest) -> dict[str, str]:
    if req.destination_id not in graph.nodes:
        raise HTTPException(status_code=400, detail=f"Unknown destination node: {req.destination_id}")
    start_node_id = req.start_node_id
    if start_node_id is None:
        start_node_id = "C1" if "C1" in graph.nodes else sorted(graph.nodes.keys())[0]
    if start_node_id not in graph.nodes:
        raise HTTPException(status_code=400, detail=f"Unknown start node: {start_node_id}")

    s = session_manager.start_session(req.destination_id, start_node_id)
    start_node = graph.nodes[start_node_id]
    localizer.reset_session(s.session_id, start_node.x, start_node.z)
    return {"session_id": s.session_id, "start_node_id": start_node_id}


@app.post("/api/v1/session/{session_id}/destination")
def update_destination(session_id: str, req: DestinationUpdateRequest) -> dict[str, str]:
    if session_id not in session_manager.sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    if req.destination_id not in graph.nodes:
        raise HTTPException(status_code=400, detail=f"Unknown destination node: {req.destination_id}")
    session_manager.set_destination(session_id, req.destination_id)
    return {"status": "ok"}


@app.get("/api/v1/session/{session_id}/state")
def get_state(session_id: str) -> dict[str, Any]:
    if session_id not in session_manager.sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return session_manager.state(session_id).model_dump()


# Compatibility endpoint for your current Android HTTP polling style.
@app.get("/api/v1/pose")
def get_pose_mock() -> PoseMock:
    ts = int(time.time() * 1000)
    loc = localizer.localize(session_id="compat", jpeg_b64="", heading_deg=0.0, timestamp_ms=ts)
    return PoseMock(
        timestamp=ts,
        position=loc.position,
        rotation=loc.rotation,
        targetLabel="mock-target",
    )


@app.websocket("/api/v1/session/{session_id}/stream")
async def ws_stream(session_id: str, websocket: WebSocket) -> None:
    if session_id not in session_manager.sessions:
        await websocket.accept()
        await websocket.send_json({"type": "error", "message": "session_not_found"})
        await websocket.close()
        return

    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong", "timestamp_ms": int(time.time() * 1000)})
                continue
            msg = FrameMessage(**data)
            loc = localizer.localize(
                session_id=session_id,
                jpeg_b64=msg.jpeg_b64,
                heading_deg=msg.heading_deg if msg.heading_deg is not None else 0.0,
                timestamp_ms=msg.timestamp_ms,
            )
            heading = msg.heading_deg if msg.heading_deg is not None else 0.0
            nav = session_manager.update_navigation(
                session_id=session_id,
                position=loc.position,
                rotation=loc.rotation,
                confidence=loc.confidence,
                heading_deg=heading,
            )
            await websocket.send_json(nav.model_dump())
    except WebSocketDisconnect:
        return
    except Exception as ex:
        await websocket.send_json({"type": "error", "message": str(ex)})
        await websocket.close()
