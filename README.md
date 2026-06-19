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
  <a href="https://github.com/hariharanragothaman/freeRTOS-visualizer/actions/workflows/ci.yml"><img src="https://github.com/hariharanragothaman/freeRTOS-visualizer/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
  <a href="https://codecov.io/gh/hariharanragothaman/freeRTOS-visualizer"><img src="https://codecov.io/gh/hariharanragothaman/freeRTOS-visualizer/branch/main/graph/badge.svg" alt="coverage" /></a>
  <a href="https://github.com/hariharanragothaman/freeRTOS-visualizer/actions/workflows/codeql.yml"><img src="https://github.com/hariharanragothaman/freeRTOS-visualizer/actions/workflows/codeql.yml/badge.svg" alt="CodeQL" /></a>
  <a href="SECURITY.md"><img src="https://img.shields.io/badge/security-policy-blue" alt="security policy" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="license MIT" /></a>
  <a href="https://github.com/hariharanragothaman/freeRTOS-visualizer/stargazers"><img src="https://img.shields.io/github/stars/hariharanragothaman/freeRTOS-visualizer" alt="GitHub Stars" /></a>
</p>

<p align="center">
  <a href="#demo">Demo</a> · <a href="#features">Features</a> · <a href="#how-it-works">How It Works</a> · <a href="#quick-start">Quick Start</a> · <a href="#cli-options">CLI Options</a> · <a href="#serial-protocol">Serial Protocol</a> · <a href="#security">Security</a> · <a href="#development">Development</a> · <a href="#project-layout">Project Layout</a> · <a href="#roadmap">Roadmap</a>
</p>

---

## Demo

End-to-end demos below are generated **headlessly** from the built-in serial
simulator — no hardware required — by
[`examples/record_demo.py`](examples/record_demo.py). They show the exact same
rendering the live GUI produces.

| Live bar chart (`--demo`) | Timeline view (`--demo --view timeline`) |
|:---:|:---:|
| ![Bar chart demo](docs/demo_bar.gif) | ![Timeline demo](docs/demo_timeline.gif) |

Reproduce them yourself:

```bash
make gifs
# or
python examples/record_demo.py --mode both --out-dir docs
```

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

### Try it without hardware (demo mode)

No board or QEMU? Run the GUI against the built-in serial simulator:

```bash
rtos-visualize --demo                  # live bar chart
rtos-visualize --demo --view timeline  # Gantt-style timeline
# or
python -m freertos_visualizer.visualize --demo
python examples/run_demo.py
```

The simulator emits a realistic, seeded stream of `Task:<name>,State:<code>`
lines so you can see the visualization immediately. Use `--seed N` for a
different but reproducible stream.

### Run (against real hardware / QEMU)

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
| `--demo` | `false` | Use the built-in serial simulator (no hardware needed) |
| `--seed` | `0` | Seed for the `--demo` simulator |

**Example — custom endpoint and fast refresh:**

```bash
rtos-visualize --serial-url socket://192.168.1.10:5555 --refresh-ms 500 \
  --export-csv task_history.csv
```

The exported CSV has one row per sample with a capture timestamp:

```csv
task_name,sample_index,timestamp,state
LED_Blink,0,1718764812.31,Ready
LED_Blink,1,1718764813.33,Running
```

---

## Task Statistics

Compute a per-task breakdown — sample counts, state transitions, and
state distribution (with time-in-state percentages when timestamps are present):

```bash
python examples/print_stats.py --samples 500
# or
make stats
```

```
Task           Samples  Transitions  State distribution (by samples)
--------------------------------------------------------------------
LED_Blink          100           72  Running 17%, Ready 37%, Blocked 35%, Suspended 11%
SensorRead         100           79  Running 37%, Ready 38%, Blocked 18%, Suspended 7%
```

Programmatic use:

```python
from freertos_visualizer import TaskStateStore

store = TaskStateStore()
store.ingest_line("Task:LED,State:1")
store.ingest_line("Task:LED,State:0")
print(store.summary())   # {'LED': {'samples': 2, 'transitions': 1, ...}}
```

---

## Timeline / Gantt View

The timeline view plots each task's state over time as colored spans — far more
useful than a momentary snapshot for understanding scheduling behavior.

```bash
rtos-visualize --demo --view timeline      # live GUI
python examples/plot_timeline.py --out timeline.png   # headless PNG render
```

![Task state timeline (simulated)](docs/timeline_demo.png)

| State | Color |
|---|---|
| Running | green |
| Ready | blue |
| Blocked | orange |
| Suspended | red |

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

## Security

