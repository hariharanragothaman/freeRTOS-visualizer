"""Security helpers for handling untrusted device input.

The visualizer consumes ``Task:<name>,State:<code>`` data from an embedded
target over serial/TCP. That target is **untrusted** — buggy or compromised
firmware (or a man-in-the-middle on the link) must not be able to harm the host
running this tool. These helpers neutralize the concrete risks that arise when
device-supplied strings cross a trust boundary:

* **CSV / formula injection** — when exported data is opened in a spreadsheet.
* **Terminal / ANSI escape injection** — when names are printed to a console.
* **Resource exhaustion** — via unbounded name/line lengths and task counts.

The module depends only on the standard library so it can be imported and
audited in isolation.
"""

import re

# Defaults chosen to be comfortably larger than any realistic FreeRTOS
# configMAX_TASK_NAME_LEN while still bounding memory against a hostile device.
DEFAULT_MAX_NAME_LENGTH = 64
DEFAULT_MAX_LINE_LENGTH = 4096
DEFAULT_MAX_TASKS = 256

# Leading characters that cause a spreadsheet to treat a cell as a formula.
# See OWASP "CSV Injection". TAB and CR are included because some apps strip
# them and then evaluate the following formula character.
_CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")

# CSI/escape sequences (e.g. "\x1b[31m") and standalone C1-style escapes.
_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b[@-Z\\-_]")

# All C0 control characters plus DEL. Task names are single tokens, so there is
# never a legitimate reason for them to contain control characters.
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")


def strip_ansi(text):
    """Remove ANSI escape sequences from ``text``."""
    return _ANSI_RE.sub("", text)


def sanitize_display_text(text, max_length=DEFAULT_MAX_NAME_LENGTH):
    """Make untrusted ``text`` safe to print or render.

    Strips ANSI escape sequences and control characters, then truncates to
    ``max_length`` (pass ``None`` to disable truncation).
    """
    text = strip_ansi(text)
    text = _CONTROL_RE.sub("", text)
    if max_length is not None and len(text) > max_length:
        text = text[:max_length]
    return text


def sanitize_csv_field(value):
    """Neutralize spreadsheet formula injection for a CSV cell.

    If ``value`` is a string beginning with a formula-trigger character, a
    single quote is prepended so spreadsheet apps treat it as text. Non-string
    values (e.g. numbers) are returned unchanged.
    """
    if isinstance(value, str) and value and value[0] in _CSV_FORMULA_PREFIXES:
        return "'" + value
    return value


def clamp_line(raw, max_line_length=DEFAULT_MAX_LINE_LENGTH):
    """Bound the length of a raw serial line (``bytes`` or ``str``).

    Protects against a device that never emits a newline, which would otherwise
    let a single ``readline`` grow without limit.
    """
    if max_line_length is None:
        return raw
    return raw[:max_line_length]
