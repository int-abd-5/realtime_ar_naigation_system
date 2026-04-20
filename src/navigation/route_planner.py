import argparse
import json
import math
from dataclasses import dataclass
from heapq import heappop, heappush
from pathlib import Path


@dataclass
class Node:
    node_id: str
    name: str
    x: float
    z: float


def load_graph(base_dir: Path) -> tuple[dict[str, Node], dict[str, list[tuple[str, float]]]]:
    nodes_raw = json.loads((base_dir / "nodes.json").read_text(encoding="utf-8"))
    edges_raw = json.loads((base_dir / "edges.json").read_text(encoding="utf-8"))

    flat_nodes: list[dict] = []
    if isinstance(nodes_raw, list) and len(nodes_raw) == 1 and isinstance(nodes_raw[0], dict):
        container = nodes_raw[0]
        if "corner_nodes" in container or "door_nodes" in container:
            flat_nodes.extend(container.get("corner_nodes", []))
            flat_nodes.extend(container.get("door_nodes", []))
        else:
            flat_nodes.extend(nodes_raw)
    elif isinstance(nodes_raw, dict):
        flat_nodes.extend(nodes_raw.get("corner_nodes", []))
        flat_nodes.extend(nodes_raw.get("door_nodes", []))
    else:
        flat_nodes.extend(nodes_raw)

    nodes: dict[str, Node] = {}
    for item in flat_nodes:
        node_id = item["id"]
        node_name = item.get("name", node_id)
        x = float(item["x"])
        z = float(item.get("z", item.get("y", 0.0)))
        nodes[node_id] = Node(node_id=node_id, name=node_name, x=x, z=z)

    adj: dict[str, list[tuple[str, float]]] = {node_id: [] for node_id in nodes}
    for edge in edges_raw:
        src = edge["from"]
        dst = edge["to"]
        cost = float(edge["cost"])
        if src not in adj or dst not in adj:
            continue
        adj[src].append((dst, cost))
        adj[dst].append((src, cost))
    return nodes, adj


def heuristic(a: Node, b: Node) -> float:
    return abs(a.x - b.x) + abs(a.z - b.z)


def astar(
    nodes: dict[str, Node],
    adj: dict[str, list[tuple[str, float]]],
    start_id: str,
    goal_id: str,
) -> tuple[list[str], float]:
    open_heap: list[tuple[float, str]] = []
    heappush(open_heap, (0.0, start_id))

    came_from: dict[str, str] = {}
    g_score: dict[str, float] = {node_id: math.inf for node_id in nodes}
    g_score[start_id] = 0.0

    f_score: dict[str, float] = {node_id: math.inf for node_id in nodes}
    f_score[start_id] = heuristic(nodes[start_id], nodes[goal_id])

    while open_heap:
        _, current = heappop(open_heap)
        if current == goal_id:
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return path, g_score[goal_id]

        for neighbor, edge_cost in adj[current]:
            tentative = g_score[current] + edge_cost
            if tentative < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative
                f_score[neighbor] = tentative + heuristic(nodes[neighbor], nodes[goal_id])
                heappush(open_heap, (f_score[neighbor], neighbor))

    raise ValueError(f"No path found between {start_id} and {goal_id}.")


def nearest_node(nodes: dict[str, Node], x: float, z: float) -> str:
    return min(nodes, key=lambda node_id: abs(nodes[node_id].x - x) + abs(nodes[node_id].z - z))


def pretty_steps(path: list[str], nodes: dict[str, Node]) -> list[str]:
    steps: list[str] = []
    for idx in range(len(path) - 1):
        src = nodes[path[idx]]
        dst = nodes[path[idx + 1]]
        dist = abs(dst.x - src.x) + abs(dst.z - src.z)
        steps.append(f"{idx + 1}. Move from {src.name} to {dst.name} ({dist:.1f} m)")
    return steps


def main() -> None:
    parser = argparse.ArgumentParser(description="A* route planner for indoor navigation graph")
    parser.add_argument("--start-node", type=str, default=None, help="Start node ID (if known)")
    parser.add_argument("--goal-node", type=str, required=True, help="Goal node ID")
    parser.add_argument("--start-x", type=float, default=None, help="Start x coordinate")
    parser.add_argument("--start-z", type=float, default=None, help="Start z coordinate")
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent
    nodes, adj = load_graph(base_dir)

    if args.goal_node not in nodes:
        raise ValueError(f"Unknown goal node '{args.goal_node}'. Available: {list(nodes)}")

    if args.start_node is not None:
        if args.start_node not in nodes:
            raise ValueError(f"Unknown start node '{args.start_node}'. Available: {list(nodes)}")
        start = args.start_node
    else:
        if args.start_x is None or args.start_z is None:
            raise ValueError("Pass --start-node OR both --start-x and --start-z.")
        start = nearest_node(nodes, args.start_x, args.start_z)

    path, total_cost = astar(nodes, adj, start, args.goal_node)
    print(f"Start: {start} ({nodes[start].name})")
    print(f"Goal:  {args.goal_node} ({nodes[args.goal_node].name})")
    print(f"Path:  {' -> '.join(path)}")
    print(f"Cost:  {total_cost:.2f} m")
    print("Instructions:")
    for step in pretty_steps(path, nodes):
        print(step)


if __name__ == "__main__":
    main()
