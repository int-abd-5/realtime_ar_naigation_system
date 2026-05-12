from __future__ import annotations

import argparse
import json
from pathlib import Path


def manhattan(a: dict, b: dict) -> float:
    return abs(float(a["x"]) - float(b["x"])) + abs(float(a["z"]) - float(b["z"]))


def load_nodes(nodes_path: Path) -> tuple[list[dict], list[dict]]:
    raw = json.loads(nodes_path.read_text(encoding="utf-8"))
    if isinstance(raw, list) and raw and isinstance(raw[0], dict):
        container = raw[0]
        corners = list(container.get("corner_nodes", []))
        doors = list(container.get("door_nodes", []))
    elif isinstance(raw, dict):
        corners = list(raw.get("corner_nodes", []))
        doors = list(raw.get("door_nodes", []))
    else:
        corners = [n for n in raw if str(n.get("type", "")).startswith("corner")]
        doors = [n for n in raw if str(n.get("type", "")).startswith("door")]
    return corners, doors


def add_edge(edge_map: dict[tuple[str, str], float], a: dict, b: dict) -> None:
    key = tuple(sorted((a["id"], b["id"])))
    edge_map[key] = round(manhattan(a, b), 6)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate navigation edges from corner/door nodes.")
    parser.add_argument("--nodes", required=True, help="Path to nodes.json")
    parser.add_argument("--edges", required=True, help="Path to output edges.json")
    parser.add_argument(
        "--door-second-threshold",
        type=float,
        default=2.2,
        help="Connect a door to second nearest corner only if Manhattan distance <= threshold.",
    )
    args = parser.parse_args()

    nodes_path = Path(args.nodes).resolve()
    edges_path = Path(args.edges).resolve()
    corners, doors = load_nodes(nodes_path)

    if not corners:
        raise ValueError("No corner_nodes found in nodes file.")

    # Corridor backbone: link corners in monotonic path order.
    sorted_corners = sorted(corners, key=lambda n: (float(n["z"]), float(n["x"])))

    edge_map: dict[tuple[str, str], float] = {}
    for i in range(len(sorted_corners) - 1):
        add_edge(edge_map, sorted_corners[i], sorted_corners[i + 1])

    # Attach each door to nearest corner, plus optional second nearest for better routing flexibility.
    for door in doors:
        dists = sorted(((manhattan(door, c), c) for c in corners), key=lambda t: t[0])
        if not dists:
            continue
        add_edge(edge_map, door, dists[0][1])
        if len(dists) > 1 and dists[1][0] <= args.door_second_threshold:
            add_edge(edge_map, door, dists[1][1])

    edges = [{"from": a, "to": b, "cost": c} for (a, b), c in sorted(edge_map.items())]
    edges_path.write_text(json.dumps(edges, indent=2), encoding="utf-8")

    print(f"Wrote {len(edges)} edges to {edges_path}")


if __name__ == "__main__":
    main()
