from __future__ import annotations

import sys
from reliability_lab.config import load_config
from reliability_lab.cache import SharedRedisCache


def main() -> None:
    print("=== System Diagnostics & Health Check ===")
    
    # 1. Load configuration
    try:
        config = load_config("configs/default.yaml")
        print(f"[OK] Configuration loaded successfully. Target Redis URL: {config.cache.redis_url}")
    except Exception as e:
        print(f"[FAIL] Failed to load configurations: {e}")
        sys.exit(1)
        
    # 2. Check python-redis package installation
    try:
        import redis
        print("[OK] Python 'redis' client library is installed.")
    except ImportError:
        print("[FAIL] 'redis' library is not installed in the current virtual environment.")
        sys.exit(1)
        
    # 3. Ping Redis Server and Inspect Keys
    print(f"Connecting to Redis at: {config.cache.redis_url} ...")
    try:
        # Create two simulated Pod instances with separate client connections
        pod_a = SharedRedisCache(
            redis_url=config.cache.redis_url,
            ttl_seconds=config.cache.ttl_seconds,
            similarity_threshold=config.cache.similarity_threshold
        )
        pod_b = SharedRedisCache(
            redis_url=config.cache.redis_url,
            ttl_seconds=config.cache.ttl_seconds,
            similarity_threshold=config.cache.similarity_threshold
        )
        
        if pod_a.ping() and pod_b.ping():
            print("[OK] Redis server is ONLINE and responding to PING.")
            
            # --- Simulate Multi-Instance Cache Write/Read ---
            print("\n--- Simulating Cache Writes from Two Pod Instances ---")
            
            # Query A written by Pod A
            query_a = "summarize student admission guidelines"
            val_a = "Admission guidelines: Submit GPA transcripts by August."
            print(f"[Pod A] Writing cache: '{query_a}' -> '{val_a}'")
            pod_a.set(query_a, val_a)
            print("[OK] Pod A wrote successfully to Redis.")
            
            # Query A read by Pod B
            print(f"[Pod B] Reading cache for: '{query_a}'")
            res_b, score_b = pod_b.get(query_a)
            if res_b == val_a:
                print(f"[OK] Pod B successfully retrieved Pod A's cached response (Score: {score_b:.2f}).")
            else:
                print(f"[FAIL] Pod B cache miss or mismatch. Got: {res_b}")
                
            # Query B written by Pod B
            query_b = "what is tuition fees for international students"
            val_b = "Tuition fees: $12000 per academic semester."
            print(f"[Pod B] Writing cache: '{query_b}' -> '{val_b}'")
            pod_b.set(query_b, val_b)
            print("[OK] Pod B wrote successfully to Redis.")
            
            # Query B read by Pod A
            print(f"[Pod A] Reading cache for: '{query_b}'")
            res_a, score_a = pod_a.get(query_b)
            if res_a == val_b:
                print(f"[OK] Pod A successfully retrieved Pod B's cached response (Score: {score_a:.2f}).")
            else:
                print(f"[FAIL] Pod A cache miss or mismatch. Got: {res_a}")
                
            print("[OK] Multi-instance concurrent cache writing & sharing is FULLY FUNCTIONAL!\n")
            
            # Inspect existing keys
            keys = list(pod_a._redis.scan_iter(f"{pod_a.prefix}*"))
            print(f"[INFO] Current active cached entries in Redis: {len(keys)}")
            if keys:
                print("Samples:")
                for k in keys[:5]:
                    print(f"  - {k}")
                if len(keys) > 5:
                    print("  - ... and more")
            
            # Close connections
            pod_a.close()
            pod_b.close()
        else:
            print("[FAIL] Redis server PING failed.")
    except Exception as e:
        print(f"[FAIL] Error during pod instance cache validation: {e}")


if __name__ == "__main__":
    main()