**The embedded target is treated as untrusted input.** Debug/trace output is
usually assumed to be benign, but buggy or compromised firmware (or a MITM on
the serial/TCP link) should never be able to harm the host that's debugging it.
The data crossing from device to host is the security boundary, and it is
hardened accordingly:

| Threat | Vector | Mitigation |
|---|---|---|
| **CSV / formula injection** (code execution when the export is opened in Excel/Sheets) | task name starting with `= + - @` | `sanitize_csv_field` prefixes `'` so the cell stays text |
| **Terminal / ANSI escape injection** (console spoofing) | ANSI escapes / control bytes in a task name | `strip_ansi` + control-char stripping at parse time |
| **Memory-exhaustion DoS** | unbounded distinct task names | `TaskStateStore(max_tasks=...)` cap |
| **Memory-exhaustion DoS** | oversized task name | name truncated to `max_name_length` |
| **Memory-exhaustion DoS** | serial line with no newline | `clamp_line` bounds bytes per read |

Every mitigation has regression tests in
[`tests/test_security.py`](tests/test_security.py) and a runnable
demonstration:

```bash
make security-demo        # watch hostile device input get neutralized
```

Tooling (see [SECURITY.md](SECURITY.md) for the full threat model and
disclosure policy):

- **Bandit** (SAST) and **pip-audit** (dependency CVEs) — `make security`, also in CI
- **CodeQL** semantic scanning (push/PR + weekly)
- **Dependabot** dependency & GitHub Actions updates

---

## Development

```bash
git clone https://github.com/hariharanragothaman/freeRTOS-visualizer.git
cd freeRTOS-visualizer

make install       # full install incl. GUI stack
# or
make install-dev   # headless: test dependencies only (no PyQt5/matplotlib)
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full contributor workflow.

### Running Tests

```bash
make test          # run the suite
make cov           # run with a terminal coverage report
make cov-html      # write an HTML coverage report to htmlcov/
```

Tests cover: serial-line parsing, state-store history tracking, CSV export, `SerialConnection` reconnect/backoff logic, malformed binary input, and end-to-end pipeline integration. Coverage is reported in CI and published to [Codecov](https://codecov.io/gh/hariharanragothaman/freeRTOS-visualizer).

---

## Project Layout

```
freertos_visualizer/
  visualize.py          # Parsing, TaskStateStore, SerialConnection, PyQt5 GUI
  simulator.py          # Headless serial simulator (TaskSimulator)
  timeline.py           # Gantt segment computation + state colors
  stats.py              # Per-task statistics (compute_summary / format_summary)
  render.py             # Shared matplotlib drawing (bar chart + timeline)
  security.py           # Untrusted-input sanitizers + resource-bound defaults
examples/
  run_demo.py           # Launch the GUI against the simulator
  print_stats.py        # Headless stats table
  plot_timeline.py      # Headless timeline PNG
  record_demo.py        # Headless animated demo GIFs
  security_demo.py      # Untrusted-input hardening demo
tests/                  # ~75 unit tests (parser, store, serial, sim, stats,
                        #   timeline, render, security); coverage to Codecov
SECURITY.md             # Threat model + disclosure policy
docs/
  demo_bar.gif          # Generated bar-chart demo
  demo_timeline.gif     # Generated timeline demo
  paper.md / paper.bib  # JOSS-style paper
.github/
  workflows/ci.yml             # CI: tests + coverage (Python 3.9–3.13)
  workflows/security.yml       # Bandit (SAST) + pip-audit (dependency CVEs)
  workflows/codeql.yml         # CodeQL semantic scanning
  workflows/build-publish.yml  # Publish to PyPI on version tags
  dependabot.yml               # Automated dependency / actions updates
```

---

## Roadmap

Tracked as GitHub issues:

- [ ] [Headless serial simulator & demo mode (#4)](https://github.com/hariharanragothaman/freeRTOS-visualizer/issues/4) — try it without hardware
- [ ] [Timestamped task-state history & enhanced CSV (#5)](https://github.com/hariharanragothaman/freeRTOS-visualizer/issues/5)
- [ ] [Task statistics summary (#6)](https://github.com/hariharanragothaman/freeRTOS-visualizer/issues/6) — time-in-state %, transitions
- [ ] [Developer tooling: coverage in CI, Makefile, CONTRIBUTING (#7)](https://github.com/hariharanragothaman/freeRTOS-visualizer/issues/7)
- [x] [Timeline / Gantt chart view (#8)](https://github.com/hariharanragothaman/freeRTOS-visualizer/issues/8)
- [ ] In-app export button / periodic autosave
- [ ] Configurable color schemes and chart types
- [ ] Support for additional FreeRTOS trace data (stack usage, CPU %)

---

## Contributing

Contributions are welcome! Please read the [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
