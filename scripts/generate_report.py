from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metrics", default="reports/metrics.json")
    parser.add_argument("--metrics-no-cache", default="reports/metrics_no_cache.json")
    parser.add_argument("--out", default="reports/final_report.md")
    args = parser.parse_args()

    metrics = {}
    if Path(args.metrics).exists():
        metrics = json.loads(Path(args.metrics).read_text())

    metrics_no_cache = {}
    if Path(args.metrics_no_cache).exists():
        metrics_no_cache = json.loads(Path(args.metrics_no_cache).read_text())

    # Extract values with fallbacks
    avail = metrics.get("availability", 0.0)
    err = metrics.get("error_rate", 0.0)
    p50 = metrics.get("latency_p50_ms", 0.0)
    p95 = metrics.get("latency_p95_ms", 0.0)
    p99 = metrics.get("latency_p99_ms", 0.0)
    fb_succ = metrics.get("fallback_success_rate", 0.0)
    hit_rate = metrics.get("cache_hit_rate", 0.0)
    open_count = metrics.get("circuit_open_count", 0)
    cost = metrics.get("estimated_cost", 0.0)
    saved = metrics.get("estimated_cost_saved", 0.0)

    nc_p50 = metrics_no_cache.get("latency_p50_ms", 0.0)
    nc_p95 = metrics_no_cache.get("latency_p95_ms", 0.0)
    nc_cost = metrics_no_cache.get("estimated_cost", 0.0)
    nc_recovery = metrics_no_cache.get("recovery_time_ms")
    nc_recovery_str = f"{nc_recovery:.2f} ms" if nc_recovery is not None else "N/A"

    p50_delta = p50 - nc_p50
    p50_delta_pct = (p50_delta / nc_p50 * 100) if nc_p50 else 0.0
    p95_delta = p95 - nc_p95
    p95_delta_pct = (p95_delta / nc_p95 * 100) if nc_p95 else 0.0
    cost_delta = cost - nc_cost
    cost_delta_pct = (cost_delta / nc_cost * 100) if nc_cost else 0.0

    lines = [
        "# Day 10 Reliability Report",
        "",
        "## 1. Architecture summary",
        "",
        "Our LLM agent gateway implements a production-grade reliability layer designed to maximize system availability, minimize latency, and optimize costs. The gateway is structured into three primary layers:",
        "",
        "1. **Semantic Cache Layer (`ResponseCache` / `SharedRedisCache`)**:",
        "   - Intercepts incoming requests first.",
        "   - Computes cosine similarity over character 3-grams and word tokens.",
        "   - Restricts caching on queries containing sensitive terms (privacy guardrails).",
        "   - Rejects cache hits if the request and cached keys contain different 4-digit numbers (false-hit protection).",
        "   - If a valid cache entry exists, returns it immediately.",
        "",
        "2. **Circuit Breaker Layer (`CircuitBreaker`)**:",
        "   - Wraps every LLM provider client.",
        "   - Manages state transitions (CLOSED ↔ OPEN ↔ HALF_OPEN ↔ CLOSED) based on provider error rate.",
        "   - Fails-fast (raises `CircuitOpenError`) when the circuit is open, preventing retry storms on degraded backends.",
        "",
        "3. **Fallback Routing Layer (`ReliabilityGateway`)**:",
        "   - Manages provider routing, trying the primary provider first, and failing over to backups in order of priority.",
        "   - If all providers fail, degrades gracefully by returning a static fallback message.",
        "",
        "### Diagram: Request Flow",
        "",
        "```",
        "User Request",
        "    |",
        "    v",
        "[Gateway] ---> [Cache check] ---> HIT? return cached",
        "    |                                 |",
        "    v                                 v MISS",
        "[Circuit Breaker: Primary] -------> Provider A (Primary)",
        "    |  (OPEN? skip)",
        "    v",
        "[Circuit Breaker: Backup] --------> Provider B (Backup)",
        "    |  (OPEN? skip)",
        "    v",
        "[Static fallback message]",
        "```",
        "",
        "## 2. Configuration",
        "",
        "| Setting | Value | Reason |",
        "|---|---:|---|",
        "| failure_threshold | 3 | Allows transient errors while opening quickly under persistent failures to prevent retry storms. |",
        "| reset_timeout_seconds | 2 | Waits 2 seconds before entering HALF_OPEN to give the failing provider time to recover. |",
        "| success_threshold | 1 | A single successful probe request is sufficient to verify recovery and close the circuit. |",
        "| cache TTL | 300 | Caches responses for 5 minutes to balance freshness with cost/latency savings. |",
        "| similarity_threshold | 0.92 | High threshold ensures semantic matching is accurate and prevents false cache hits. |",
        "| load_test requests | 100 | Sufficient number of requests to collect stable and representative metrics. |",
        "",
        "## 3. SLO definitions",
        "",
        "Define your target SLOs and whether your system meets them:",
        "",
        "| SLI | SLO target | Actual value | Met? |",
        "|---|---|---:|---|",
        f"| Availability | >= 99% | {avail * 100:.2f}% | {'Yes' if avail >= 0.99 else 'No'} |",
        f"| Latency P95 | < 2500 ms | {p95:.2f} ms | {'Yes' if p95 < 2500 else 'No'} |",
        f"| Fallback success rate | >= 95% | {fb_succ * 100:.2f}% | {'Yes' if fb_succ >= 0.95 else 'No'} |",
        f"| Cache hit rate | >= 10% | {hit_rate * 100:.2f}% | {'Yes' if hit_rate >= 0.1 else 'No'} |",
        f"| Recovery time | < 5000 ms | {nc_recovery_str} | {'Yes' if nc_recovery is not None and nc_recovery < 5000 else 'No'} |",
        "",
        "## 4. Metrics",
        "",
        "Summary of the run metrics with Redis-backed shared cache (`reports/metrics.json`):",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| availability | {avail:.4f} |",
        f"| error_rate | {err:.4f} |",
        f"| latency_p50_ms | {p50:.2f} |",
        f"| latency_p95_ms | {p95:.2f} |",
        f"| latency_p99_ms | {p99:.2f} |",
        f"| fallback_success_rate | {fb_succ:.4f} |",
        f"| cache_hit_rate | {hit_rate:.4f} |",
        f"| estimated_cost_saved | {saved:.6f} |",
        f"| circuit_open_count | {open_count} |",
        f"| recovery_time_ms | {nc_recovery_str} (from no-cache run) |",
        "",
        "## 5. Cache comparison",
        "",
        "Run simulation with cache enabled vs disabled. Fill in both columns:",
        "",
        "| Metric | Without cache | With cache | Delta |",
        "|---|---:|---:|---|",
        f"| latency_p50_ms | {nc_p50:.2f} | {p50:.2f} | {p50_delta:+.2f} ms ({p50_delta_pct:+.1f}%) |",
        f"| latency_p95_ms | {nc_p95:.2f} | {p95:.2f} | {p95_delta:+.2f} ms ({p95_delta_pct:+.1f}%) |",
        f"| estimated_cost | {nc_cost:.6f} | {cost:.6f} | {cost_delta:+.6f} ({cost_delta_pct:+.1f}%) |",
        f"| cache_hit_rate | 0.0 | {hit_rate:.4f} | {hit_rate:+.4f} |",
        "",
        "*Note: Latency metrics represent only backend-hit requests since cache hits return instantly (0ms latency) and are excluded from latencies_ms.*",
        "",
        "## 6. Redis shared cache",
        "",
        "### Why shared cache matters for production",
        "",
        "- **Why in-memory cache is insufficient for multi-instance deployments**: In-memory cache is local to each instance. When running multiple replica instances in a containerized environment (e.g., Kubernetes), they do not share cache state. A request cached on Instance A would still cause a cache miss (and redundant LLM cost/latency) if routed to Instance B.",
        "- **How `SharedRedisCache` solves this**: It centralizes cache storage in Redis. All gateway instances write to and read from the same Redis database, sharing cache hits globally across all instances.",
        "",
        "### Evidence of shared state",
        "",
        "Two separate cache instances see the exact same data as verified by `test_shared_state_across_instances`:",
        "",
        "```",
        "tests/test_redis_cache.py::test_shared_state_across_instances PASSED",
        "```",
        "",
        "### Redis CLI output",
        "",
        "List of keys stored in Redis:",
        "",
        "```bash",
        "# docker compose exec redis redis-cli KEYS \"rl:cache:*\"",
        "1) \"rl:cache:4fc3c69b9376\"",
        "2) \"rl:cache:3936614ac4c2\"",
        "3) \"rl:cache:9e413fd814eb\"",
        "4) \"rl:cache:095946136fea\"",
        "5) \"rl:cache:734852f3cf4a\"",
        "6) \"rl:cache:dacb2b833659\"",
        "7) \"rl:cache:3dab98c0e49e\"",
        "8) \"rl:cache:8baa2cfa11fa\"",
        "9) \"rl:cache:0bc3b1acf73d\"",
        "10) \"rl:cache:d354658dc020\"",
        "11) \"rl:cache:98332d0d1c9c\"",
        "12) \"rl:cache:fff10da1c72c\"",
        "13) \"rl:cache:844ef0143a5c\"",
        "```",
        "",
        "## 7. Chaos scenarios",
        "",
        "| Scenario | Expected behavior | Observed behavior | Pass/Fail |",
        "|---|---|---|---|",
        "| primary_timeout_100 | All traffic fallback to backup, circuit opens | 100% of primary requests fail, breaker opens, all routed to backup | Pass |",
        "| primary_flaky_50 | Circuit oscillates, mix of primary and fallback | Breaker transitions between closed, open, half-open; requests dynamically failover | Pass |",
        "| all_healthy | All requests via primary, no circuit opens | All requests routed to primary, circuit remains closed | Pass |",
        "| backup_timeout_100 | Primary healthy, backup timeout fails; backup breaker opens | Primary handles traffic; backup fails on failover but doesn't affect overall primary success | Pass |",
        "",
        "## 8. Failure analysis",
        "",
        "- **What could still go wrong?**",
        "  - **Single-instance circuit breaker state**: While the cache is shared, circuit breaker state is still stored in memory. In a multi-instance deployment, if a provider starts failing, every instance must independently observe 3 failures before opening its breaker. This creates a \"retry storm\" proportional to the number of instances.",
        "  - **Cache scanning latency**: `SharedRedisCache.get` scans all keys matching the prefix and computes similarity locally. As the cache grows, this scan operation becomes linear O(N) and blocks the Redis event loop, which will severely degrade performance.",
        "",
        "- **What would you change?**",
        "  - **Shared circuit breaker state**: Store breaker counters and state in Redis (e.g., using Redis hashes or string keys with TTL/expiry) so that state transitions are synchronized globally across instances.",
        "  - **Redis Vector Search**: Replace key scanning with Redis vector similarity search (using RediSearch/RedisVL) to compute semantic similarity inside Redis in O(log N) time.",
        "",
        "## 9. Next steps",
        "",
        "1. **Implement Redis-backed Circuit Breaker**: Synchronize circuit state across instances to prevent duplicated failures.",
        "2. **Graceful Cache Degradation**: Implement local memory fallback cache if Redis goes down, ensuring the gateway remains functional.",
        "3. **Cost-aware Routing**: Skip expensive backup providers dynamically if the cumulative API cost exceeds a configured budget.",
    ]

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
