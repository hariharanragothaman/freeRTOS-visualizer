import argparse
import csv
import re
import sys
import time

from freertos_visualizer import security

try:
    import serial
except ImportError:  # pragma: no cover - exercised through runtime checks
    serial = None

try:
    from PyQt5.QtCore import QTimer
    from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
except ImportError:  # pragma: no cover - exercised through runtime checks
    QApplication = None
    QMainWindow = None
    QTimer = None
    QWidget = None
    QVBoxLayout = None
    FigureCanvas = object
    Figure = None

# Codes mirror FreeRTOS eTaskState (task.h): eRunning..eInvalid.
STATE_DICT = {
    '0': 'Running',
    '1': 'Ready',
    '2': 'Blocked',
    '3': 'Suspended',
    '4': 'Deleted',
    '5': 'Invalid',
}

_BACKOFF_INITIAL_S = 1.0
_BACKOFF_MAX_S = 30.0
_BACKOFF_FACTOR = 2.0

# Task name is comma-free (anchored to [^,\s]+ so it cannot swallow the
# following fields). An optional device tick makes timing device-relative.
_LINE_RE = re.compile(r"Task:([^,\s]+),State:(\d+)(?:,Tick:(\d+))?")

# Out-of-band metadata the device announces so the host can interpret ticks:
#   TickRate:<hz>   -- ticks per second, lets the host convert ticks -> seconds
#   TickBits:<n>    -- tick counter width, so wraparound can be unwrapped
# Anchored at start so a normal "Task:...,Tick:n" line can never match.
_META_RE = re.compile(r"^Tick(Rate|Bits):(\d+)\s*$")


def parse_meta_line(line):
    """Parse a protocol metadata line (``TickRate:``/``TickBits:``).

    Returns a dict like ``{"tick_rate_hz": 1000}`` or ``{"tick_bits": 32}``,
    or ``None`` if the line is not metadata.
    """
    match = _META_RE.match(line)
    if not match:
        return None
    field, value = match.group(1), int(match.group(2))
    if field == "Rate":
        if value <= 0:
            return None
        return {"tick_rate_hz": value}
    if value <= 0:
        return None
    return {"tick_bits": value}


def parse_serial_line(line, max_name_length=security.DEFAULT_MAX_NAME_LENGTH):
    """Parse one protocol line.

    Returns ``(task_name, task_state, tick)`` or ``None``. ``tick`` is the
    device-supplied tick as an ``int`` when the optional ``,Tick:<n>`` field is
    present, otherwise ``None``.
    """
    match = _LINE_RE.search(line)
    if not match:
        return None

    # The task name comes from an untrusted device: strip control/ANSI bytes
    # and bound its length before it propagates to storage, CSV, or the console.
    task_name = security.sanitize_display_text(match.group(1), max_length=max_name_length)
    if not task_name:
        return None

    task_state = STATE_DICT.get(match.group(2), 'Unknown')
    tick = int(match.group(3)) if match.group(3) is not None else None
    return task_name, task_state, tick


