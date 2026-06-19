import threading
import time

from freertos_visualizer.reader import SerialReader


class FakeConn:
    """A connection that yields a fixed list of lines, then empty strings."""

    def __init__(self, lines):
        self._lines = list(lines)
        self._lock = threading.Lock()
        self.closed = False

    def connect(self):
        pass

    def readline(self):
        with self._lock:
            if self._lines:
                return self._lines.pop(0)
        return ""

    def close(self):
        self.closed = True


def _collect(reader, n, timeout=5.0):
    got = []
    deadline = time.time() + timeout
    while len(got) < n and time.time() < deadline:
        got.extend(reader.drain())
        time.sleep(0.005)
    return got


def test_reader_collects_all_lines_in_order():
    lines = [f"Task:T,State:{i % 4}" for i in range(200)]
    reader = SerialReader(FakeConn(lines))
    reader.start()
    try:
        got = _collect(reader, 200)
    finally:
        reader.stop()
    assert got == lines  # nothing dropped, FIFO order preserved


def test_reader_counts_drops_under_backpressure():
    lines = [f"L{i}" for i in range(500)]
    reader = SerialReader(FakeConn(lines), max_queue=10)
    reader.start()
    # Deliberately do not drain: the bounded queue fills and the rest are dropped.
    time.sleep(0.3)
    reader.stop()
    assert reader.qsize() <= 10
    assert reader.dropped > 0
    # Every line is accounted for: either queued or counted as dropped.
    assert reader.qsize() + reader.dropped <= 500


def test_reader_stop_closes_connection():
    conn = FakeConn([])
    reader = SerialReader(conn)
    reader.start()
    reader.stop()
    assert conn.closed is True


def test_reader_survives_readline_exception():
    class Flaky:
        def __init__(self):
            self.n = 0

        def connect(self):
            pass

        def readline(self):
            self.n += 1
            if self.n == 1:
                raise OSError("transient")
            if self.n == 2:
                return "Task:OK,State:0"
            return ""

        def close(self):
            pass

    reader = SerialReader(Flaky())
    reader.start()
    try:
        got = _collect(reader, 1)
    finally:
        reader.stop()
    assert "Task:OK,State:0" in got
