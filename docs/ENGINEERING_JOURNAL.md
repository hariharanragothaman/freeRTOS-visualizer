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
| [#24](https://github.com/hariharanragothaman/freeRTOS-visualizer/issues/24) | Bar-chart y-axis magnitude is semantically empty | Low | Fixed |
| [#25](https://github.com/hariharanragothaman/freeRTOS-visualizer/issues/25) | `compute_segments` rebuilds full history every tick | Low | Fixed |
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

Added `tests/test_integration_pipeline.py`: it bursts 2000 lines through the real
`SerialConnection` → `SerialReader` → `TaskStateStore` path and asserts **zero**
dropped lines (every device tick present exactly once). It exercises the exact
path unit tests and the GUI's `pragma: no cover` never touched, and would have
caught #18.

We first wrote this over a real TCP `socket://` loopback, but that proved
non-deterministic in CI (see the post-merge note below) because the framing
depended on pyserial's socket read timing. The final test delivers the bytes in
adversarial, randomly-sized chunks that split lines mid-field and coalesce
several per read — a *stronger* drop/corruption check than a clean loopback, and
fully deterministic.

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
onboarding gap and makes the tool demonstrably end-to-end. (Follow-up: a
runnable QEMU image that links this shim now proves it — see "Closing the
firmware gap" below.)

### Rendering polish (#24, #25)

- **#24** The bar chart encoded state as bar *height* (`index+1`), implying
  Suspended (4) was "more" than Running (1) — meaningless for a categorical
  value. Replaced with an equal-height **status strip**: one coloured cell per
  task with the state name as a label. Colour + label carry the meaning; the
  misleading magnitude axis is gone.
- **#25** `compute_segments` rebuilt every task's full history each repaint
  (O(total) per frame). Added `SegmentCache`, which keeps a per-task running span
  and only appends new samples, falling back to a full rebuild for a task whose
  history was trimmed by `max_history`. Output is identical to
  `compute_segments` (verified incrementally in tests); the GUI now uses it.

### Everything from the review is now addressed

All eleven findings (#18–#28) are implemented. The deferred list is empty.

### Post-merge: the integration test caught a real bug (as intended)

Right after merging, the integration test (#21), then written over a real TCP
`socket://` loopback, failed on slow CI runners — non-deterministically, 1–3 of
2000 lines "dropped". Investigation showed pyserial's `readline()` returns a
**partial line** when its read timeout fires mid-line (normal on a real UART or
a loaded host), and we were treating that fragment as a whole line — corrupting
it and the next.

Two fixes came out of this:

1. **Real robustness fix:** `SerialConnection` now reassembles bytes on newline
   boundaries (buffer the partial, only emit complete lines, still bounded by
   `max_line_length`), with unit tests for fragmentation and multi-line chunks.
   This matters for real hardware, not just CI.
2. **Deterministic test:** the socket loopback itself was still flaky because the
   outcome depended on pyserial's socket read timing — a third-party transport
   detail, not our code. Replaced it with an in-process burst that drives the
   same `SerialConnection`/`SerialReader`/store with adversarial fragmentation,
   so the test is deterministic *and* a stronger framing check.

This is exactly the class of real-hardware bug the reviewer said an integration
test would be "worth more than the rest combined" for — and it was.

### Closing the firmware gap: a runnable QEMU demo (#22 follow-up)

The reviewer's standing objection was fair: a `trace_shim.c` that nobody had
*run* is unverified C. So [`firmware/qemu-demo/`](../firmware/qemu-demo/) now
links that exact shim into a FreeRTOS image for QEMU's `mps2-an385` (Cortex-M3)
and boots it:

- Board glue only — `uart.c` (CMSDK UART = `trace_serial_write`), `startup.c`
  (vector table → FreeRTOS `vPort*`/`xPort*` handlers), `mps2_m3.ld`,
  `FreeRTOSConfig.h`. The shim itself is compiled unmodified from `../trace_shim.c`.
- `make verify` boots the ELF headless and pipes the captured UART through the
  **host** `parse_serial_line` — the same code the GUI uses — asserting multiple
  tasks, advancing device ticks, and zero unparseable lines. A new
  `.github/workflows/firmware.yml` runs this on every push, so the firmware claim
  is continuously verified by CI, not just by me once.

**The demo immediately earned its keep.** The first boot emitted exactly one
snapshot and then froze, with one task name corrupted to `__`. Root cause:
`trace_emit_snapshot()` puts a `TRACE_MAX_TASKS`-entry `TaskStatus_t` array
*and* the line buffer on the trace task's stack, but `trace_shim_start()` only
requests `configMINIMAL_STACK_SIZE * 2`. With a small `configMINIMAL_STACK_SIZE`
that's a stack overflow on the first call — silent memory corruption. Fixes:
sized `configMINIMAL_STACK_SIZE` for the array, turned on
`configCHECK_FOR_STACK_OVERFLOW` with a hook that reports the failure over the
same UART, and documented the trace-task stack sizing as a porting note. After
that, a 4-second run yields ~380 lines, 6 tasks across Running/Ready/Blocked/
Suspended, ticks advancing 1 → 3100 — over both `-serial stdio` and the
documented `socket://` TCP transport.

### Restoring the `socket://` loopback test — and proving it cross-platform

The reviewer specifically wanted the *real* socket transport under test, not
just the in-process fragmentation test. I'd deleted the original socket loopback
because it was flaky on CI; the right answer was to understand *why* and fix it
properly rather than avoid it.

Investigation (with evidence, not guesses):

- The in-process pipeline never drops: 40/40 in-process runs delivered all 2000
  lines in ~0.13 s each. So the framing/reassembly/queue code is correct.
- The real `socket://` path flaked at ~1–4%. Instrumenting the failures showed
  the signature `ticks=0/2000 connects=1 reconnects=0` — i.e. the client
  connected once and received **nothing**, with zero drops and zero reconnects.
  That is a connected-but-no-data race at TCP *connection setup* (hammering
  loopback connect/accept on ephemeral ports), **not** a dropped line. TCP is
  reliable: once bytes flow, they all arrive and our reassembly delivers them.
- To answer "is this a macOS-only artifact?", I ran it on Linux in Docker
  (`python:3.12-slim`). Same class of failure (~1/100), so it's inherent to the
  socket setup, not the host OS.

Fix: the restored test separates the two concerns it had been conflating. It
retries **connection establishment**, but on any attempt where data actually
flows it requires an exact, lossless count and `reader.dropped == 0`. A partial
delivery or any drop fails immediately and is never retried — only a no-data
connection is retried. A dropped *connection* is not a dropped *line*.

Attestation of the fix (Docker, Linux + local macOS):

| Harness | Platform | Runs | Failures |
|---------|----------|------|----------|
| raw pipeline, 1 connection | Linux | 100 | 1 (the `ticks=0` race) |
| raw pipeline, +4 conn retries | Linux | 150 | 0 |
| pytest test (retry wrapper) | Linux (Docker) | 60 | 0 |
| pytest test (retry wrapper) | macOS | 40 | 0 |

So both the genuine `socket://` transport *and* the deterministic in-process
fragmentation test now guard the no-dropped-lines property, and neither is flaky.

## Round 2 review: the device-tick semantics I'd just added were lying differently

The reviewer read the actual diffs and found that the device-tick change — the
half meant to stop the timeline from lying about *time* — introduced a new way to
lie. Four findings (#44–#47), all fixed in `fix/device-tick-semantics`.

### #44 — "Time (s)" axis was actually plotting raw ticks

`ingest_line` stored `float(tick)` and `render.py` labeled the x-axis
`"Time (s)"`, but a tick is a *count*. At `configTICK_RATE_HZ=1000` the journal's
own "1 → 3751 over ~4 s" meant the axis read 0–3751 for a 3.75 s capture — off by
1000×. The host can't fix this alone because the rate isn't in the protocol.

Decision (the reviewer asked me to state it): **add the rate to the protocol**
rather than just relabel. The device now announces `TickRate:<hz>` (and
`TickBits:<n>`) as out-of-band metadata; the store converts ticks→seconds via
`time_scale` and the timeline labels `"Time (s)"`. **When no rate has been
announced, the axis honestly reads `"Device ticks"`** instead of claiming
seconds. End-to-end proof: the QEMU demo now emits `TickRate:1000` and
`make verify` reports `Seconds: 0.001 -> 3.050 s` for the same run that used to
read "3050 ticks."

### #45 — tick wraparound, hidden by the render clamp

`TickType_t` wraps (~49.7 days for 32-bit at 1 kHz; every ~65.5 s for
`configUSE_16_BIT_TICKS`). On wrap the stored timestamp jumped backward;
`_segments_for` produced `end < start`, and `render.py`'s `max(end-start, 0)`
silently collapsed the segment to zero width — "looks fine, is wrong." Stats'
`total_time` could go negative and poison every percentage.

Fix at the source: `ingest_line` unwraps via `_unwrap_tick` — any strict
decrease is a wrap (device ticks are non-decreasing between snapshots), so it
accumulates one `tick_bits`-wide modulus into a 64-bit offset. `TickBits` makes
16- and 32-bit counters both unwrap correctly. Tested past the boundary with an
8-bit counter (`tick_bits=8`, ticks `250,255,2,10,255,0,5` → monotonic
`250…517`).

### #46 — optional `Tick` invited mixed clock domains

The grammar made `Tick` optional and `ingest_line` chose per line (tick, else
host epoch seconds ~1.7×10⁹). A stream that ever mixed the two would interleave
~10³ and ~10⁹ in one history. Fix: the store **locks the clock domain on the
first sample**; a later line whose domain disagrees is rejected, not stored.

### #47 — the socket test's `dropped == 0` was vacuous

Fair hit: queue 100k, burst 2k, no render competing — drops were impossible by
construction, so the `queue.Full`/`dropped` path was never exercised. Added
`tests/test_backpressure.py`: a `max_queue=10` reader with a 5000-line sustained
source that saturates the queue, asserting the real accounting
`dropped == sent - delivered` (and `dropped > 0`). The companion test confirms
zero drops when the queue is large enough.

### What the reviewer said was good (kept)

Clean module decomposition (parse / store / serial / reader / render / timeline
/ stats), lazy PyQt/matplotlib imports so headless CI runs core logic, the
simulator-as-drop-in `SerialConnection` (duck typing), backoff reconnect, CSV
export, and the 3.9–3.13 matrix. None of these were disturbed by the fixes.
