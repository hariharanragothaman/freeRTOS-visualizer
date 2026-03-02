# freeRTOS-visualizer

A Python tool for real-time visualization of FreeRTOS task states.

## Introduction

**freeRTOS-visualizer** connects to a running FreeRTOS instance (for example, emulated via QEMU) over a serial link and displays task states dynamically using a PyQt5/Matplotlib GUI. It is open-source, cross-platform, and designed to be easy to integrate into existing FreeRTOS projects.

## Features

- **Real-Time Visualization** — monitor task states (Running, Ready, Blocked, Suspended) as they change.
- **Dynamic Bar Charts** — each task's current state rendered as a live bar chart.
- **CSV Data Export** — export the full task-state history to a CSV file on exit via `--export-csv`.
- **Automatic Reconnect** — if the serial link drops, the tool retries with exponential backoff.
- **CLI Configuration** — serial URL, baud rate, timeout, and refresh interval are all configurable from the command line.
- **Cross-Platform** — compatible with macOS, Linux, and Windows.

## Installation

### Prerequisites

- Python 3.9+
- A serial data source (QEMU, real hardware UART, etc.)

### From PyPI

```bash
pip install freertos-visualizer
```

### From Source

```bash
git clone https://github.com/hariharanragothaman/freeRTOS-visualizer.git
cd freeRTOS-visualizer
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

### 1. Start QEMU with Serial Redirection

```bash
qemu-system-arm -M mps2-an385 -kernel RTOSDemo.axf -nographic \
  -serial tcp::12345,server,nowait
```

### 2. Run the Visualizer

If installed from PyPI:

```bash
rtos-visualize
```

Or run the module directly:

```bash
python -m freertos_visualizer.visualize
```

### CLI Options

| Flag              | Default                        | Description                              |
|-------------------|--------------------------------|------------------------------------------|
| `--serial-url`    | `socket://localhost:12345`     | Serial endpoint URL                      |
| `--baudrate`      | `115200`                       | Serial baud rate                         |
| `--timeout`       | `1.0`                          | Serial read timeout (seconds)            |
| `--refresh-ms`    | `1000`                         | GUI refresh interval (milliseconds)      |
| `--export-csv`    | *(none)*                       | Path to write task-history CSV on exit   |

**Example — custom port and CSV export:**

```bash
rtos-visualize --serial-url socket://192.168.1.10:5555 --refresh-ms 500 \
  --export-csv task_history.csv
```

## Serial Protocol

The tool expects lines in the format:

```
Task:<name>,State:<code>
```

Where `<code>` maps to:

| Code | State     |
|------|-----------|
| 0    | Running   |
| 1    | Ready     |
| 2    | Blocked   |
| 3    | Suspended |

Any unrecognized code is displayed as **Unknown**.

## Development

```bash
git clone https://github.com/hariharanragothaman/freeRTOS-visualizer.git
cd freeRTOS-visualizer
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### Running Tests

```bash
python -m pytest -v
```

### Project Layout

```
freertos_visualizer/
  visualize.py        # Core logic: parsing, state store, serial, GUI
tests/
  test_serial.py      # Unit tests (parser, store, serial mock, CSV export)
docs/
  paper.md            # JOSS-style paper
  paper.bib
```

## Contributing

Contributions are welcome! Please read the [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
