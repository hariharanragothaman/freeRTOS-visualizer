from freertos_visualizer.stats import compute_summary, format_summary
from freertos_visualizer.visualize import TaskStateStore


def _store_with(samples):
    """Build a store from a list of (timestamp, line) tuples."""
    store = TaskStateStore()
    for ts, line in samples:
        store.ingest_line(line, timestamp=ts)
    return store


def test_sample_and_transition_counts():
    store = _store_with([
        (0.0, "Task:A,State:0"),  # Running
        (1.0, "Task:A,State:0"),  # Running (no transition)
        (2.0, "Task:A,State:1"),  # Ready  (transition)
        (3.0, "Task:A,State:2"),  # Blocked(transition)
    ])
    summary = compute_summary(store)["A"]
    assert summary["samples"] == 4
    assert summary["transitions"] == 2


def test_state_count_distribution():
    store = _store_with([
        (0.0, "Task:A,State:0"),
        (1.0, "Task:A,State:0"),
        (2.0, "Task:A,State:1"),
        (3.0, "Task:A,State:1"),
    ])
    summary = compute_summary(store)["A"]
    assert summary["state_counts"]["Running"] == 2
    assert summary["state_counts"]["Ready"] == 2
    assert summary["state_pct"]["Running"] == 50.0
    assert summary["state_pct"]["Ready"] == 50.0


def test_time_in_state_percentages():
    # Running for 3s (0->3), then Blocked for 1s (3->4). Final sample uncounted.
    store = _store_with([
        (0.0, "Task:A,State:0"),  # Running
        (3.0, "Task:A,State:2"),  # Blocked
        (4.0, "Task:A,State:2"),  # Blocked (final, no following gap)
    ])
    summary = compute_summary(store)["A"]
    assert summary["total_time"] == 4.0
    assert summary["time_in_state"]["Running"] == 3.0
    assert summary["time_in_state"]["Blocked"] == 1.0
    assert summary["time_pct"]["Running"] == 75.0
    assert summary["time_pct"]["Blocked"] == 25.0


def test_single_sample_has_no_time():
    store = _store_with([(0.0, "Task:A,State:0")])
    summary = compute_summary(store)["A"]
    assert summary["samples"] == 1
    assert summary["transitions"] == 0
    assert summary["total_time"] == 0.0
    assert all(v == 0.0 for v in summary["time_pct"].values())


def test_multiple_tasks_summarized_independently():
    store = _store_with([
        (0.0, "Task:A,State:0"),
        (1.0, "Task:B,State:1"),
        (2.0, "Task:A,State:1"),
    ])
    summary = compute_summary(store)
    assert set(summary) == {"A", "B"}
    assert summary["A"]["samples"] == 2
    assert summary["B"]["samples"] == 1


def test_store_summary_delegates():
    store = _store_with([(0.0, "Task:A,State:0"), (1.0, "Task:A,State:1")])
    assert store.summary() == compute_summary(store)


def test_format_summary_empty():
    assert format_summary({}) == "No task data captured."


def test_format_summary_renders_tasks():
    store = _store_with([
        (0.0, "Task:Worker,State:0"),
        (1.0, "Task:Worker,State:1"),
    ])
    text = format_summary(compute_summary(store))
    assert "Worker" in text
    assert "Samples" in text
    assert "Transitions" in text
