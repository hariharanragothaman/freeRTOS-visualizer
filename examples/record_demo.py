#!/usr/bin/env python3
"""Record end-to-end animated GIF demos of the visualizer — headless.

Drives the full pipeline (TaskSimulator -> TaskStateStore -> render) and writes
animated GIFs using matplotlib's Agg backend and PillowWriter. No display,
hardware, or QEMU required.

Examples::

    python examples/record_demo.py --mode both --out-dir docs
    python examples/record_demo.py --mode bar --frames 40 --fps 8 --out-dir docs

This is exactly what the live GUI shows; the GUI version is::

    rtos-visualize --demo                 # bar chart
    rtos-visualize --demo --view timeline # timeline
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.animation import FuncAnimation, PillowWriter  # noqa: E402

from freertos_visualizer import TaskSimulator, TaskStateStore  # noqa: E402
from freertos_visualizer.render import draw_bar_chart, draw_timeline  # noqa: E402


def _record(out_path, draw_fn, frames, fps, lines_per_frame, seed, tick):
    sim = TaskSimulator(seed=seed)
    store = TaskStateStore()
    counter = {"n": 0}

    fig, ax = plt.subplots(figsize=(8, 4.5))

    def update(_frame):
        for _ in range(lines_per_frame):
            store.ingest_line(sim.next_line(), timestamp=counter["n"] * tick)
            counter["n"] += 1
        draw_fn(ax, store)
        return []

    anim = FuncAnimation(fig, update, frames=frames, blit=False)
    anim.save(out_path, writer=PillowWriter(fps=fps))
    plt.close(fig)
    print(f"Wrote {out_path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("bar", "timeline", "both"), default="both")
    parser.add_argument("--frames", type=int, default=40, help="Number of animation frames.")
    parser.add_argument("--fps", type=int, default=8, help="GIF frames per second.")
    parser.add_argument("--seed", type=int, default=1, help="Simulator seed.")
    parser.add_argument("--tick", type=float, default=0.1, help="Simulated seconds per sample.")
    parser.add_argument("--out-dir", default="docs", help="Directory for the GIF(s).")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    if args.mode in ("bar", "both"):
        _record(
            os.path.join(args.out_dir, "demo_bar.gif"),
            draw_bar_chart,
            frames=args.frames,
            fps=args.fps,
            lines_per_frame=5,  # one update per task each frame
            seed=args.seed,
            tick=args.tick,
        )
    if args.mode in ("timeline", "both"):
        _record(
            os.path.join(args.out_dir, "demo_timeline.gif"),
            draw_timeline,
            frames=args.frames,
            fps=args.fps,
            lines_per_frame=5,
            seed=args.seed,
            tick=args.tick,
        )


if __name__ == "__main__":
    main()
