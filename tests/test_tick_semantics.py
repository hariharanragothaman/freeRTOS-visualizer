"""Device-tick semantics: units, wraparound, clock-domain locking, metadata.

These guard the round-2 review findings:
  #44 the timeline must not call raw ticks "seconds"
  #45 a wrapping tick counter must not produce a backwards timeline
  #46 device ticks and host wall-clock must never interleave in one history
"""

from freertos_visualizer.visualize import TaskStateStore, parse_meta_line


def _seq_clock(values):
    it = iter(values)
    return lambda: next(it)


# --- #44: tick rate / units -------------------------------------------------

def test_meta_line_parsing():
    assert parse_meta_line("TickRate:1000") == {"tick_rate_hz": 1000}
    assert parse_meta_line("TickBits:16") == {"tick_bits": 16}
    assert parse_meta_line("TickRate:0") is None      # nonsensical
    assert parse_meta_line("Task:A,State:0,Tick:5") is None  # not metadata


def test_tickrate_line_sets_rate_and_is_not_a_sample():
    store = TaskStateStore()
    assert store.ingest_line("TickRate:1000") is None
    assert store.tick_rate_hz == 1000
    assert store.task_states == {}  # metadata is not a task sample


def test_axis_is_seconds_only_when_rate_known():
    # Device ticks with no announced rate: do NOT claim seconds.
    ticks_only = TaskStateStore()
    ticks_only.ingest_line("Task:A,State:0,Tick:0")
    assert ticks_only.clock_domain == "device"
    assert ticks_only.time_axis_label == "Device ticks"
    assert ticks_only.time_scale == 1.0

    # Once the device announces TickRate, convert ticks -> seconds.
    with_rate = TaskStateStore()
    with_rate.ingest_line("TickRate:1000")
    with_rate.ingest_line("Task:A,State:0,Tick:0")
    with_rate.ingest_line("Task:A,State:1,Tick:3751")
    assert with_rate.time_axis_label == "Time (s)"
    assert with_rate.time_scale == 1.0 / 1000
    # 3751 ticks at 1 kHz is 3.751 s, not 3751 s.
    stamps = with_rate.task_timestamps["A"]
    assert stamps == [0.0, 3751.0]
    assert stamps[-1] * with_rate.time_scale == 3.751


def test_host_domain_axis_is_seconds():
    store = TaskStateStore(clock=_seq_clock([10.0, 11.0]))
    store.ingest_line("Task:A,State:0")
    assert store.clock_domain == "host"
    assert store.time_axis_label == "Time (s)"
    assert store.time_scale == 1.0


# --- #45: wraparound --------------------------------------------------------

def test_tick_wraparound_is_unwrapped_monotonic():
    # 8-bit counter (modulus 256) so we can run past the boundary cheaply.
    store = TaskStateStore(tick_bits=8)
    raw = [250, 255, 2, 10, 255, 0, 5]  # wraps twice
    for i, t in enumerate(raw):
        store.ingest_line(f"Task:A,State:{i % 4},Tick:{t}")
    stamps = store.task_timestamps["A"]
    # Strictly non-decreasing after unwrapping.
    assert stamps == sorted(stamps)
    # Two wraps => +512 total offset; last raw 5 -> 5 + 512 = 517.
    assert stamps == [250.0, 255.0, 258.0, 266.0, 511.0, 512.0, 517.0]


def test_wraparound_keeps_timeline_segments_forward():
    from freertos_visualizer.timeline import compute_segments

    store = TaskStateStore(tick_bits=8)
    # Same state across a wrap: one continuous forward span, never end < start.
    for t in [250, 255, 1, 8]:
        store.ingest_line(f"Task:A,State:0,Tick:{t}")
    segments = compute_segments(store)["A"]
    for start, end, _state in segments:
        assert end >= start


def test_tickbits_meta_sets_wrap_modulus():
    store = TaskStateStore()  # default 32-bit
    store.ingest_line("TickBits:16")
    assert store.tick_bits == 16
    # 16-bit modulus now: 65535 -> 0 is a wrap, not a 65535-unit jump back.
    store.ingest_line("Task:A,State:0,Tick:65535")
    store.ingest_line("Task:A,State:0,Tick:0")
    stamps = store.task_timestamps["A"]
    assert stamps == [65535.0, 65536.0]


# --- #46: clock-domain locking ---------------------------------------------

def test_device_then_host_line_is_rejected():
    store = TaskStateStore(clock=_seq_clock([1.7e9]))
    assert store.ingest_line("Task:A,State:0,Tick:5") is not None
    # A later line missing Tick would inject host epoch seconds (~1.7e9) next to
    # ticks (~1e3): reject it instead of corrupting the history.
    assert store.ingest_line("Task:A,State:1") is None
    assert store.task_timestamps["A"] == [5.0]


def test_host_then_device_line_is_rejected():
    store = TaskStateStore(clock=_seq_clock([10.0, 11.0]))
    assert store.ingest_line("Task:A,State:0") is not None
    assert store.ingest_line("Task:A,State:1,Tick:5") is None
    assert store.task_timestamps["A"] == [10.0]
