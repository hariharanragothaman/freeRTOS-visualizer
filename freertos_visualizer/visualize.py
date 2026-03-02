import argparse
import csv
import re
import sys
import time

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

STATE_DICT = {
    '0': 'Running',
    '1': 'Ready',
    '2': 'Blocked',
    '3': 'Suspended',
}

# Keep the old name around for backward compatibility
state_dict = STATE_DICT

_BACKOFF_INITIAL_S = 1.0
_BACKOFF_MAX_S = 30.0
_BACKOFF_FACTOR = 2.0


def parse_serial_line(line):
    match = re.search(r"Task:(\S+),State:(\d+)", line)
    if not match:
        return None

    task_name = match.group(1)
    task_state = STATE_DICT.get(match.group(2), 'Unknown')
    return task_name, task_state


class TaskStateStore:
    def __init__(self, max_history=10_000):
        self.task_states = {}
        self.max_history = max_history

    def ingest_line(self, line):
        parsed = parse_serial_line(line)
        if not parsed:
            return None

        task_name, task_state = parsed
        history = self.task_states.setdefault(task_name, [])
        history.append(task_state)
        if len(history) > self.max_history:
            del history[: len(history) - self.max_history]
        return parsed

    def export_csv(self, output_path):
        with open(output_path, "w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(["task_name", "sample_index", "state"])
            for task_name, history in self.task_states.items():
                for sample_index, state in enumerate(history):
                    writer.writerow([task_name, sample_index, state])


class SerialConnection:
    """Wrapper around pyserial that reconnects with exponential backoff."""

    def __init__(self, url, baudrate=115200, timeout=1.0, _clock=time):
        self.url = url
        self.baudrate = baudrate
        self.timeout = timeout
        self._clock = _clock
        self._port = None
        self._backoff = _BACKOFF_INITIAL_S
        self._last_attempt = 0.0
        self.connected = False

    def _open(self):
        if serial is None:
            raise RuntimeError("pyserial is not installed")
        self._port = serial.serial_for_url(
            self.url, baudrate=self.baudrate, timeout=self.timeout,
        )
        self.connected = True
        self._backoff = _BACKOFF_INITIAL_S

    def connect(self):
        try:
            self._open()
        except Exception as exc:
            self.connected = False
            raise exc

    def readline(self):
        if not self.connected:
            now = self._clock.time()
            if now - self._last_attempt < self._backoff:
                return ""
            self._last_attempt = now
            try:
                self._open()
            except Exception:
                self._backoff = min(self._backoff * _BACKOFF_FACTOR, _BACKOFF_MAX_S)
                return ""

        try:
            raw = self._port.readline()
            return raw.decode("utf-8", errors="replace").strip()
        except Exception:
            self.connected = False
            self._last_attempt = self._clock.time()
            return ""

    def close(self):
        if self._port is not None:
            try:
                self._port.close()
            except Exception:
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
    def __init__(self, serial_conn, refresh_interval_ms=1000, export_csv_path=None):
        if QMainWindow is None:
            raise RuntimeError("PyQt5 is required to launch the visualizer UI.")
        super().__init__()
        self.serial_conn = serial_conn
        self.refresh_interval_ms = refresh_interval_ms
        self.export_csv_path = export_csv_path
        self.store = TaskStateStore()

        self.initUI()

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
        line = self.serial_conn.readline()
        if line:
            self.store.ingest_line(line)
        self.plot_task_states()

    def plot_task_states(self):
        self.canvas.axes.clear()

        # Prepare data
        tasks = list(self.store.task_states.keys())
        if not tasks:
            self.canvas.axes.set_title('Current Task States')
            self.canvas.axes.text(0.5, 0.5, "Waiting for task data...", ha="center", va="center")
            self.canvas.draw()
            return

        states = [self.store.task_states[task][-1] for task in tasks]
        state_labels = list(state_dict.values())
        state_values = [(state_labels.index(state) + 1) if state in state_labels else 0 for state in states]

        # Create bar chart
        bars = self.canvas.axes.bar(tasks, state_values, color='skyblue')

        # Set labels and title
        self.canvas.axes.set_ylim(0, len(state_dict) + 1)
        self.canvas.axes.set_ylabel('Task State')
        self.canvas.axes.set_title('Current Task States')

        # Set y-ticks to include unknown states.
        self.canvas.axes.set_yticks(range(0, len(state_dict) + 1))
        self.canvas.axes.set_yticklabels(['Unknown'] + list(state_dict.values()))

        # Add text labels on bars
        for bar, state in zip(bars, states):
            height = bar.get_height()
            self.canvas.axes.text(bar.get_x() + bar.get_width() / 2., height + 0.1, state, ha='center', va='bottom')

        self.canvas.draw()

    def closeEvent(self, event):
        if self.export_csv_path:
            self.store.export_csv(self.export_csv_path)
        self.serial_conn.close()
        super().closeEvent(event)


def main():
    parser = argparse.ArgumentParser(description="Visualize FreeRTOS task states from serial data.")
    parser.add_argument("--serial-url", default="socket://localhost:12345", help="Serial endpoint URL.")
    parser.add_argument("--baudrate", type=int, default=115200, help="Serial baudrate.")
    parser.add_argument("--timeout", type=float, default=1.0, help="Serial read timeout in seconds.")
    parser.add_argument("--refresh-ms", type=int, default=1000, help="UI refresh interval in milliseconds.")
    parser.add_argument("--export-csv", help="Path to export task history CSV when the UI closes.")
    args = parser.parse_args()

    if serial is None:
        print("pyserial is required. Install dependencies and retry.")
        sys.exit(1)
    if QApplication is None:
        print("PyQt5 and matplotlib are required. Install dependencies and retry.")
        sys.exit(1)

    conn = SerialConnection(
        url=args.serial_url,
        baudrate=args.baudrate,
        timeout=args.timeout,
    )
    try:
        conn.connect()
    except Exception as e:
        print(f"Failed to connect to serial port: {e}")
        print("The visualizer will keep retrying in the background.")

    app = QApplication(sys.argv)
    vis = TaskVisualization(
        conn,
        refresh_interval_ms=args.refresh_ms,
        export_csv_path=args.export_csv,
    )
    vis.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
