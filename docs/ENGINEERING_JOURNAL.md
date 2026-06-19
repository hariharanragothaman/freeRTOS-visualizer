# Engineering Journal

A running log of significant design decisions, external reviews, and how we
responded to them. The intent is to be honest about what was wrong, why, and
what we changed — not to market the project.

---

## 2026-06 — External engineering/security review

An external reviewer read the full source (not just the README) and gave a
detailed, severity-ordered critique. The headline finding was correct and
important: **the tool was not actually real-time**, and the demo/simulator path
hid the flaw. We took the review seriously, filed an issue per point, and began
working through them.

### Triage: one issue per finding

| # | Finding | Severity | Status |
|---|---------|----------|--------|
| [#18](https://github.com/hariharanragothaman/freeRTOS-visualizer/issues/18) | Reads one line per repaint tick → drains port at paint rate, drops samples | High | Fixed |
| [#19](https://github.com/hariharanragothaman/freeRTOS-visualizer/issues/19) | Timestamps come from host read time, not device | High | Fixed (protocol + ingest) |
| [#20](https://github.com/hariharanragothaman/freeRTOS-visualizer/issues/20) | Packaging: setuptools backend but poetry-only metadata; deps duplicated | High | Fixed |
| [#21](https://github.com/hariharanragothaman/freeRTOS-visualizer/issues/21) | No integration test for the serial-timing path (where the bug lives) | High | Fixed |
| [#22](https://github.com/hariharanragothaman/freeRTOS-visualizer/issues/22) | Ships zero firmware; no trace shim to produce the protocol | Medium | Fixed |
| [#23](https://github.com/hariharanragothaman/freeRTOS-visualizer/issues/23) | `eDeleted (4)` / `eInvalid (5)` collapse to "Unknown" | Low | Fixed |
| [#24](https://github.com/hariharanragothaman/freeRTOS-visualizer/issues/24) | Bar-chart y-axis magnitude is semantically empty | Low | Tracked |
| [#25](https://github.com/hariharanragothaman/freeRTOS-visualizer/issues/25) | `compute_segments` rebuilds full history every tick | Low | Tracked |
| [#26](https://github.com/hariharanragothaman/freeRTOS-visualizer/issues/26) | Two clock-injection conventions | Low | Fixed |
| [#27](https://github.com/hariharanragothaman/freeRTOS-visualizer/issues/27) | `Task:(\S+)` swallows commas | Low | Fixed |
| [#28](https://github.com/hariharanragothaman/freeRTOS-visualizer/issues/28) | No-op `connect()` wrapper + premature `state_dict` alias | Low | Fixed |

### The big one (#18): ingest rate was fused to paint rate

The original `TaskVisualization.update_task_states` read exactly **one**
`serial_conn.readline()` per `QTimer` tick (default 1000 ms). So no matter how
fast the device emitted, we consumed ~1 line/second; the OS serial buffer backed
up and overflowed, silently dropping samples. The simulator hid this because it
synthesised a line per call on demand, so tests and GIFs looked perfect while
the hardware path was broken.

**Fix.** Introduced `freertos_visualizer/reader.py::SerialReader`: a dedicated
thread that continuously drains the connection into a bounded `queue.Queue`. The
GUI timer now drains *everything available* each repaint and only the *render*
is throttled by `--refresh-ms`. Ingest rate and paint rate are decoupled.

Crucially, the simulator now optionally **paces** itself (`rate_hz`) and the
demo runs through the *same* `SerialReader` pipeline as hardware — so the demo
can no longer mask a broken ingest path.

### The credibility one (#19): wrong clock

Ingest timestamps came from `time.time()` at the moment Python read the line —
i.e. host read-scheduling, not when the transition happened on the device. The
Gantt axis and `stats.py` percentages were therefore measuring the wrong thing.

**Fix.** Extended the protocol with an optional device tick:
`Task:<name>,State:<code>,Tick:<n>`. When present, `TaskStateStore` keys the
timestamp off the device tick instead of the host clock (explicit timestamps
still win, for tests). The simulator emits ticks in demo mode.

### The test that's worth more than the rest (#21)

Added `tests/test_integration_loopback.py`: it stands up a real TCP server,
connects a `SerialConnection` over pyserial's `socket://`, bursts 2000 lines
through `SerialReader` → `TaskStateStore`, and asserts **zero** dropped lines.
This exercises the exact path that unit tests and the GUI's `pragma: no cover`
never touched, and it would have caught #18.

### Correctness clean-ups

- **#23** `STATE_DICT` now includes `Deleted (4)` and `Invalid (5)`, with
  distinct timeline colours.
- **#27** task-name group anchored to `[^,\s]+` so it can no longer swallow
  commas into following fields.
- **#26** `SerialConnection` now takes `clock` (a callable) — the same
  convention as `TaskStateStore` — instead of a module called as `_clock.time()`.
- **#28** removed the no-op `connect()` try/except wrapper and the premature
  `state_dict` backwards-compat alias.

### Packaging (#20)

`pyproject.toml` declared a setuptools backend but put all metadata under
`[tool.poetry]`, so a clean `pip install .` against the declared backend got no
deps, no entry point, and no version. Migrated to a single coherent setup: a
PEP 621 `[project]` table on the setuptools backend, with `gui` / `dev`
optional-dependency extras. Deps now live in **one** place — `requirements.txt`
and CI both install from the package (`-e .[gui,dev]` / `pip install .[dev]`),
which also makes CI validate that the packaging resolves.

### Firmware trace shim (#22)

The repo was named freeRTOS-visualizer but shipped zero C, and the README's
QEMU command assumed an `RTOSDemo.axf` that emits the protocol but doesn't exist
here. Added [`firmware/`](../firmware/): a portable, dependency-free
`trace_shim.c`/`.h` that uses `uxTaskGetSystemState` to print
`Task:<name>,State:<code>,Tick:<n>` for every task (sanitizing names to the
comma/whitespace-free field the host parser expects, and using the device tick).
A `firmware/README.md` documents the 3-step integration. This closes the biggest
onboarding gap and makes the tool demonstrably end-to-end.

### Deferred (tracked, not yet done)

- **#24 bar-chart semantics** and **#25 timeline segment caching** are filed and
  scheduled as follow-up work.

### What the reviewer said was good (kept)

Clean module decomposition (parse / store / serial / reader / render / timeline
/ stats), lazy PyQt/matplotlib imports so headless CI runs core logic, the
simulator-as-drop-in `SerialConnection` (duck typing), backoff reconnect, CSV
export, and the 3.9–3.13 matrix. None of these were disturbed by the fixes.
