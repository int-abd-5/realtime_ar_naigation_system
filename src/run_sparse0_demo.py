import argparse
from pathlib import Path

from localization.map_loader import load_active_map
from navigation.route_planner import astar, load_graph, nearest_node, pretty_steps


def main() -> None:
    parser = argparse.ArgumentParser(description="Sparse0 baseline demo: map load + nearest-node + A* route")
    parser.add_argument("--repo-root", type=str, required=True, help="Absolute path of repository root")
    parser.add_argument("--x", type=float, required=True, help="Current user x coordinate")
    parser.add_argument("--z", type=float, required=True, help="Current user z coordinate")
    parser.add_argument("--goal-node", type=str, required=True, help="Destination node id")
    args = parser.parse_args()

    map_info = load_active_map(args.repo_root)
    print("Loaded map:")
    print(f"- Active map: {map_info['active_map']}")
    print(f"- Fused file: {map_info['fused_ply']}")
    print(f"- Mesh file:  {map_info['mesh_ply']}")

    nav_dir = Path(args.repo_root) / "src" / "navigation"
    nodes, adj = load_graph(nav_dir)
    start_node = nearest_node(nodes, args.x, args.z)

    path, total_cost = astar(nodes, adj, start_node, args.goal_node)
    print("")
    print(f"Current pose: ({args.x:.2f}, {args.z:.2f})")
    print(f"Start node:   {start_node} ({nodes[start_node].name})")
    print(f"Goal node:    {args.goal_node} ({nodes[args.goal_node].name})")
    print(f"Path:         {' -> '.join(path)}")
    print(f"Cost:         {total_cost:.2f} m")
    print("Instructions:")
    for step in pretty_steps(path, nodes):
        print(step)


if __name__ == "__main__":
    main()
