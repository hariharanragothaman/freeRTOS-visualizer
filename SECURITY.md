# Security Policy

## Reporting a vulnerability

Please report security issues **privately**:

- Preferred: open a [GitHub Security Advisory](https://github.com/hariharanragothaman/freeRTOS-visualizer/security/advisories/new) (private).
- Or email: **hariharanragothaman@gmail.com** with the subject `SECURITY: freeRTOS-visualizer`.

Please include a description, reproduction steps, and impact. We aim to
acknowledge reports within 5 business days. Do not open a public issue for
undisclosed vulnerabilities.

## Supported versions

The latest release on the `main` branch receives security fixes.

| Version | Supported |
|---|---|
| `main` (latest) | ✅ |
| older tags | ❌ |

---

## Threat model

freeRTOS-visualizer connects to an embedded target over a serial port or TCP
socket and parses `Task:<name>,State:<code>` lines emitted by the firmware.

**The target device is treated as untrusted.** Debug/trace output is commonly
assumed to be benign, but the device may be:

- running **buggy firmware** that emits malformed or pathological output,
- **compromised** (malicious firmware), or
- subject to a **man-in-the-middle** on the serial/TCP link.

The security boundary is therefore the data crossing from the device into the
host process. A debugging tool must not let the thing it is debugging harm the
operator's machine.

### Assets
- The host running the visualizer (process integrity, memory).
- The operator's terminal session.
- Exported artifacts (the task-history CSV) and any application that opens them.

### Threats and mitigations

| # | Threat | Vector | Mitigation | Where |
|---|--------|--------|------------|-------|
| T1 | **CSV / formula injection** → code execution in a spreadsheet (DDE) when the export is opened | A task name beginning with `=`, `+`, `-`, `@` | `sanitize_csv_field` prepends `'` so the cell is treated as text | `security.py`, `TaskStateStore.export_csv` |
| T2 | **Terminal / ANSI escape injection** → console spoofing, clearing, cursor abuse | ANSI escapes / C0 control bytes in a task name that is later printed | `strip_ansi` + control-character stripping via `sanitize_display_text` at parse time | `security.py`, `parse_serial_line` |
| T3 | **Memory exhaustion (DoS)** via unbounded distinct task names | Device emits unique names forever | `TaskStateStore(max_tasks=...)` caps tracked tasks; further unseen names are ignored | `visualize.py` |
| T4 | **Memory exhaustion (DoS)** via an oversized task name | `\S+` would match arbitrarily long input | Task names truncated to `max_name_length` | `parse_serial_line` |
| T5 | **Memory exhaustion (DoS)** via a line with no newline | A single `readline` grows without bound | `clamp_line` bounds raw bytes per read (`max_line_length`) | `SerialConnection.readline` |

All mitigations have dedicated regression tests in
[`tests/test_security.py`](tests/test_security.py) and a runnable demonstration
in [`examples/security_demo.py`](examples/security_demo.py)
(`make security-demo`).

### Out of scope
- The integrity/authenticity of the serial link itself (use a trusted physical
  connection; this tool does not authenticate the peer).
- The security of QEMU or the firmware being debugged.
- Rendering-layer robustness of third-party GUI libraries (PyQt5/matplotlib).

## Automated security checks

CI runs on every push and pull request:

- **Bandit** — static analysis of the Python source for common security issues.
- **pip-audit** — known-vulnerability (CVE) scanning of dependencies.
- **CodeQL** — semantic code scanning (also on a weekly schedule).
- **Dependabot** — automated dependency and GitHub Actions update PRs.

Run the SAST + dependency checks locally with `make security`.
