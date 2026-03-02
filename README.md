<p align="center">
  <h1 align="center">freeRTOS-visualizer</h1>
</p>

<p align="center">
  <b>Real-time visualization of FreeRTOS task states over serial. Open-source and cross-platform.</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.9+-blue?logo=python&logoColor=white" alt="python 3.9+" />
  <img src="https://img.shields.io/badge/PyQt5-GUI-green?logo=qt&logoColor=white" alt="PyQt5 GUI" />
  <img src="https://img.shields.io/badge/matplotlib-charts-orange?logo=plotly&logoColor=white" alt="matplotlib charts" />
  <img src="https://img.shields.io/badge/pyserial-serial%20IO-yellow" alt="pyserial" />
  <img src="https://img.shields.io/badge/tests-22%20passing-brightgreen" alt="tests 22 passing" />
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="license MIT" /></a>
  <a href="https://github.com/hariharanragothaman/freeRTOS-visualizer/stargazers"><img src="https://img.shields.io/github/stars/hariharanragothaman/freeRTOS-visualizer" alt="GitHub Stars" /></a>
</p>

<p align="center">
  <a href="#features">Features</a> · <a href="#how-it-works">How It Works</a> · <a href="#quick-start">Quick Start</a> · <a href="#cli-options">CLI Options</a> · <a href="#serial-protocol">Serial Protocol</a> · <a href="#development">Development</a> · <a href="#project-layout">Project Layout</a> · <a href="#roadmap">Roadmap</a>
</p>

---

## Features

- **Real-Time Visualization** — monitor task states (Running, Ready, Blocked, Suspended) as they change
- **Dynamic Bar Charts** — each task's current state rendered as a live-updating bar chart
- **CSV Data Export** — export the full task-state history to a CSV file on exit via `--export-csv`
- **Automatic Reconnect** — if the serial link drops, the tool retries with exponential backoff
- **CLI Configuration** — serial URL, baud rate, timeout, and refresh interval are all configurable
- **Cross-Platform** — compatible with macOS, Linux, and Windows

---

## How It Works

```
┌──────────────┐   serial/TCP   ┌───────────────────┐   matplotlib   ┌────────────┐
│  FreeRTOS    │ ─────────────▶ │  SerialConnection │ ────────────▶ │  PyQt5 GUI │
│  (QEMU/HW)  │   Task:X,      │  + TaskStateStore │               │  Bar Chart │
└──────────────┘   State:N      └───────────────────┘               └────────────┘
```

1. FreeRTOS prints `Task:<name>,State:<code>` lines over a serial port
2. `SerialConnection` reads and decodes lines, reconnecting automatically on failure
3. `TaskStateStore` parses and accumulates task-state history
4. The PyQt5 GUI renders a live bar chart, refreshing on a configurable interval

---

## Quick Start

### Install

**From PyPI:**

```bash
pip install freertos-visualizer
```

**From source:**

```bash
git clone https://github.com/hariharanragothaman/freeRTOS-visualizer.git
cd freeRTOS-visualizer
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### Run

**1. Start QEMU with serial redirection:**

```bash
qemu-system-arm -M mps2-an385 -kernel RTOSDemo.axf -nographic \
  -serial tcp::12345,server,nowait
```

**2. Launch the visualizer:**

```bash
# If installed from PyPI
rtos-visualize

# Or run the module directly
python -m freertos_visualizer.visualize
```

**3. (Optional) Export history on exit:**

```bash
rtos-visualize --export-csv task_history.csv
```

---

## CLI Options

| Flag | Default | Description |
|---|---|---|
| `--serial-url` | `socket://localhost:12345` | Serial endpoint URL |
| `--baudrate` | `115200` | Serial baud rate |
| `--timeout` | `1.0` | Serial read timeout (seconds) |
| `--refresh-ms` | `1000` | GUI refresh interval (milliseconds) |
| `--export-csv` | *(none)* | Path to write task-history CSV on exit |

**Example — custom endpoint and fast refresh:**

```bash
rtos-visualize --serial-url socket://192.168.1.10:5555 --refresh-ms 500 \
  --export-csv task_history.csv
```

---

## Serial Protocol

The tool expects lines in the format:

```
Task:<name>,State:<code>
```

| Code | State |
|------|-----------|
| 0 | Running |
| 1 | Ready |
| 2 | Blocked |
| 3 | Suspended |

Any unrecognized code is displayed as **Unknown**. Lines that don't match the pattern are silently ignored.

---

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

Tests cover: serial-line parsing, state-store history tracking, CSV export, `SerialConnection` reconnect/backoff logic, malformed binary input, and end-to-end pipeline integration.

---

## Project Layout

```
freertos_visualizer/
  visualize.py          # Core logic: parsing, state store, serial, GUI
tests/
  test_serial.py        # 22 unit tests (parser, store, serial mock, CSV)
docs/
  paper.md              # JOSS-style paper
  paper.bib
.github/workflows/
  ci.yml                # CI: tests on push to main (Python 3.9–3.13)
  build-publish.yml     # Publish to PyPI on version tags
```

---

## Roadmap

- [ ] Timestamps in task-state history (not just sample index)
- [ ] In-app export button / periodic autosave
- [ ] Timeline / Gantt chart view alongside bar chart
- [ ] Configurable color schemes and chart types
- [ ] Support for additional FreeRTOS trace data (stack usage, CPU %)

---

## Contributing

Contributions are welcome! Please read the [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
