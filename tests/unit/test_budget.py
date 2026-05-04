"""Budget — cost cap, iteration cap, circuit breakers."""
from __future__ import annotations

from ralph.budget import BlockReason, Budget, IterationOutcome


def _outcome(i: int, cost: float = 0.1, files: int = 1, error: bool = False) -> IterationOutcome:
    return IterationOutcome(
        iteration=i, cost_usd=cost, duration_s=1.0, files_changed=files, is_error=error
    )


def test_initial_state_allows_run():
    b = Budget(max_iterations=10, max_cost_usd=5.0)
    allowed, reason = b.can_start_next()
    assert allowed
    assert reason == BlockReason.OK


def test_iteration_cap_blocks():
    b = Budget(max_iterations=2, max_cost_usd=10.0)
    b.record(_outcome(1))
    b.record(_outcome(2))
    allowed, reason = b.can_start_next()
    assert not allowed
    assert reason == BlockReason.ITERATIONS_EXHAUSTED


def test_cost_cap_blocks():
    b = Budget(max_iterations=100, max_cost_usd=1.0)
    b.record(_outcome(1, cost=0.6))
    b.record(_outcome(2, cost=0.5))
    allowed, reason = b.can_start_next()
    assert not allowed
    assert reason == BlockReason.COST_EXHAUSTED


def test_no_op_streak_breaks():
    b = Budget(max_iterations=100, max_cost_usd=100.0, no_op_streak_threshold=3)
    for i in range(3):
        b.record(_outcome(i + 1, files=0))
    allowed, reason = b.can_start_next()
    assert not allowed
    assert reason == BlockReason.NO_OP_STREAK


def test_no_op_streak_resets_on_progress():
    b = Budget(max_iterations=100, max_cost_usd=100.0, no_op_streak_threshold=3)
    b.record(_outcome(1, files=0))
    b.record(_outcome(2, files=0))
    b.record(_outcome(3, files=5))  # progress
    b.record(_outcome(4, files=0))
    allowed, reason = b.can_start_next()
    assert allowed
    assert reason == BlockReason.OK


def test_error_streak_breaks():
    b = Budget(max_iterations=100, max_cost_usd=100.0, error_streak_threshold=3)
    for i in range(3):
        b.record(_outcome(i + 1, error=True, files=1))
    allowed, reason = b.can_start_next()
    assert not allowed
    assert reason == BlockReason.ERROR_STREAK


def test_circuit_breaker_can_be_disabled():
    b = Budget(
        max_iterations=100,
        max_cost_usd=100.0,
        no_op_streak_threshold=2,
        circuit_breaker_enabled=False,
    )
    for i in range(5):
        b.record(_outcome(i + 1, files=0))
    allowed, reason = b.can_start_next()
    assert allowed
    assert reason == BlockReason.OK


def test_remaining_helpers():
    b = Budget(max_iterations=10, max_cost_usd=5.0)
    b.record(_outcome(1, cost=2.0))
    assert b.remaining_iterations == 9
    assert abs(b.remaining_cost_usd - 3.0) < 1e-9
