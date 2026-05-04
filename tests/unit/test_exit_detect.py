"""Exit detection — dual-condition signal."""
from __future__ import annotations

from ralph import exit_detect


def test_explicit_signal_alone_is_not_enough_in_strict_mode():
    text = "EXIT_SIGNAL: true"
    assert not exit_detect.is_complete(text, "EXIT_SIGNAL: true")


def test_heuristic_alone_is_not_enough():
    text = "All tasks complete."
    assert not exit_detect.is_complete(text, "EXIT_SIGNAL: true")


def test_both_signals_terminate():
    text = "All tasks complete.\nEXIT_SIGNAL: true"
    assert exit_detect.is_complete(text, "EXIT_SIGNAL: true")


def test_loose_mode_accepts_explicit_alone():
    text = "EXIT_SIGNAL: true"
    assert exit_detect.is_complete(text, "EXIT_SIGNAL: true", require_both=False)


def test_empty_text_returns_false():
    assert not exit_detect.is_complete("", "EXIT_SIGNAL: true")


def test_case_insensitive_heuristic():
    text = "AUDIT COMPLETE.\nEXIT_SIGNAL: true"
    assert exit_detect.is_complete(text, "EXIT_SIGNAL: true")


def test_partial_signal_does_not_match():
    text = "exit_signal: true\naudit complete"  # lowercase signal
    # Explicit signal is case-sensitive (we want the EXACT string).
    assert not exit_detect.is_complete(text, "EXIT_SIGNAL: true")
