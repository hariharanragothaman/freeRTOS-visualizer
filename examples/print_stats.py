#!/usr/bin/env python3
"""Headless example: simulate a FreeRTOS run and print task statistics.

No hardware, QEMU, or GUI required. Run with::

    python examples/print_stats.py
    # or
    make stats
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from freertos_visualizer import TaskSimulator, TaskStateStore, format_summary  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=500, help="Number of samples to simulate.")
    parser.add_argument("--seed", type=int, default=0, help="Simulator seed.")
    parser.add_argument("--tick", type=float, default=0.01, help="Simulated seconds between samples.")
    args = parser.parse_args()

    sim = TaskSimulator(seed=args.seed)
    store = TaskStateStore()

    # Feed explicit, evenly spaced timestamps so the run is fully reproducible.
    for i, line in enumerate(sim.stream(args.samples)):
        store.ingest_line(line, timestamp=i * args.tick)

    print(f"Simulated {args.samples} samples (seed={args.seed}):\n")
    print(format_summary(store.summary()))


if __name__ == "__main__":
    main()
