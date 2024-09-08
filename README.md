# freeRTOS-visualizer
Python Tool to visualize RTOS tasks in real-time

## Introduction
A Python-based tool that provides real-time visualization of task states in a FreeRTOS environment. It connects to a running FreeRTOS instance (emulated via QEMU) and displays task states dynamically using an intuitive GUI.

## Features
- **Real-Time Visualization:** Monitor task states as they change in real-time.
- **Dynamic Bar Charts:** Visual representation of each task's current state.
- **Data Export:** Export task state histories as CSV files.
- **Cross-Platform Support:** Compatible with macOS, Linux, and Windows.
- **Customizable Interface:** Easily modify the visualization parameters.

## Installation

### Prerequisites
- Python 3.x
- pip

### Steps
1. **Clone the Repository:**
    ```bash
    git clone https://github.com/your-repo/freeRTOS-visualization-tool.git
    cd freeRTOS-visualization-tool
    ```

2. **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Usage

1. **Start QEMU with Serial Redirection:**
    ```bash
    qemu-system-arm -M mps2-an385 -kernel RTOSDemo.axf -nographic -serial tcp::12345,server,nowait
    ```

2. **Run the Visualization Tool:**
    ```bash
    python visualize.py
    ```

   The GUI will launch, displaying the current states of tasks in your FreeRTOS environment.

## Contributing

Contributions are welcome! Please read the [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
