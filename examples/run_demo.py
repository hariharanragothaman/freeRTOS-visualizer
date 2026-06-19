#!/usr/bin/env python3
"""Launch the freeRTOS-visualizer GUI against the built-in serial simulator.

No hardware or QEMU required. Equivalent to::

    python -m freertos_visualizer.visualize --demo

Run with::

    python examples/run_demo.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from freertos_visualizer.visualize import main  # noqa: E402

if __name__ == "__main__":
    # Inject the --demo flag and hand off to the normal entry point.
    if "--demo" not in sys.argv:
        sys.argv.append("--demo")
    main()
