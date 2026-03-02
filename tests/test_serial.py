from freertos_visualizer.visualize import (
    TaskStateStore,
    SerialConnection,
    parse_serial_line,
    STATE_DICT,
)


# ---------------------------------------------------------------------------
# parse_serial_line
# ---------------------------------------------------------------------------


def test_parse_valid_running():
    assert parse_serial_line("Task:Task1,State:0") == ("Task1", "Running")


def test_parse_valid_ready():
    assert parse_serial_line("Task:LED,State:1") == ("LED", "Ready")


def test_parse_valid_blocked():
    assert parse_serial_line("Task:Sensor,State:2") == ("Sensor", "Blocked")


def test_parse_valid_suspended():
    assert parse_serial_line("Task:Motor,State:3") == ("Motor", "Suspended")


def test_parse_unknown_state_code():
    assert parse_serial_line("Task:Task1,State:99") == ("Task1", "Unknown")


def test_parse_invalid_line_returns_none():
    assert parse_serial_line("Invalid line") is None


def test_parse_empty_string():
    assert parse_serial_line("") is None


def test_parse_partial_match():
    assert parse_serial_line("Task:,State:0") is None  # empty task name (\S+ won't match)


def test_parse_embedded_in_noise():
    assert parse_serial_line("garbage Task:X,State:1 more") == ("X", "Ready")


# ---------------------------------------------------------------------------
# TaskStateStore
# ---------------------------------------------------------------------------


def test_store_tracks_history():
    store = TaskStateStore()
    store.ingest_line("Task:Task1,State:0")
    store.ingest_line("Task:Task1,State:2")
    store.ingest_line("Task:Task2,State:1")

    assert store.task_states["Task1"] == ["Running", "Blocked"]
    assert store.task_states["Task2"] == ["Ready"]


def test_store_ignores_invalid_lines():
    store = TaskStateStore()
    result = store.ingest_line("not a task line")
    assert result is None
    assert store.task_states == {}


def test_store_max_history():
    store = TaskStateStore(max_history=3)
    for i in range(5):
        store.ingest_line(f"Task:T,State:{i % 4}")

    assert len(store.task_states["T"]) == 3


def test_export_csv(tmp_path):
    store = TaskStateStore()
    store.ingest_line("Task:Task1,State:0")
    store.ingest_line("Task:Task1,State:1")

    output_file = tmp_path / "task_history.csv"
    store.export_csv(str(output_file))

    contents = output_file.read_text(encoding="utf-8")
    lines = [line.strip() for line in contents.splitlines() if line.strip()]
    assert lines[0] == "task_name,sample_index,state"
    assert "Task1,0,Running" in lines
    assert "Task1,1,Ready" in lines


def test_export_csv_empty(tmp_path):
    store = TaskStateStore()
    output_file = tmp_path / "empty.csv"
    store.export_csv(str(output_file))

    contents = output_file.read_text(encoding="utf-8")
    lines = [line.strip() for line in contents.splitlines() if line.strip()]
    assert lines == ["task_name,sample_index,state"]


# ---------------------------------------------------------------------------
# SerialConnection  (with mock serial ports)
# ---------------------------------------------------------------------------


class FakePort:
    """Minimal stand-in for a pyserial port object."""

    def __init__(self, lines=None, fail_after=None):
        self._lines = list(lines or [])
        self._index = 0
        self._fail_after = fail_after
        self._read_count = 0

    def readline(self):
        if self._fail_after is not None and self._read_count >= self._fail_after:
            raise OSError("simulated disconnect")
        self._read_count += 1
        if self._index < len(self._lines):
            line = self._lines[self._index]
            self._index += 1
            return line.encode("utf-8")
        return b""

    def close(self):
        pass


class FakeClock:
    """Deterministic clock for testing backoff timing."""

    def __init__(self, start=0.0):
        self._now = start

    def time(self):
        return self._now

    def advance(self, seconds):
        self._now += seconds


def _make_conn(fake_port, clock=None):
    """Build a SerialConnection pre-wired to a FakePort, bypassing real serial."""
    clock = clock or FakeClock()
    conn = SerialConnection(url="fake://", _clock=clock)
    conn._port = fake_port
    conn.connected = True
    return conn, clock


def test_readline_returns_decoded_line():
    port = FakePort(lines=["Task:T1,State:0\n"])
    conn, _ = _make_conn(port)
    assert conn.readline() == "Task:T1,State:0"


def test_readline_returns_empty_on_no_data():
    port = FakePort(lines=[])
    conn, _ = _make_conn(port)
    assert conn.readline() == ""


def test_readline_marks_disconnected_on_error():
    port = FakePort(lines=[], fail_after=0)
    conn, _ = _make_conn(port)
    result = conn.readline()
    assert result == ""
    assert conn.connected is False


def test_backoff_prevents_immediate_reconnect():
    clock = FakeClock(start=100.0)
    conn = SerialConnection(url="fake://", _clock=clock)
    conn.connected = False
    conn._last_attempt = 100.0

    result = conn.readline()
    assert result == ""


def test_backoff_allows_reconnect_after_delay():
    clock = FakeClock(start=100.0)
    conn = SerialConnection(url="fake://", _clock=clock)
    conn.connected = False
    conn._last_attempt = 98.0  # 2 seconds ago, > initial 1s backoff

    # _open will raise because url is fake, but it should *try*
    result = conn.readline()
    assert result == ""
    # backoff should have doubled since _open failed
    assert conn._backoff > 1.0


def test_close_resets_state():
    port = FakePort()
    conn, _ = _make_conn(port)
    assert conn.connected is True
    conn.close()
    assert conn.connected is False
    assert conn._port is None


# ---------------------------------------------------------------------------
# Integration-style: store fed through SerialConnection
# ---------------------------------------------------------------------------


def test_serial_to_store_pipeline():
    port = FakePort(lines=[
        "Task:Task1,State:0\n",
        "Task:Task1,State:2\n",
        "noise\n",
        "Task:Task2,State:1\n",
    ])
    conn, _ = _make_conn(port)
    store = TaskStateStore()

    for _ in range(4):
        line = conn.readline()
        if line:
            store.ingest_line(line)

    assert store.task_states["Task1"] == ["Running", "Blocked"]
    assert store.task_states["Task2"] == ["Ready"]


def test_malformed_binary_input():
    """Non-UTF-8 bytes should be replaced, not crash."""
    port = FakePort(lines=[])
    conn, _ = _make_conn(port)
    conn._port = type("Fake", (), {
        "readline": lambda self: b"\xff\xfeTask:X,State:1\n",
        "close": lambda self: None,
    })()
    line = conn.readline()
    assert "Task:X,State:1" in line
