from __future__ import annotations

import time
from hypothesis import given, strategies as st
from reliability_lab.circuit_breaker import CircuitBreaker, CircuitState


@given(
    actions=st.lists(st.sampled_from(["success", "failure", "wait"]), min_size=1, max_size=50),
    failure_threshold=st.integers(min_value=1, max_value=5),
    success_threshold=st.integers(min_value=1, max_value=5),
)
def test_circuit_breaker_properties(actions: list[str], failure_threshold: int, success_threshold: int) -> None:
    cb = CircuitBreaker(
        name="test_fuzz",
        failure_threshold=failure_threshold,
        reset_timeout_seconds=0.01,
        success_threshold=success_threshold,
    )
    
    for act in actions:
        if act == "wait":
            time.sleep(0.015)
            cb.allow_request()
            continue
            
        allowed = cb.allow_request()
        if allowed:
            if act == "success":
                cb.record_success()
            else:
                cb.record_failure()
                
        # Invariant 1: Counts are non-negative
        assert cb.failure_count >= 0
        assert cb.success_count >= 0
        
        # Invariant 2: State belongs to CircuitState
        assert cb.state in (CircuitState.CLOSED, CircuitState.OPEN, CircuitState.HALF_OPEN)
        
        # Invariant 3: In HALF_OPEN state, success_count is at most success_threshold
        if cb.state == CircuitState.HALF_OPEN:
            assert cb.success_count <= cb.success_threshold
            
        # Invariant 4: In OPEN state, success_count is 0
        if cb.state == CircuitState.OPEN:
            assert cb.success_count == 0
