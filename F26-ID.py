import argparse
import json
from datetime import datetime
from pathlib import Path

from src.localization.map_loader import load_active_map
from src.navigation.route_planner import astar, load_graph, nearest_node, pretty_steps


def main() -> None:
    parser = argparse.ArgumentParser(description="F26-ID submission runner")
    parser.add_argument("--repo-root", type=str, default=r"C:\Users\Abdul\Desktop\ai_proj_indoor_navigation")
    parser.add_argument("--start-node", type=str, default=None)
    parser.add_argument("--start-x", type=float, default=None)
    parser.add_argument("--start-z", type=float, default=None)
    parser.add_argument("--goal-node", type=str, required=True)
    parser.add_argument("--save-output", action="store_true")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    map_info = load_active_map(str(repo_root))
    nodes, adj = load_graph(repo_root / "src" / "navigation")

    if args.goal_node not in nodes:
        raise ValueError(f"Unknown goal node '{args.goal_node}'. Available: {list(nodes.keys())}")

    if args.start_node is not None:
        if args.start_node not in nodes:
            raise ValueError(f"Unknown start node '{args.start_node}'. Available: {list(nodes.keys())}")
        start = args.start_node
    else:
        if args.start_x is None or args.start_z is None:
            raise ValueError("Provide --start-node or both --start-x and --start-z.")
        start = nearest_node(nodes, args.start_x, args.start_z)

    path, cost = astar(nodes, adj, start, args.goal_node)
    instructions = pretty_steps(path, nodes)

    print("Loaded map:")
    print(f"- Active map: {map_info['active_map']}")
    print(f"- Fused file: {map_info['fused_ply']}")
    print(f"- Mesh file:  {map_info['mesh_ply']}")
    print("")
    print(f"Start node: {start} ({nodes[start].name})")
    print(f"Goal node:  {args.goal_node} ({nodes[args.goal_node].name})")
    print(f"Path:       {' -> '.join(path)}")
    print(f"Cost:       {cost:.3f}")
    print("Instructions:")
    for step in instructions:
        print(step)

    if args.save_output:
        out_dir = repo_root / "outputs" / "routes"
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = out_dir / f"route_{stamp}.json"
        payload = {
            "timestamp": stamp,
            "active_map": map_info["active_map"],
            "start_node": start,
            "goal_node": args.goal_node,
            "path": path,
            "cost": cost,
            "instructions": instructions,
        }
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print("")
        print(f"Saved route output: {out_path}")


if __name__ == "__main__":
    main()
