from freertos_visualizer.visualize import TaskStateStore


def _seq_clock(values):
    it = iter(values)
    return lambda: next(it)


def test_timestamps_recorded_in_parallel():
    store = TaskStateStore(clock=_seq_clock([1.0, 2.0, 3.0]))
    store.ingest_line("Task:A,State:0")
    store.ingest_line("Task:A,State:1")
    store.ingest_line("Task:B,State:2")

    assert store.task_timestamps["A"] == [1.0, 2.0]
    assert store.task_timestamps["B"] == [3.0]


def test_explicit_timestamp_overrides_clock():
    store = TaskStateStore(clock=_seq_clock([999.0]))
    store.ingest_line("Task:A,State:0", timestamp=42.0)
    assert store.task_timestamps["A"] == [42.0]


def test_device_tick_used_as_timestamp():
    # When the device supplies a tick, it should drive the timeline, not the
    # host read clock.
    store = TaskStateStore(clock=_seq_clock([999.0]))
    store.ingest_line("Task:A,State:0,Tick:7")
    assert store.task_timestamps["A"] == [7.0]


def test_explicit_timestamp_overrides_device_tick():
    store = TaskStateStore(clock=_seq_clock([999.0]))
    store.ingest_line("Task:A,State:0,Tick:7", timestamp=3.0)
    assert store.task_timestamps["A"] == [3.0]


def test_history_pairs_timestamp_and_state():
    store = TaskStateStore(clock=_seq_clock([5.0, 6.0]))
    store.ingest_line("Task:A,State:0")
    store.ingest_line("Task:A,State:2")
    assert store.history("A") == [(5.0, "Running"), (6.0, "Blocked")]


def test_history_unknown_task_is_empty():
    store = TaskStateStore()
    assert store.history("nope") == []


def test_invalid_line_records_no_timestamp():
    store = TaskStateStore(clock=_seq_clock([1.0]))
    assert store.ingest_line("garbage") is None
    assert store.task_timestamps == {}


def test_max_history_trims_states_and_timestamps_together():
    store = TaskStateStore(max_history=2, clock=_seq_clock([1.0, 2.0, 3.0, 4.0]))
    for code in range(4):
        store.ingest_line(f"Task:T,State:{code % 4}")

    assert len(store.task_states["T"]) == 2
    assert len(store.task_timestamps["T"]) == 2
    # Oldest samples dropped; newest two retained.
    assert store.task_timestamps["T"] == [3.0, 4.0]
