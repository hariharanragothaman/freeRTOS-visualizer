#!/usr/bin/env python3
"""End-to-end gate for the QEMU FreeRTOS trace-shim demo.

Boots the freshly built ELF in QEMU, captures the target UART, and parses every
line with the *host* code (``freertos_visualizer.parse_serial_line``). This is
the proof the reviewer asked for: working C, linked against trace_shim.c, emits
the protocol the Python tool consumes — no hand-waving, no hardware required.

Asserts:
  * multiple distinct tasks are reported (the app tasks + Trace + IDLE),
  * the device Tick advances over the run (timeline keys off device time),
  * every captured line parses cleanly.

Exit code 0 on success, 1 otherwise.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import threading
import time

# Import the host parser so we validate against the exact code the tool ships.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from freertos_visualizer.visualize import (  # noqa: E402
    STATE_DICT,
    parse_meta_line,
    parse_serial_line,
)


def _drain(stream, sink: list[str], stop: threading.Event) -> None:
    for raw in iter(stream.readline, ""):
        sink.append(raw)
        if stop.is_set():
            break


def run_qemu(elf: str, seconds: float, qemu: str) -> list[str]:
    cmd = [
        qemu,
        "-machine", "mps2-an385",
        "-cpu", "cortex-m3",
        "-kernel", elf,
        "-display", "none",
        "-monitor", "none",
        "-serial", "stdio",
    ]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )
    lines: list[str] = []
    stop = threading.Event()
    reader = threading.Thread(target=_drain, args=(proc.stdout, lines, stop), daemon=True)
    reader.start()
    try:
        time.sleep(seconds)
    finally:
        stop.set()
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
        reader.join(timeout=2)
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--elf", required=True, help="Path to the built demo ELF")
    ap.add_argument("--seconds", type=float, default=4.0, help="How long to capture")
    ap.add_argument("--qemu", default=os.environ.get("QEMU", "qemu-system-arm"))
    ap.add_argument("--min-tasks", type=int, default=3)
    args = ap.parse_args()

    qemu = shutil.which(args.qemu)
    if qemu is None:
        print(f"ERROR: '{args.qemu}' not found on PATH", file=sys.stderr)
        return 1
    if not os.path.exists(args.elf):
        print(f"ERROR: ELF not found: {args.elf}", file=sys.stderr)
        return 1

    print(f"Booting {args.elf} in QEMU for {args.seconds:g}s ...")
    raw_lines = run_qemu(args.elf, args.seconds, qemu)

    parsed = []
    bad = 0
    meta = {}
    for raw in raw_lines:
        line = raw.strip()
        if not line:
            continue
        m = parse_meta_line(line)
        if m is not None:
            meta.update(m)
            continue
        result = parse_serial_line(line)
        if result is None:
            bad += 1
            continue
        name, state, tick = result
        parsed.append((name, state, tick))

    tasks = sorted({name for name, _, _ in parsed})
    ticks = [t for _, _, t in parsed if t is not None]
    states = sorted({STATE_DICT.get(s, s) for _, s, _ in parsed})

    print(f"\nCaptured {len(raw_lines)} UART lines, {len(parsed)} parsed, "
          f"{bad} unparseable.")
    print(f"Tasks   ({len(tasks)}): {', '.join(tasks) if tasks else '<none>'}")
    print(f"States  : {', '.join(states) if states else '<none>'}")
    if ticks:
        print(f"Tick    : {min(ticks)} -> {max(ticks)} (device clock)")
    rate = meta.get("tick_rate_hz")
    bits = meta.get("tick_bits")
    print(f"Meta    : TickRate={rate} Hz, TickBits={bits}")
    if rate:
        print(f"Seconds : {min(ticks) / rate:.3f} -> {max(ticks) / rate:.3f} s "
              f"(host converts ticks via TickRate)")

    ok = True
    if len(parsed) == 0:
        print("FAIL: no protocol lines parsed from the target", file=sys.stderr)
        ok = False
    if len(tasks) < args.min_tasks:
        print(f"FAIL: expected >= {args.min_tasks} tasks, saw {len(tasks)}",
              file=sys.stderr)
        ok = False
    if len(ticks) < 2 or max(ticks) <= min(ticks):
        print("FAIL: device Tick did not advance", file=sys.stderr)
        ok = False
    if bad > 0:
        print(f"FAIL: {bad} lines did not match the host parser", file=sys.stderr)
        ok = False
    if not meta.get("tick_rate_hz"):
        print("FAIL: device never announced TickRate (timeline can't show seconds)",
              file=sys.stderr)
        ok = False

    print("\nPASS: trace_shim.c emits the protocol and the host parser accepts it."
          if ok else "\nRESULT: FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
