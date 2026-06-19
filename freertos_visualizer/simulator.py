"""Headless serial simulator for freeRTOS-visualizer.

Generates a realistic, deterministic stream of ``Task:<name>,State:<code>`` lines
so the tool can be demoed and tested without real hardware or QEMU.

The :class:`TaskSimulator` is a drop-in replacement for
:class:`freertos_visualizer.visualize.SerialConnection`: it exposes ``connect``,
``readline`` and ``close``, so the GUI can run against it directly.
"""

import time
import random

from freertos_visualizer.visualize import STATE_DICT

DEFAULT_TASKS = ("IDLE", "LED_Blink", "SensorRead", "NetTask", "Logger")

# Per-state transition weights over state codes 0..3
# (Running, Ready, Blocked, Suspended). Tuned so output looks plausible:
# tasks mostly cycle Running <-> Ready, occasionally Block, rarely Suspend.
_TRANSITIONS = {
    "0": {"0": 2, "1": 5, "2": 2, "3": 1},  # Running ->
    "1": {"0": 5, "1": 2, "2": 2, "3": 1},  # Ready ->
    "2": {"0": 1, "1": 5, "2": 2, "3": 1},  # Blocked ->
    "3": {"0": 1, "1": 3, "2": 1, "3": 2},  # Suspended ->
}

_STATE_CODES = tuple(STATE_DICT.keys())  # ("0", "1", "2", "3")


class TaskSimulator:
    """Produce a deterministic, realistic FreeRTOS-like task-state stream.

    Parameters
    ----------
    tasks:
        Iterable of task names to emit. Defaults to :data:`DEFAULT_TASKS`.
    seed:
        Seed for the internal PRNG. The same seed always yields the same stream.
    emit_tick:
        When ``True``, append a monotonic device tick (``,Tick:<n>``) to each
        line so timing is device-relative rather than host-read-relative.
    rate_hz:
        When set, :meth:`readline` paces output to ~``rate_hz`` lines/second so
        a live demo behaves like a real device feeding the threaded reader.
    """

    def __init__(self, tasks=DEFAULT_TASKS, seed=0, emit_tick=False, tick_step=1,
                 rate_hz=None, tick_rate_hz=None, _sleep=time.sleep):
        self.tasks = list(tasks)
        if not self.tasks:
            raise ValueError("TaskSimulator requires at least one task")
        # Non-cryptographic PRNG is intentional: this only generates synthetic
        # demo/test data, never anything security-sensitive.
        self._rng = random.Random(seed)  # nosec B311
        # Every task starts Ready ("1").
        self._current = {task: "1" for task in self.tasks}
        self._next_index = 0
        self._tick = 0
        self.emit_tick = emit_tick
        self.tick_step = tick_step
        self.rate_hz = rate_hz
        # When set (with emit_tick), the first emitted line announces TickRate so
        # the host can convert the simulated ticks into real seconds.
        self.tick_rate_hz = tick_rate_hz
        self._meta_emitted = False
        self._sleep = _sleep
        self.connected = False

    def connect(self):
        """Mark the (virtual) connection as open. Always succeeds."""
        self.connected = True

    def _advance(self, state_code):
        weights = _TRANSITIONS[state_code]
        codes = list(weights.keys())
        chosen = self._rng.choices(codes, weights=[weights[c] for c in codes], k=1)
        return chosen[0]

    def next_line(self):
        """Return the next protocol line as a string."""
        # Announce the tick rate once, before any sample, so the host learns the
        # device clock and the timeline reads in seconds.
        if self.emit_tick and self.tick_rate_hz and not self._meta_emitted:
            self._meta_emitted = True
            return f"TickRate:{self.tick_rate_hz}"

        task = self.tasks[self._next_index % len(self.tasks)]
        self._next_index += 1
        new_state = self._advance(self._current[task])
        self._current[task] = new_state
        if self.emit_tick:
            tick = self._tick
            self._tick += self.tick_step
            return f"Task:{task},State:{new_state},Tick:{tick}"
        return f"Task:{task},State:{new_state}"

    def readline(self):
        """SerialConnection-compatible alias for :meth:`next_line`."""
        if not self.connected:
            self.connect()
        if self.rate_hz:
            self._sleep(1.0 / self.rate_hz)
        return self.next_line()

    def stream(self, count):
        """Yield ``count`` simulated lines."""
        for _ in range(count):
            yield self.next_line()

    def close(self):
        """SerialConnection-compatible no-op close."""
        self.connected = False
