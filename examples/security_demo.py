#!/usr/bin/env python3
"""Demonstrate how the visualizer hardens against a hostile/compromised target.

Treats the embedded device's serial output as UNTRUSTED input and shows the
mitigations in action — no hardware required. Run with::

    python examples/security_demo.py
    # or
    make security-demo
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from freertos_visualizer import TaskStateStore, parse_serial_line  # noqa: E402

# Lines a malicious or buggy firmware might emit over the debug serial link.
HOSTILE_LINES = [
    # 1. Spreadsheet formula injection (executes when CSV opened in Excel).
    r"Task:=cmd|'/c calc'!A1,State:0",
    # 2. ANSI / terminal escape injection (rewrites the operator's console).
    "Task:\x1b[31m\x1b[2JPwned\x07,State:1",
    # 3. Oversized task name (memory pressure).
    "Task:" + "A" * 5000 + ",State:2",
    # 4. A perfectly normal line, for contrast.
    "Task:LED_Blink,State:0",
]


def main():
    print("=" * 72)
    print("Untrusted-input hardening demo  (device output is NOT trusted)")
    print("=" * 72)

    print("\n[1] Parsing / sanitization of task names\n")
    for raw in HOSTILE_LINES:
        parsed = parse_serial_line(raw)
        shown_raw = raw if len(raw) < 60 else raw[:57] + "..."
        # repr() so escape sequences in this script's own output are inert.
        print(f"  raw : {shown_raw!r}")
        print(f"  safe: {parsed!r}\n")

    print("[2] Resource cap: a flood of unique task names cannot exhaust memory\n")
    store = TaskStateStore(max_tasks=8)
    for i in range(10_000):
        store.ingest_line(f"Task:Flood{i},State:0", timestamp=float(i))
    print(f"  10,000 unique task names sent -> {len(store.task_states)} tracked "
          f"(cap = {store.max_tasks})\n")

    print("[3] CSV export neutralizes formula injection\n")
    store2 = TaskStateStore()
    store2.ingest_line(r"Task:=2+5,State:0", timestamp=0.0)
    with tempfile.NamedTemporaryFile("w+", suffix=".csv", delete=False) as tmp:
        path = tmp.name
    store2.export_csv(path)
    with open(path, encoding="utf-8") as fh:
        rows = fh.read().strip().splitlines()
    os.unlink(path)
    print(f"  header: {rows[0]}")
    print(f"  row   : {rows[1]}   <- leading quote keeps it inert text\n")

    print("=" * 72)
    print("All hostile inputs were neutralized before reaching storage, the")
    print("console, or the exported file.")
    print("=" * 72)


if __name__ == "__main__":
    main()
