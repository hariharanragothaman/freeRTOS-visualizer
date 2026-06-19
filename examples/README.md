# Examples

Runnable examples for freeRTOS-visualizer. None of these require hardware or
QEMU — they use the built-in serial simulator.

| Script | What it does |
|---|---|
| `run_demo.py` | Launches the PyQt5 GUI against the serial simulator (needs the GUI stack). |
| `print_stats.py` | Headless: simulates a run and prints per-task statistics. |
| `plot_timeline.py` | Headless: simulates a run and renders a Gantt-style timeline PNG (needs matplotlib). |
| `record_demo.py` | Headless: records animated bar-chart and timeline demo GIFs (needs matplotlib + pillow). |

## Running

```bash
# From the repo root, after `make install` (GUI) or `make install-dev` (headless)
python examples/run_demo.py
python examples/print_stats.py
```

Or via make:

```bash
make demo
make stats
```