class TaskStateStore:
    """Accumulates per-task state history with a timestamp for every sample.

    ``task_states`` maps task name -> list of state strings (kept for backward
    compatibility), and ``task_timestamps`` maps task name -> a parallel list of
    monotonic-ish timestamps captured at ingest time. Pass ``clock`` (a callable
    returning a float) to make timestamps deterministic in tests.
    """

    def __init__(self, max_history=10_000, clock=time.time, max_tasks=security.DEFAULT_MAX_TASKS,
                 tick_rate_hz=None, tick_bits=32):
        self.task_states = {}
        self.task_timestamps = {}
        self.max_history = max_history
        self.max_tasks = max_tasks
        self._clock = clock
        # Tick semantics. ``tick_rate_hz`` (ticks/second) lets the host convert
        # device ticks into seconds; ``tick_bits`` is the counter width used to
        # unwrap wraparound. Both can be set up front or learned at runtime from
        # TickRate:/TickBits: protocol metadata.
        self.tick_rate_hz = tick_rate_hz
        self.tick_bits = tick_bits
        self._tick_modulus = 1 << tick_bits
        # Clock domain is locked to the first sample so device ticks and host
        # wall-clock can never interleave in one task's history (see #46).
        self._domain = None
        self._last_raw_tick = None
        self._tick_offset = 0

    def _apply_meta(self, meta):
        if "tick_rate_hz" in meta:
            self.tick_rate_hz = meta["tick_rate_hz"]
        if "tick_bits" in meta:
            self.tick_bits = meta["tick_bits"]
            self._tick_modulus = 1 << self.tick_bits

    def _unwrap_tick(self, tick):
        """Map a wrapping device tick to a monotonic 64-bit value.

        Device ticks are non-decreasing between snapshots, so any strict
        decrease is a counter wrap; accumulate one modulus per wrap. Honors the
        advertised ``tick_bits`` so 16- and 32-bit counters both unwrap.
        """
        if self._last_raw_tick is not None and tick < self._last_raw_tick:
            self._tick_offset += self._tick_modulus
        self._last_raw_tick = tick
        return tick + self._tick_offset

    def _resolve_timestamp(self, tick):
        """Return the timestamp for a sample, or ``None`` to reject a domain mix."""
        domain = "device" if tick is not None else "host"
        if self._domain is None:
            self._domain = domain
        elif domain != self._domain:
            # Refuse to interleave device ticks (~1e3) and host epoch seconds
            # (~1e9) in one history — that corruption is invisible until it isn't.
            return None
        if domain == "device":
            return float(self._unwrap_tick(tick))
        return self._clock()

    @property
    def clock_domain(self):
        """``"device"``, ``"host"``, or ``None`` before the first sample."""
        return self._domain

    @property
    def time_scale(self):
        """Multiplier to convert stored timestamps to seconds (1.0 if already)."""
        if self._domain == "device" and self.tick_rate_hz:
            return 1.0 / self.tick_rate_hz
        return 1.0

    @property
    def time_axis_label(self):
        """Honest x-axis label: seconds only when the unit really is seconds."""
        if self._domain == "device" and not self.tick_rate_hz:
            return "Device ticks"
        return "Time (s)"

    def ingest_line(self, line, timestamp=None):
        meta = parse_meta_line(line)
        if meta is not None:
            self._apply_meta(meta)
            return None

        parsed = parse_serial_line(line)
        if not parsed:
            return None

        task_name, task_state, tick = parsed

        # Prefer the device tick (the transition's real time on the target) over
        # the host read time, which is distorted by buffering and scheduling.
        # Locks the clock domain and unwraps tick wraparound; rejects a line
        # whose domain doesn't match what was locked in.
        if timestamp is None:
            timestamp = self._resolve_timestamp(tick)
            if timestamp is None:
                return None

        # Resource cap: a hostile device could emit unbounded distinct task
        # names to exhaust memory. Once the cap is hit, ignore unseen tasks
        # (already-tracked tasks continue to update).
        if (
            self.max_tasks is not None
            and task_name not in self.task_states
            and len(self.task_states) >= self.max_tasks
        ):
            return None

        history = self.task_states.setdefault(task_name, [])
        stamps = self.task_timestamps.setdefault(task_name, [])
        history.append(task_state)
        stamps.append(timestamp)
        if len(history) > self.max_history:
            overflow = len(history) - self.max_history
            del history[:overflow]
            del stamps[:overflow]
        return parsed

    def history(self, task_name):
        """Return a list of ``(timestamp, state)`` tuples for ``task_name``."""
        return list(zip(
            self.task_timestamps.get(task_name, []),
            self.task_states.get(task_name, []),
        ))

    def summary(self):
        """Return per-task statistics (see :func:`stats.compute_summary`)."""
        from freertos_visualizer.stats import compute_summary

        return compute_summary(self)

    def export_csv(self, output_path):
        # Task names originate from an untrusted device. Neutralize spreadsheet
        # formula injection before writing them to a CSV that a human may open.
        with open(output_path, "w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(["task_name", "sample_index", "timestamp", "state"])
            for task_name, states in self.task_states.items():
                stamps = self.task_timestamps.get(task_name, [])
                safe_name = security.sanitize_csv_field(task_name)
                for sample_index, state in enumerate(states):
                    timestamp = stamps[sample_index] if sample_index < len(stamps) else ""
                    writer.writerow([
                        safe_name,
                        sample_index,
                        timestamp,
                        security.sanitize_csv_field(state),
                    ])


class SerialConnection:
    """Wrapper around pyserial that reconnects with exponential backoff."""

    def __init__(self, url, baudrate=115200, timeout=1.0, clock=time.time,
                 max_line_length=security.DEFAULT_MAX_LINE_LENGTH):
        self.url = url
        self.baudrate = baudrate
        self.timeout = timeout
        self.max_line_length = max_line_length
        # ``clock`` is a callable returning a float (same convention as
        # TaskStateStore), injectable for deterministic tests.
        self._clock = clock
        self._port = None
        self._backoff = _BACKOFF_INITIAL_S
        self._last_attempt = 0.0
        self.connected = False
        # Bytes read but not yet terminated by a newline. pyserial's readline
        # returns a *partial* line when its timeout fires mid-line (common on a
        # real UART or a loaded host), so we reassemble across reads instead of
        # treating a fragment as a whole — otherwise that line is corrupted/lost.
        self._buf = b""

    def connect(self):
        if serial is None:
            raise RuntimeError("pyserial is not installed")
        self._port = serial.serial_for_url(
            self.url, baudrate=self.baudrate, timeout=self.timeout,
        )
        self.connected = True
        self._backoff = _BACKOFF_INITIAL_S
        self._buf = b""

    def readline(self):
        if not self.connected:
            now = self._clock()
            if now - self._last_attempt < self._backoff:
                return ""
            self._last_attempt = now
            try:
                self.connect()
            except Exception:
                self._backoff = min(self._backoff * _BACKOFF_FACTOR, _BACKOFF_MAX_S)
                return ""

        # Only read more when we don't already have a complete buffered line.
        if b"\n" not in self._buf:
            try:
                self._buf += self._port.readline()
            except Exception:
                self.connected = False
                self._last_attempt = self._clock()
                self._buf = b""
                return ""

        if b"\n" in self._buf:
            raw, _, self._buf = self._buf.partition(b"\n")
            # Bound the line so a hostile device cannot push an unbounded one.
            raw = security.clamp_line(raw, self.max_line_length)
            return raw.decode("utf-8", errors="replace").strip()

        # No complete line yet. Bound the partial so a device that never sends a
        # newline cannot grow the buffer without limit.
        if len(self._buf) > self.max_line_length:
            self._buf = self._buf[-self.max_line_length:]
        return ""

    def close(self):
        if self._port is not None:
            # Best-effort close; there is nothing to recover if it fails.
            try:
                self._port.close()
            except Exception:  # nosec B110
                pass
            self._port = None
        self.connected = False


class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        if Figure is None:
            raise RuntimeError("Matplotlib/PyQt5 dependencies are required for GUI rendering.")
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super(MplCanvas, self).__init__(fig)


class TaskVisualization(QMainWindow if QMainWindow is not None else object):
    def __init__(self, serial_conn, refresh_interval_ms=1000, export_csv_path=None, view="bar"):
        if QMainWindow is None:
            raise RuntimeError("PyQt5 is required to launch the visualizer UI.")
        super().__init__()
        from freertos_visualizer.reader import SerialReader

        self.serial_conn = serial_conn
        # A dedicated thread drains the port at line rate; the repaint timer only
        # throttles rendering. Ingest rate and paint rate are decoupled.
        self.reader = SerialReader(serial_conn)
        self.refresh_interval_ms = refresh_interval_ms
        self.export_csv_path = export_csv_path
        self.view = view
        self.store = TaskStateStore()
        from freertos_visualizer.timeline import SegmentCache

        # Reused across repaints so the timeline appends instead of rebuilding
        # the full history each frame.
        self._segment_cache = SegmentCache()

        self.initUI()
        self.reader.start()

    def initUI(self):
        self.setWindowTitle("FreeRTOS Task State Visualization")
        self.setGeometry(100, 100, 800, 600)

        # Set up layout
        layout = QVBoxLayout()

        # Initialize Matplotlib Canvas
        self.canvas = MplCanvas(self, width=5, height=4, dpi=100)
        layout.addWidget(self.canvas)

        # Set up widget
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Timer to update task states
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_task_states)
        self.timer.start(self.refresh_interval_ms)

    def update_task_states(self):
        # Drain everything the reader has buffered since the last repaint, so a
        # fast device is fully captured even though we paint at refresh_interval.
        for line in self.reader.drain():
            self.store.ingest_line(line)
        if self.view == "timeline":
            self.plot_timeline()
        else:
            self.plot_task_states()

    def plot_task_states(self):
        from freertos_visualizer.render import draw_bar_chart

        draw_bar_chart(self.canvas.axes, self.store)
        self.canvas.draw()

    def plot_timeline(self):
        from freertos_visualizer.render import draw_timeline

        draw_timeline(self.canvas.axes, self.store, cache=self._segment_cache)
        self.canvas.draw()

    def closeEvent(self, event):
        self.reader.stop()
        if self.export_csv_path:
            self.store.export_csv(self.export_csv_path)
        super().closeEvent(event)


