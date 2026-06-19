# QEMU FreeRTOS demo — `trace_shim.c` end-to-end

This is the missing proof for the firmware side: a **runnable** FreeRTOS image
that links the real [`trace_shim.c`](../trace_shim.c), runs on an emulated
Cortex-M3, and emits the host protocol over a UART — no physical board required.

It exists to answer one question directly: *does the shim actually produce what
the Python visualizer consumes?* You can build it and check in ~10 seconds.

```
Task:Trace,State:0,Tick:100
Task:IDLE,State:1,Tick:100
Task:LED_Blink,State:2,Tick:100
Task:SensorRead,State:2,Tick:100
Task:Maintenance,State:3,Tick:100
Task:Worker,State:2,Tick:100
```

(Real UART output, captured from QEMU. `State` follows FreeRTOS `eTaskState`;
`Tick` is the device's `xTaskGetTickCount()`.)

## Requirements

| Tool | Install (macOS) | Install (Debian/Ubuntu) |
|------|-----------------|--------------------------|
| ARM GCC | `brew install --cask gcc-arm-embedded` | `apt-get install gcc-arm-none-eabi` |
| QEMU (ARM) | `brew install qemu` | `apt-get install qemu-system-arm` |
| Python 3 | (system) | (system) |

## Quick start

```bash
cd firmware/qemu-demo

make verify   # build + boot in QEMU + assert the host parser accepts the output
make run      # stream the protocol live to your terminal (quit with Ctrl-A then X)
```

`make` fetches a pinned FreeRTOS-Kernel (`V11.1.0`) on first build; it is not
vendored into the repo.

Expected `make verify` result:

```
Captured 378 UART lines, 378 parsed, 0 unparseable.
Tasks   (6): IDLE, LED_Blink, Maintenance, SensorRead, Trace, Worker
States  : Blocked, Ready, Running, Suspended
Tick    : 1 -> 3100 (device clock)

PASS: trace_shim.c emits the protocol and the host parser accepts it.
```

## Drive the real visualizer against it

`make socket` exposes the target UART on TCP `:12345`, which is exactly what the
host tool's `socket://` URL connects to:

```bash
# Terminal 1 — emulated target
make socket

# Terminal 2 — host visualizer (needs the [gui] extra)
rtos-visualize --serial-url socket://localhost:12345 --view timeline
```

## What's here

| File | Role |
|------|------|
| [`main.c`](main.c) | App tasks (LED/sensor/worker/maintenance) + `trace_shim_start()` |
| [`uart.c`](uart.c) | CMSDK UART driver = the board's `trace_serial_write()` |
| [`startup.c`](startup.c) | Cortex-M3 vector table, reset/`.data`/`.bss` init, FreeRTOS handlers |
| [`FreeRTOSConfig.h`](FreeRTOSConfig.h) | CM3 config (`configUSE_TRACE_FACILITY=1`, etc.) |
| [`mps2_m3.ld`](mps2_m3.ld) | Linker script for QEMU `mps2-an385` |
| [`Makefile`](Makefile) | Fetch kernel, cross-compile, run/verify |
| [`verify_qemu.py`](verify_qemu.py) | Headless gate: boots QEMU, parses UART with the *host* code |

The demo links `../trace_shim.c` unmodified — only the board glue
(`trace_serial_write`, startup, linker, config) lives here, which is the
porting work any integrator does.

## How it maps to a real board

| Demo (QEMU mps2-an385) | Your hardware |
|------------------------|---------------|
| CMSDK UART0 @ `0x40004000` | Your MCU's UART/USB-CDC peripheral |
| `qemu ... -serial tcp::12345` | A USB-serial bridge enumerated as `/dev/tty*` |
| `socket://localhost:12345` | `--serial-url /dev/ttyUSB0` (or `COMx`) |

Everything above the transport — the shim, the protocol, the host parser — is
identical.

## Notes / gotchas (the demo surfaced these)

- **Trace-task stack:** `trace_shim_start()` creates its task with
  `configMINIMAL_STACK_SIZE * 2`, and `trace_emit_snapshot()` puts a
  `TRACE_MAX_TASKS`-entry `TaskStatus_t` array **and** the line buffer on that
  stack. With a too-small `configMINIMAL_STACK_SIZE` the first snapshot
  overflows and silently corrupts a task name. This demo sets
  `configMINIMAL_STACK_SIZE = 256` and turns on
  `configCHECK_FOR_STACK_OVERFLOW` so the failure is loud, not silent. Size the
  trace task for your `TRACE_MAX_TASKS`.
- QEMU's SysTick is driven from `configCPU_CLOCK_HZ`; wall-clock speed differs
  from real silicon, but tick *ordering* and state transitions are faithful.
