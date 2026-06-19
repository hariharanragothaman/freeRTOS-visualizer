from freertos_visualizer.timeline import (
    STATE_COLORS,
    _segments_for,
    compute_segments,
    state_color,
)
from freertos_visualizer.visualize import TaskStateStore


def _store_with(samples):
    store = TaskStateStore()
    for ts, line in samples:
        store.ingest_line(line, timestamp=ts)
    return store


def test_empty_store_has_no_segments():
    assert compute_segments(TaskStateStore()) == {}


def test_segments_for_empty_inputs():
    assert _segments_for([], []) == []
    assert _segments_for([1.0], []) == []


def test_single_sample_is_zero_width_span():
    store = _store_with([(5.0, "Task:A,State:0")])
    assert compute_segments(store)["A"] == [(5.0, 5.0, "Running")]


def test_collapses_consecutive_identical_states():
    store = _store_with([
        (0.0, "Task:A,State:0"),  # Running
        (1.0, "Task:A,State:0"),  # Running (collapsed)
        (2.0, "Task:A,State:1"),  # Ready
    ])
    # Running spans 0->2 (until Ready begins); final Ready is zero-width at 2.
    assert compute_segments(store)["A"] == [
        (0.0, 2.0, "Running"),
        (2.0, 2.0, "Ready"),
    ]


def test_multiple_transitions():
    store = _store_with([
        (0.0, "Task:A,State:0"),  # Running
        (1.0, "Task:A,State:2"),  # Blocked
        (4.0, "Task:A,State:0"),  # Running
        (5.0, "Task:A,State:0"),  # Running (collapsed)
    ])
    assert compute_segments(store)["A"] == [
        (0.0, 1.0, "Running"),
        (1.0, 4.0, "Blocked"),
        (4.0, 5.0, "Running"),
    ]


def test_segments_per_task():
    store = _store_with([
        (0.0, "Task:A,State:0"),
        (1.0, "Task:B,State:1"),
        (2.0, "Task:A,State:1"),
    ])
    segments = compute_segments(store)
    assert set(segments) == {"A", "B"}
    assert segments["A"] == [(0.0, 2.0, "Running"), (2.0, 2.0, "Ready")]
    assert segments["B"] == [(1.0, 1.0, "Ready")]


def test_unknown_state_color_fallback():
    assert state_color("Running") == STATE_COLORS["Running"]
    assert state_color("definitely-not-a-state") == STATE_COLORS["Unknown"]


def test_spans_have_nonnegative_width():
    store = _store_with([
        (0.0, "Task:A,State:0"),
        (3.0, "Task:A,State:1"),
        (3.0, "Task:A,State:2"),  # same timestamp -> zero width, not negative
    ])
    for start, end, _state in compute_segments(store)["A"]:
        assert end >= start