def main():
    parser = argparse.ArgumentParser(description="Visualize FreeRTOS task states from serial data.")
    parser.add_argument("--serial-url", default="socket://localhost:12345", help="Serial endpoint URL.")
    parser.add_argument("--baudrate", type=int, default=115200, help="Serial baudrate.")
    parser.add_argument("--timeout", type=float, default=1.0, help="Serial read timeout in seconds.")
    parser.add_argument("--refresh-ms", type=int, default=1000, help="UI refresh interval in milliseconds.")
    parser.add_argument("--export-csv", help="Path to export task history CSV when the UI closes.")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run against the built-in serial simulator instead of a real port (no hardware needed).",
    )
    parser.add_argument("--seed", type=int, default=0, help="Seed for the --demo simulator.")
    parser.add_argument("--demo-rate", type=float, default=200.0,
                        help="Lines/second emitted by the --demo simulator.")
    parser.add_argument(
        "--view",
        choices=("bar", "timeline"),
        default="bar",
        help="Visualization style: live bar chart (default) or Gantt-style timeline.",
    )
    args = parser.parse_args()

    if QApplication is None:
        print("PyQt5 and matplotlib are required. Install dependencies and retry.")
        sys.exit(1)

    if args.demo:
        from freertos_visualizer.simulator import TaskSimulator

        # Paced + tick-emitting so the demo exercises the same threaded reader
        # pipeline (and device-tick timing) as real hardware. The simulated tick
        # advances one step per line, so announcing TickRate == lines/second
        # makes the timeline axis read in real seconds.
        conn = TaskSimulator(
            seed=args.seed, emit_tick=True, rate_hz=args.demo_rate,
            tick_rate_hz=int(args.demo_rate),
        )
        print("Running in demo mode with the built-in serial simulator.")
    else:
        if serial is None:
            print("pyserial is required. Install dependencies and retry.")
            sys.exit(1)
        conn = SerialConnection(
            url=args.serial_url,
            baudrate=args.baudrate,
            timeout=args.timeout,
        )
        # The reader thread connects lazily and reconnects with backoff.

    app = QApplication(sys.argv)
    vis = TaskVisualization(
        conn,
        refresh_interval_ms=args.refresh_ms,
        export_csv_path=args.export_csv,
        view=args.view,
    )
    vis.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
