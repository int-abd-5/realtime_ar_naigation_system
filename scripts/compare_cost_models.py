import json
import math
import copy
from pathlib import Path
from statistics import mean
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.navigation.route_planner import load_graph, astar

ROOT = Path(__file__).resolve().parents[1]
NAV_DIR = ROOT / "src" / "navigation"
OUT_DIR = ROOT / "outputs" / "phase4"
OUT_DIR.mkdir(parents=True, exist_ok=True)

def euclidean(a, b):
    return math.hypot(a["x"] - b["x"], a["z"] - b["z"])

def manhattan(a, b):
    return abs(a["x"] - b["x"]) + abs(a["z"] - b["z"])

def load_flat_nodes(nodes_json):
    data = json.loads(nodes_json.read_text(encoding="utf-8"))
    if isinstance(data, list) and len(data) == 1 and isinstance(data[0], dict):
        data = data[0]
    if isinstance(data, dict):
        return data.get("corner_nodes", []) + data.get("door_nodes", [])
    return data

def build_edges(nodes, dist_fn):
    out = []
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            a, b = nodes[i], nodes[j]
            out.append({"from": a["id"], "to": b["id"], "cost": dist_fn(a, b)})
    return out

def run_eval(nodes_file, edges_temp):
    orig_edges = NAV_DIR / "edges.json"
    backup = orig_edges.read_text(encoding="utf-8")
    orig_edges.write_text(json.dumps(edges_temp, indent=2), encoding="utf-8")
    try:
        nodes, adj = load_graph(NAV_DIR)
        tests = json.loads((ROOT / "eval" / "test_cases.json").read_text(encoding="utf-8"))
        costs = []
        success = 0
        for t in tests:
            try:
                _, c = astar(nodes, adj, t["start_node"], t["goal_node"])
                costs.append(c)
                success += 1
            except Exception:
                pass
        return {
            "success_rate": success / len(tests) if tests else 0.0,
            "avg_cost": mean(costs) if costs else None
        }
    finally:
        orig_edges.write_text(backup, encoding="utf-8")

def main():
    nodes = load_flat_nodes(NAV_DIR / "nodes.json")
    m_edges = build_edges(nodes, manhattan)
    e_edges = build_edges(nodes, euclidean)

    man = run_eval(NAV_DIR / "nodes.json", m_edges)
    euc = run_eval(NAV_DIR / "nodes.json", e_edges)

    out = {"manhattan": man, "euclidean": euc}
    (OUT_DIR / "cost_model_comparison.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
