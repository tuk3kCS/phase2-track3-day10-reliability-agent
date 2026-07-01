from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from reliability_lab.chaos import load_queries, run_simulation
from reliability_lab.config import load_config


def run_comparison(
    config_path: str,
    out_path_cache: str,
    queries_path: str = "data/sample_queries.jsonl",
    requests_override: int | None = None,
    concurrency_override: int | None = None,
    similarity_override: float | None = None,
) -> None:
    """Run simulation with and without cache, print and save exact metrics from reference."""
    queries = load_queries(queries_path)
    
    # 1. Run with cache enabled
    config = load_config(config_path)
    if requests_override is not None:
        config.load_test.requests = requests_override
    if concurrency_override is not None:
        config.load_test.concurrency = concurrency_override
    if similarity_override is not None:
        config.cache.similarity_threshold = similarity_override
        
    metrics_cache = run_simulation(config, queries)
    
    # 2. Run with cache disabled
    config_no_cache = copy.deepcopy(config)
    config_no_cache.cache.enabled = False
    metrics_no_cache = run_simulation(config_no_cache, queries)
    
    # Write files
    metrics_cache.write_json(out_path_cache)
    print(f"wrote {out_path_cache}")
    
    csv_path = str(Path(out_path_cache).with_suffix(".csv"))
    metrics_cache.write_csv(csv_path)
    print(f"wrote {csv_path}")
    
    # Write cache comparison
    c_rep = metrics_cache.to_report_dict()
    nc_rep = metrics_no_cache.to_report_dict()
    
    comparison_data = {
        "without_cache": {
            "latency_p50_ms": nc_rep["latency_p50_ms"],
            "latency_p95_ms": nc_rep["latency_p95_ms"],
            "estimated_cost": nc_rep["estimated_cost"]
        },
        "with_cache": {
            "latency_p50_ms": c_rep["latency_p50_ms"],
            "latency_p95_ms": c_rep["latency_p95_ms"],
            "estimated_cost": c_rep["estimated_cost"]
        }
    }
    
    comp_json_path = str(Path(out_path_cache).with_name("cache_comparison.json"))
    Path(comp_json_path).write_text(json.dumps(comparison_data, indent=2), encoding="utf-8")
    print(f"wrote {comp_json_path}")
    
    # Print Metrics Summary
    print("\n=== Metrics Summary ===")
    print(f"total_requests: {c_rep['total_requests']}")
    print(f"availability: {c_rep['availability']}")
    print(f"error_rate: {c_rep['error_rate']}")
    print(f"latency_p50_ms: {c_rep['latency_p50_ms']}")
    print(f"latency_p95_ms: {c_rep['latency_p95_ms']}")
    print(f"latency_p99_ms: {c_rep['latency_p99_ms']}")
    print(f"fallback_success_rate: {c_rep['fallback_success_rate']}")
    print(f"cache_hit_rate: {c_rep['cache_hit_rate']}")
    print(f"circuit_open_count: {c_rep['circuit_open_count']}")
    
    rec_time = c_rep["recovery_time_ms"]
    rec_time_str = f"{round(rec_time, 2)}" if rec_time is not None else "0.0"
    print(f"recovery_time_ms: {rec_time_str}")
    print(f"estimated_cost: {c_rep['estimated_cost']}")
    print(f"estimated_cost_saved: {c_rep['estimated_cost_saved']}")
    
    # Print Scenarios
    print("\n=== Scenarios ===")
    scenarios = c_rep.get("scenarios", {})
    if isinstance(scenarios, dict):
        for name, status in scenarios.items():
            print(f"{name}: {status}")
            
    # Print Cache Comparison
    print("\n=== Cache Comparison ===")
    print("without_cache:")
    print(f"  latency_p50_ms: {nc_rep['latency_p50_ms']}")
    print(f"  latency_p95_ms: {nc_rep['latency_p95_ms']}")
    print(f"  estimated_cost: {nc_rep['estimated_cost']}")
    print("with_cache:")
    print(f"  latency_p50_ms: {c_rep['latency_p50_ms']}")
    print(f"  latency_p95_ms: {c_rep['latency_p95_ms']}")
    print(f"  estimated_cost: {c_rep['estimated_cost']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Gateway Reliability Chaos Simulations")
    parser.add_argument("--config", default="configs/default.yaml", help="Path to default config file")
    parser.add_argument("--out", default="reports/metrics.json", help="Path to save main output metrics")
    parser.add_argument("--queries", default="data/sample_queries.jsonl", help="Path to sample queries dataset")
    parser.add_argument("--requests", type=int, default=None, help="Override load test request count")
    parser.add_argument("--concurrency", type=int, default=None, help="Override load test concurrency level")
    parser.add_argument("--similarity", type=float, default=None, help="Override cache similarity threshold")
    parser.add_argument("--compare", action="store_true", default=True, help="Perform Cache vs No-Cache comparison run")
    args = parser.parse_args()
    
    if args.compare:
        run_comparison(
            args.config,
            args.out,
            queries_path=args.queries,
            requests_override=args.requests,
            concurrency_override=args.concurrency,
            similarity_override=args.similarity,
        )
    else:
        config = load_config(args.config)
        if args.requests is not None:
            config.load_test.requests = args.requests
        if args.concurrency is not None:
            config.load_test.concurrency = args.concurrency
        if args.similarity is not None:
            config.cache.similarity_threshold = args.similarity
            
        metrics = run_simulation(config, load_queries(args.queries))
        metrics.write_json(args.out)
        print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
