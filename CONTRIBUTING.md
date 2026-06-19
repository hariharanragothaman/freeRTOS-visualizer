# Contributing to freeRTOS-visualizer

Thanks for your interest in improving freeRTOS-visualizer! This guide covers the
local setup, testing, and pull-request workflow.

## Development setup

```bash
git clone https://github.com/hariharanragothaman/freeRTOS-visualizer.git
cd freeRTOS-visualizer

# Full install (includes the PyQt5/matplotlib GUI stack)
make install

# Or, headless install for running tests only (no GUI dependencies)
make install-dev
```

This creates a virtual environment in `.venv/`.

## Running the tests

```bash
make test        # run the suite
make cov         # run with a terminal coverage report
make cov-html    # write an HTML report to htmlcov/
```

The core logic (parsing, the task-state store, serial reconnect, the simulator,
and statistics) is fully testable **without** a display or any hardware. GUI code
is guarded so the package imports cleanly even when PyQt5/matplotlib are absent.

## Trying it without hardware

You do not need QEMU or an embedded board to see the tool work:

```bash
make demo     # launches the GUI against the built-in serial simulator
make stats    # prints task statistics from a simulated run (headless)
```

See [`examples/`](examples/) for runnable scripts.

## Pull-request guidelines

1. Branch from `main` using a descriptive name, e.g. `feat/...` or `fix/...`.
2. Keep PRs focused and reviewable; one feature or fix per PR.
3. Add or update tests for any behavior change — coverage should not regress.
4. Update the `README.md` and `examples/` when you add user-facing features.
5. Ensure `make cov` passes locally before opening the PR.
6. Link the issue your PR closes (e.g. `Closes #5`).

## Code style

- Standard library first; keep runtime dependencies minimal.
- Keep GUI imports optional/guarded so headless environments still work.
- Prefer small, pure functions that are easy to unit test.
