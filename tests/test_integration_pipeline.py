"""End-to-end ingest test: burst → SerialConnection → SerialReader → store.

This is the test the external review asked for — feed a burst through the *real*
ingest path and assert none are dropped — exercising the threaded reader, the
queue, line reassembly, and the store together (the parts the unit tests and the
GUI's ``pragma: no cover`` don't cover end to end).

We deliberately deliver the byte stream in adversarial, randomly-sized chunks
that split lines mid-field and coalesce several lines per read. That is a
*stronger* drop/corruption test than a clean TCP loopback (whose framing depends
on third-party pyserial socket timing and is therefore non-deterministic in CI):
if the reader drained one line per repaint (the original bug), or if framing
reassembly dropped/merged a line, this fails deterministically.
"""

import random
import threading
import time

from freertos_visualizer.reader import SerialReader
from freertos_visualizer.visualize import SerialConnection, TaskStateStore

BURST = 2000


class ChunkedPort:
    """A pyserial-like port that serves ``data`` in pre-planned chunk sizes.

    ``readline()`` returns the next chunk of bytes (not necessarily a whole
    line), mimicking a real UART where a read can return a partial line or
    several lines at once. Returns ``b""`` once the stream is exhausted.
    """

    def __init__(self, data, chunk_sizes):
        self._data = data
        self._pos = 0
        self._sizes = chunk_sizes
        self._i = 0
        self._lock = threading.Lock()

    def readline(self):
        with self._lock:
            if self._pos >= len(self._data):
                return b""
            size = self._sizes[self._i % len(self._sizes)]
            self._i += 1
            chunk = self._data[self._pos:self._pos + size]
            self._pos += size
            return chunk

    def close(self):
        pass


def test_burst_through_pipeline_has_no_dropped_lines():
    data = b"".join(
        f"Task:T{i % 4},State:{i % 4},Tick:{i}\n".encode("utf-8") for i in range(BURST)
    )
    rng = random.Random(1234)
    # Mix tiny (mid-line split) and large (multi-line) reads.
    sizes = [rng.choice([1, 2, 5, 11, 23, 64, 250]) for _ in range(4000)]

    conn = SerialConnection(url="chunk://test")
    conn._port = ChunkedPort(data, sizes)
    conn.connected = True

    reader = SerialReader(conn)
    reader.start()

    store = TaskStateStore(max_history=10 * BURST, max_tasks=None)
    deadline = time.time() + 15
    try:
        while time.time() < deadline:
            for line in reader.drain():
                store.ingest_line(line)
            total = sum(len(v) for v in store.task_states.values())
            if total >= BURST:
                break
            time.sleep(0.005)
    finally:
        reader.stop()

    total = sum(len(v) for v in store.task_states.values())
    assert total == BURST, f"dropped {BURST - total} of {BURST} lines"
    assert reader.dropped == 0

    # Every device tick 0..BURST-1 must be present exactly once — proves no line
    # was lost or merged by the framing reassembly.
    seen = sorted(int(ts) for stamps in store.task_timestamps.values() for ts in stamps)
    assert seen == list(range(BURST))
