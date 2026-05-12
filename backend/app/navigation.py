from __future__ import annotations

import json
import math
from dataclasses import dataclass
from heapq import heappop, heappush
from pathlib import Path
from typing import Optional


@dataclass
class NavNode:
    node_id: str
    x: float
    z: float
    name: str


class NavigationGraph:
    def __init__(self, nodes_path: Path, edges_path: Path) -> None:
        self.nodes_path = nodes_path
        self.edges_path = edges_path
        self.nodes, self.adj = self._load_graph()

    def _load_graph(self) -> tuple[dict[str, NavNode], dict[str, list[tuple[str, float]]]]:
        nodes_raw = json.loads(self.nodes_path.read_text(encoding="utf-8"))
        edges_raw = json.loads(self.edges_path.read_text(encoding="utf-8"))

        flat_nodes: list[dict] = []
        if isinstance(nodes_raw, list) and len(nodes_raw) == 1 and isinstance(nodes_raw[0], dict):
            container = nodes_raw[0]
            flat_nodes.extend(container.get("corner_nodes", []))
            flat_nodes.extend(container.get("door_nodes", []))
        elif isinstance(nodes_raw, dict):
            flat_nodes.extend(nodes_raw.get("corner_nodes", []))
            flat_nodes.extend(nodes_raw.get("door_nodes", []))
        else:
            flat_nodes.extend(nodes_raw)

        nodes: dict[str, NavNode] = {}
        for item in flat_nodes:
            nid = item["id"]
            nodes[nid] = NavNode(
                node_id=nid,
                x=float(item["x"]),
                z=float(item.get("z", item.get("y", 0.0))),
                name=item.get("name", nid),
            )

        adj: dict[str, list[tuple[str, float]]] = {k: [] for k in nodes}
        for e in edges_raw:
            a = e["from"]
            b = e["to"]
            c = float(e["cost"])
            if a in adj and b in adj:
                adj[a].append((b, c))
                adj[b].append((a, c))
        return nodes, adj

    def nearest_node(self, x: float, z: float) -> Optional[str]:
        if not self.nodes:
            return None
        return min(self.nodes.keys(), key=lambda k: abs(self.nodes[k].x - x) + abs(self.nodes[k].z - z))

    def astar(self, start_id: str, goal_id: str) -> tuple[list[str], float]:
        def h(a: str, b: str) -> float:
            na, nb = self.nodes[a], self.nodes[b]
            return abs(na.x - nb.x) + abs(na.z - nb.z)

        open_heap: list[tuple[float, str]] = []
        heappush(open_heap, (0.0, start_id))
        g: dict[str, float] = {k: math.inf for k in self.nodes}
        g[start_id] = 0.0
        came: dict[str, str] = {}

        while open_heap:
            _, cur = heappop(open_heap)
            if cur == goal_id:
                path = [cur]
                while cur in came:
                    cur = came[cur]
                    path.append(cur)
                path.reverse()
                return path, g[goal_id]

            for nxt, edge in self.adj.get(cur, []):
                cand = g[cur] + edge
                if cand < g[nxt]:
                    g[nxt] = cand
                    came[nxt] = cur
                    heappush(open_heap, (cand + h(nxt, goal_id), nxt))

        raise ValueError(f"No path found from {start_id} to {goal_id}")

    def next_instruction(
        self, current_heading_deg: float, path: list[str], current_index: int, arrived_threshold: float = 1.0
    ) -> tuple[str, Optional[str]]:
        if not path or current_index >= len(path) - 1:
            return "ARRIVED", None

        cur = self.nodes[path[current_index]]
        nxt = self.nodes[path[current_index + 1]]
        dx = nxt.x - cur.x
        dz = nxt.z - cur.z
        target_bearing = (math.degrees(math.atan2(dx, dz)) + 360.0) % 360.0
        delta = ((target_bearing - current_heading_deg + 540.0) % 360.0) - 180.0

        if abs(delta) < 20.0:
            return "GO_STRAIGHT", path[current_index + 1]
        if delta > 0:
            return "TURN_RIGHT", path[current_index + 1]
        return "TURN_LEFT", path[current_index + 1]
