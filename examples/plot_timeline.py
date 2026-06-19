#!/usr/bin/env python3
"""Headless example: render a Gantt-style task-state timeline to a PNG.

Uses matplotlib's non-interactive Agg backend, so it needs no display, no
hardware, and no QEMU. Run with::

    python examples/plot_timeline.py --out timeline.png
    # equivalent live GUI version:
    rtos-visualize --demo --view timeline
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

from freertos_visualizer import (  # noqa: E402
    STATE_COLORS,
    TaskSimulator,
    TaskStateStore,
    compute_segments,
)
from freertos_visualizer.timeline import state_color  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=120, help="Samples to simulate.")
    parser.add_argument("--seed", type=int, default=0, help="Simulator seed.")
    parser.add_argument("--tick", type=float, default=0.1, help="Simulated seconds per sample.")
    parser.add_argument("--out", default="timeline.png", help="Output PNG path.")
    args = parser.parse_args()

    sim = TaskSimulator(seed=args.seed)
    store = TaskStateStore()
    for i, line in enumerate(sim.stream(args.samples)):
        store.ingest_line(line, timestamp=i * args.tick)

    segments = compute_segments(store)
    tasks = list(segments)

    fig, ax = plt.subplots(figsize=(10, 0.6 * len(tasks) + 1.5))
    row_step, row_height = 10, 9
    for idx, task in enumerate(tasks):
        spans = segments[task]
        xranges = [(start, max(end - start, 0.0)) for (start, end, _s) in spans]
        colors = [state_color(state) for (_a, _b, state) in spans]
        ax.broken_barh(xranges, (idx * row_step, row_height), facecolors=colors)

    ax.set_yticks([idx * row_step + row_height / 2 for idx in range(len(tasks))])
    ax.set_yticklabels(tasks)
    ax.set_xlabel("Time (s)")
    ax.set_title("FreeRTOS Task State Timeline (simulated)")
    ax.legend(
        handles=[Patch(color=c, label=s) for s, c in STATE_COLORS.items()],
        loc="upper center", bbox_to_anchor=(0.5, -0.15),
        ncol=len(STATE_COLORS), fontsize="small",
    )
    fig.tight_layout()
    fig.savefig(args.out, dpi=120, bbox_inches="tight")
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
