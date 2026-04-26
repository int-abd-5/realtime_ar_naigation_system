import json
import time
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

def main():
    nodes, adj = load_graph(NAV_DIR)
    tests = json.loads((ROOT / "eval" / "test_cases.json").read_text(encoding="utf-8"))

    results = []
    success = 0
    latencies_ms = []
    costs = []

    for t in tests:
        start = t["start_node"]
        goal = t["goal_node"]
        rec = {"id": t["id"], "start": start, "goal": goal, "ok": False}

        t0 = time.perf_counter()
        try:
            path, cost = astar(nodes, adj, start, goal)
            dt = (time.perf_counter() - t0) * 1000.0
            rec.update({
                "ok": True,
                "path": path,
                "cost": cost,
                "latency_ms": dt
            })
            success += 1
            latencies_ms.append(dt)
            costs.append(cost)
        except Exception as e:
            dt = (time.perf_counter() - t0) * 1000.0
            rec.update({
                "ok": False,
                "error": str(e),
                "latency_ms": dt
            })

        results.append(rec)

    summary = {
        "total_tests": len(tests),
        "success_count": success,
        "success_rate": (success / len(tests)) if tests else 0.0,
        "avg_latency_ms": mean(latencies_ms) if latencies_ms else None,
        "p95_latency_ms": sorted(latencies_ms)[int(0.95 * (len(latencies_ms)-1))] if latencies_ms else None,
        "avg_cost": mean(costs) if costs else None,
        "failed_count": len(tests) - success
    }

    (OUT_DIR / "phase4_eval_results.json").write_text(
        json.dumps({"summary": summary, "cases": results}, indent=2),
        encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()
