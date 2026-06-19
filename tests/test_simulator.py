import re

import pytest

from freertos_visualizer.simulator import DEFAULT_TASKS, TaskSimulator
from freertos_visualizer.visualize import STATE_DICT, TaskStateStore, parse_serial_line

LINE_RE = re.compile(r"^Task:(\S+),State:(\d+)$")


def test_output_matches_protocol():
    sim = TaskSimulator(seed=1)
    for _ in range(50):
        line = sim.next_line()
        match = LINE_RE.match(line)
        assert match, f"line did not match protocol: {line!r}"
        # State code must be a known code, and the line must parse cleanly.
        assert match.group(2) in STATE_DICT
        assert parse_serial_line(line) is not None


def test_only_known_tasks_emitted():
    tasks = ("Alpha", "Beta", "Gamma")
    sim = TaskSimulator(tasks=tasks, seed=3)
    seen = {parse_serial_line(sim.next_line())[0] for _ in range(60)}
    assert seen == set(tasks)


def test_deterministic_with_same_seed():
    a = TaskSimulator(seed=42)
    b = TaskSimulator(seed=42)
    assert [a.next_line() for _ in range(100)] == [b.next_line() for _ in range(100)]


def test_different_seeds_differ():
    a = [TaskSimulator(seed=1).next_line() for _ in range(100)]
    b = [TaskSimulator(seed=2).next_line() for _ in range(100)]
    assert a != b


def test_round_robins_tasks_in_order():
    sim = TaskSimulator(tasks=("A", "B", "C"), seed=0)
    names = [parse_serial_line(sim.next_line())[0] for _ in range(6)]
    assert names == ["A", "B", "C", "A", "B", "C"]


def test_empty_tasks_raises():
    with pytest.raises(ValueError):
        TaskSimulator(tasks=[])


def test_stream_yields_requested_count():
    sim = TaskSimulator(seed=7)
    lines = list(sim.stream(25))
    assert len(lines) == 25


def test_readline_is_serialconnection_compatible():
    sim = TaskSimulator(seed=5)
    assert sim.connected is False
    line = sim.readline()  # auto-connects
    assert sim.connected is True
    assert LINE_RE.match(line)
    sim.close()
    assert sim.connected is False


def test_connect_then_close():
    sim = TaskSimulator(seed=0)
    sim.connect()
    assert sim.connected is True
    sim.close()
    assert sim.connected is False


def test_feeds_store_end_to_end():
    sim = TaskSimulator(seed=9)
    store = TaskStateStore()
    for line in sim.stream(100):
        store.ingest_line(line)
    # Every default task should have accumulated history.
    assert set(store.task_states.keys()) == set(DEFAULT_TASKS)
    assert all(len(h) > 0 for h in store.task_states.values())


def test_emit_tick_appends_monotonic_tick():
    sim = TaskSimulator(seed=1, emit_tick=True)
    first = parse_serial_line(sim.next_line())
    second = parse_serial_line(sim.next_line())
    assert first[2] == 0
    assert second[2] == 1


def test_rate_hz_paces_readline():
    slept = []
    sim = TaskSimulator(seed=2, rate_hz=100.0, _sleep=slept.append)
    sim.readline()
    assert slept == [pytest.approx(0.01)]
