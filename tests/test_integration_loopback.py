"""End-to-end ingest test over a real TCP loopback (pyserial ``socket://``).

This is the test the external review asked for: feed a burst of lines through
the *actual* serial path and assert none are dropped. It exercises
SerialConnection + SerialReader + TaskStateStore together, which the unit tests
(and the GUI's ``pragma: no cover``) never touch.
"""

import socket
import threading
import time

import pytest

pytest.importorskip("serial")

from freertos_visualizer.reader import SerialReader
from freertos_visualizer.visualize import SerialConnection, TaskStateStore

BURST = 2000


def _serve_burst(srv, count, done):
    conn, _addr = srv.accept()
    try:
        for i in range(count):
            conn.sendall(f"Task:T{i % 4},State:{i % 4},Tick:{i}\n".encode("utf-8"))
        # Keep the connection open until the client has drained everything.
        # Closing early can drop the tail of the kernel buffer on slow runners;
        # waiting on an explicit signal makes the test deterministic.
        done.wait(timeout=30)
    finally:
        conn.close()


def test_loopback_burst_has_no_dropped_lines():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    port = srv.getsockname()[1]

    done = threading.Event()
    server_thread = threading.Thread(target=_serve_burst, args=(srv, BURST, done), daemon=True)
    server_thread.start()

    conn = SerialConnection(url=f"socket://127.0.0.1:{port}", timeout=0.2)
    reader = SerialReader(conn)
    reader.start()

    store = TaskStateStore(max_history=10 * BURST, max_tasks=None)
    deadline = time.time() + 30
    try:
        while time.time() < deadline:
            for line in reader.drain():
                store.ingest_line(line)
            total = sum(len(v) for v in store.task_states.values())
            if total >= BURST:
                break
            time.sleep(0.01)
    finally:
        done.set()  # let the server close now that we've drained
        reader.stop()
        srv.close()

    total = sum(len(v) for v in store.task_states.values())
    assert total == BURST, f"dropped {BURST - total} of {BURST} lines"
    assert reader.dropped == 0
