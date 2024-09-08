import sys
import re
import serial
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt5.QtCore import QTimer
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# Task state dictionary
state_dict = {
    '0': 'Running',
    '1': 'Ready',
    '2': 'Blocked',
    '3': 'Suspended'
}


class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super(MplCanvas, self).__init__(fig)


class TaskVisualization(QMainWindow):
    def __init__(self, serial_port):
        super().__init__()
        self.serial_port = serial_port
        self.task_states = {}
        self.current_time = 0

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
        self.timer.start(1000)  # Update every second

    def update_task_states(self):
        try:
            # Read a line from the serial port
            line = self.serial_port.readline().decode('utf-8').strip()
            if line:
                # Parse the line using regex
                match = re.search(r"Task:(\S+),State:(\d+)", line)
                if match:
                    task_name = match.group(1)
                    task_state = state_dict.get(match.group(2), 'Unknown')

                    # Initialize task history if new
                    if task_name not in self.task_states:
                        self.task_states[task_name] = []

                    # Append current state
                    self.task_states[task_name].append(task_state)

        except Exception as e:
            print(f"Error reading serial data: {e}")

        # Update Matplotlib plot
        self.plot_task_states()

    def plot_task_states(self):
        self.canvas.axes.clear()

        # Prepare data
        tasks = list(self.task_states.keys())
        states = [self.task_states[task][-1] for task in tasks]
        state_values = [list(state_dict.values()).index(state) + 1 for state in
                        states]  # Assign numerical values for plotting

        # Create bar chart
        bars = self.canvas.axes.bar(tasks, state_values, color='skyblue')

        # Set labels and title
        self.canvas.axes.set_ylim(0, len(state_dict) + 1)
        self.canvas.axes.set_ylabel('Task State')
        self.canvas.axes.set_title('Current Task States')

        # Set y-ticks to state names
        self.canvas.axes.set_yticks(range(1, len(state_dict) + 1))
        self.canvas.axes.set_yticklabels(state_dict.values())

        # Add text labels on bars
        for bar, state in zip(bars, states):
            height = bar.get_height()
            self.canvas.axes.text(bar.get_x() + bar.get_width() / 2., height + 0.1, state, ha='center', va='bottom')

        self.canvas.draw()


def main():
    # Connect to QEMU's serial port over TCP
    try:
        ser = serial.serial_for_url('socket://localhost:12345', baudrate=115200, timeout=1)
    except Exception as e:
        print(f"Failed to connect to serial port: {e}")
        sys.exit(1)

    app = QApplication(sys.argv)
    vis = TaskVisualization(ser)
    vis.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
