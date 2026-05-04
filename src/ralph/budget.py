"""Budget — cost cap, iteration cap, and circuit breaker.

`Budget` is the SINGLE source of truth for whether the next iteration may proceed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class BlockReason(StrEnum):
    OK = "ok"
    ITERATIONS_EXHAUSTED = "iterations_exhausted"
    COST_EXHAUSTED = "cost_exhausted"
    NO_OP_STREAK = "no_op_streak"
    ERROR_STREAK = "error_streak"


@dataclass
class IterationOutcome:
    """Minimal record of one iteration; fed into Budget for circuit-breaker logic."""

    iteration: int
    cost_usd: float
    duration_s: float
    files_changed: int
    is_error: bool
    summary: str = ""


@dataclass
class Budget:
    """Tracks cumulative cost + circuit-breaker streaks across iterations."""

    max_iterations: int
    max_cost_usd: float
    no_op_streak_threshold: int = 3
    error_streak_threshold: int = 5
    circuit_breaker_enabled: bool = True

    iterations_completed: int = 0
    total_cost_usd: float = 0.0
    history: list[IterationOutcome] = field(default_factory=list)

    @property
    def remaining_cost_usd(self) -> float:
        return max(0.0, self.max_cost_usd - self.total_cost_usd)

    @property
    def remaining_iterations(self) -> int:
        return max(0, self.max_iterations - self.iterations_completed)

    def can_start_next(self) -> tuple[bool, BlockReason]:
        """Decide whether to start iteration N+1 BEFORE invoking claude.

        Returns (allowed, reason). reason is OK iff allowed is True.
        """
        if self.iterations_completed >= self.max_iterations:
            return False, BlockReason.ITERATIONS_EXHAUSTED
        if self.total_cost_usd >= self.max_cost_usd:
            return False, BlockReason.COST_EXHAUSTED

        if self.circuit_breaker_enabled:
            if self._tail_streak(lambda o: o.files_changed == 0) >= self.no_op_streak_threshold:
                return False, BlockReason.NO_OP_STREAK
            if self._tail_streak(lambda o: o.is_error) >= self.error_streak_threshold:
                return False, BlockReason.ERROR_STREAK

        return True, BlockReason.OK

    def record(self, outcome: IterationOutcome) -> None:
        self.iterations_completed += 1
        self.total_cost_usd += outcome.cost_usd
        self.history.append(outcome)

    def _tail_streak(self, predicate) -> int:
        """Count how many consecutive recent outcomes match predicate."""
        n = 0
        for o in reversed(self.history):
            if predicate(o):
                n += 1
            else:
                break
        return n
