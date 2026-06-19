"""Backpressure accounting for SerialReader (#47).

The socket loopback proves transport + reassembly, but its ``dropped == 0`` is
vacuous: a 2k burst into a 100k queue can't overflow. These tests put the reader
under *real* pressure — a tiny bounded queue and a sender that outruns the drain
— and assert the drop accounting exactly: ``dropped == sent - delivered``.
"""

import threading
import time

from freertos_visualizer.reader import SerialReader


class _FiniteSource:
    """A SerialConnection-shaped source that yields ``total`` lines then idles.

    Signals ``done`` once every line has been handed to the reader, so the test
    can wait for steady state before asserting (no sleeps-for-luck).
    """

    def __init__(self, total):
        self.total = total
        self.sent = 0
        self.done = threading.Event()

    def connect(self):
        pass

    def readline(self):
        if self.sent < self.total:
            self.sent += 1
            return f"Task:T{self.sent % 4},State:{self.sent % 4},Tick:{self.sent}"
        self.done.set()
        return ""  # exhausted: reader treats this as idle

    def close(self):
        pass


def test_drops_account_exactly_under_backpressure():
    total = 5000
    max_queue = 10
    source = _FiniteSource(total)
    # Drain nothing while the source runs, so the queue saturates and the
    # overflow is dropped — exercising the queue.Full / dropped path.
    reader = SerialReader(source, max_queue=max_queue, idle_sleep=0.001)
    reader.start()
    try:
        assert source.done.wait(timeout=10), "source did not finish feeding"
        # Let the reader observe exhaustion and settle.
        time.sleep(0.05)
        delivered_items = reader.drain()
    finally:
        reader.stop()

    delivered = len(delivered_items)
    # The queue can hold at most max_queue at the moment we drain.
    assert delivered <= max_queue
    assert reader.dropped > 0, "expected real backpressure to drop lines"
    # The accounting the socket test only ever asserts is zero:
    assert delivered + reader.dropped == total
    assert reader.dropped == total - delivered


def test_no_drops_when_queue_is_large_enough():
    total = 2000
    source = _FiniteSource(total)
    reader = SerialReader(source, max_queue=total + 100, idle_sleep=0.001)
    reader.start()
    delivered = 0
    try:
        assert source.done.wait(timeout=10)
        deadline = time.time() + 5
        while delivered < total and time.time() < deadline:
            delivered += len(reader.drain())
            time.sleep(0.001)
    finally:
        reader.stop()
    assert delivered == total
    assert reader.dropped == 0
