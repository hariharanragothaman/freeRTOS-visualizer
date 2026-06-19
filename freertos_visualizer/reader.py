"""Background serial reader that decouples ingest rate from render rate.

The original GUI read exactly one line per repaint tick, so it drained the port
at the repaint rate (~1 line/s by default) no matter how fast the device emitted
data. At any real baud rate the OS buffer backs up and samples are silently
dropped.

``SerialReader`` runs a dedicated thread that continuously drains the connection
into a bounded :class:`queue.Queue`. The GUI then drains *everything available*
each repaint and only the render is throttled. Ingest rate and paint rate are
independent.

It works with any object exposing ``connect`` / ``readline`` / ``close`` — both
:class:`~freertos_visualizer.visualize.SerialConnection` and
:class:`~freertos_visualizer.simulator.TaskSimulator` qualify (duck typing), so
the demo and hardware paths exercise the *same* pipeline.
"""

import queue
import threading
import time


class SerialReader:
    def __init__(self, conn, max_queue=100_000, idle_sleep=0.005, _sleep=time.sleep):
        self._conn = conn
        self._queue = queue.Queue(maxsize=max_queue)
        self._stop = threading.Event()
        self._thread = None
        self._idle_sleep = idle_sleep
        self._sleep = _sleep
        # Number of lines dropped because the queue was full (backpressure).
        self.dropped = 0

    def start(self):
        """Start the background reader thread."""
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="serial-reader", daemon=True)
        self._thread.start()

    def _run(self):
        while not self._stop.is_set():
            try:
                line = self._conn.readline()
            except Exception:
                # Connection objects already swallow their own errors; guard the
                # thread regardless so a transient failure can't kill ingest.
                line = ""
            if line:
                self._offer(line)
            else:
                # No data (timeout, backoff, or idle) — yield instead of spinning.
                self._sleep(self._idle_sleep)

    def _offer(self, line):
        try:
            self._queue.put_nowait(line)
        except queue.Full:
            self.dropped += 1

    def drain(self, max_items=None):
        """Return all currently-queued lines (optionally at most ``max_items``)."""
        items = []
        while max_items is None or len(items) < max_items:
            try:
                items.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return items

    def qsize(self):
        return self._queue.qsize()

    def stop(self, timeout=2.0):
        """Stop the reader thread and close the underlying connection."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            self._thread = None
        try:
            self._conn.close()
        except Exception:  # nosec B110
            pass
