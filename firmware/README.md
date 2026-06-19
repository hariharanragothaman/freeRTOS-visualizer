# Firmware trace shim

The host tool consumes a line protocol, but a target has to *produce* it. This
directory ships the missing C side: a tiny, portable shim that makes any
FreeRTOS application emit exactly what `rtos-visualize` reads.

```
Task:<name>,State:<code>,Tick:<n>
```

- **State codes** mirror FreeRTOS `eTaskState` (`task.h`): `eRunning=0`,
  `eReady=1`, `eBlocked=2`, `eSuspended=3`, `eDeleted=4`, `eInvalid=5`.
- **Tick** is `xTaskGetTickCount()`, so the host keys the timeline and
  time-in-state stats off the *device* clock, not host read time.

## Files

| File | Purpose |
|------|---------|
| [`trace_shim.c`](trace_shim.c) | Snapshot + periodic trace task using `uxTaskGetSystemState` |
| [`trace_shim.h`](trace_shim.h) | Public API |

## Integrate in 3 steps

**1. Enable the trace facility** in `FreeRTOSConfig.h`:

```c
#define configUSE_TRACE_FACILITY    1   /* required by uxTaskGetSystemState */
```

**2. Provide a serial writer** for your board — point it at the same UART /
semihosting / TCP socket the visualizer connects to:

```c
#include "trace_shim.h"

void trace_serial_write(const char *line)
{
    /* Example: blocking UART puts. Use whatever your BSP provides. */
    for (const char *p = line; *p; ++p) {
        uart_putc(*p);
    }
}
```

**3. Start the trace task** after creating your application tasks:

```c
#include "trace_shim.h"

int main(void)
{
    /* ... create your tasks ... */
    trace_shim_start();          /* emits a snapshot every TRACE_PERIOD_MS */
    vTaskStartScheduler();
    for (;;) { }
}
```

Tunables (define before including / compiling):

| Macro | Default | Meaning |
|-------|---------|---------|
| `TRACE_PERIOD_MS` | `50` | Snapshot interval (≈20 Hz) |
| `TRACE_MAX_TASKS` | `16` | Max tasks captured per snapshot |

## Run it end-to-end

Once your firmware is emitting the protocol over, e.g., a QEMU serial socket:

```bash
# QEMU exposing the target UART on TCP :12345
qemu-system-arm -M mps2-an385 -kernel your_app.elf -nographic \
  -serial tcp::12345,server,nowait

# Host
rtos-visualize --serial-url socket://localhost:12345 --view timeline
```

No board yet? `rtos-visualize --demo` runs the same pipeline against the built-in
simulator (which now emits the `Tick` field too), so the host side is verifiable
without hardware.

## Notes

- FreeRTOS task names may contain spaces; the protocol name must be
  comma/whitespace-free, so the shim sanitizes names (non `[A-Za-z0-9_-]` → `_`)
  to match the host parser's anchored field.
- `uxTaskGetSystemState` walks the kernel lists with the scheduler suspended;
  keep `TRACE_PERIOD_MS` modest on busy systems.
- This shim is intentionally dependency-free and not tied to a specific port; it
  compiles against any standard FreeRTOS kernel with the trace facility enabled.
