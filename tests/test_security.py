import pytest

from freertos_visualizer.security import (
    clamp_line,
    sanitize_csv_field,
    sanitize_display_text,
    strip_ansi,
)
from freertos_visualizer.visualize import SerialConnection, TaskStateStore, parse_serial_line


# ---------------------------------------------------------------------------
# CSV / formula injection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("payload", ["=1+1", "+1", "-1", "@SUM(A1)", "=cmd|'/c calc'!A1"])
def test_sanitize_csv_field_neutralizes_formula(payload):
    out = sanitize_csv_field(payload)
    assert out.startswith("'")
    assert out[1:] == payload


def test_sanitize_csv_field_leaves_safe_values():
    assert sanitize_csv_field("LED_Blink") == "LED_Blink"
    assert sanitize_csv_field("") == ""
    assert sanitize_csv_field(5) == 5  # non-strings untouched


def test_export_csv_is_injection_safe(tmp_path):
    store = TaskStateStore()
    # A malicious device names a task with a spreadsheet formula.
    store.ingest_line("Task:=2+5,State:0", timestamp=0.0)

    out = tmp_path / "evil.csv"
    store.export_csv(str(out))
    body = out.read_text(encoding="utf-8")

    # The formula must be quoted so a spreadsheet treats it as text.
    assert "'=2+5" in body
    # And the raw, unescaped formula must not appear as a leading cell value.
    assert "\n=2+5" not in body and not body.split("\n")[1].startswith("=2+5")


# ---------------------------------------------------------------------------
# Terminal / ANSI escape injection
# ---------------------------------------------------------------------------


def test_strip_ansi_removes_color_codes():
    assert strip_ansi("\x1b[31mRED\x1b[0m") == "RED"


def test_sanitize_display_text_removes_control_chars():
    assert sanitize_display_text("ab\x07\x00cd") == "abcd"
    assert sanitize_display_text("nl\nbel\x07") == "nlbel"


def test_sanitize_display_text_truncates():
    assert sanitize_display_text("x" * 100, max_length=10) == "x" * 10


def test_parse_strips_ansi_from_task_name():
    name, state, _tick = parse_serial_line("Task:\x1b[31mEvil\x1b[0m,State:0")
    assert name == "Evil"
    assert state == "Running"


def test_parse_rejects_all_control_name():
    # A name made entirely of control bytes sanitizes to empty -> rejected.
    assert parse_serial_line("Task:\x07\x07,State:0") is None


def test_parse_bounds_task_name_length():
    long_name = "T" * 500
    name, _state, _tick = parse_serial_line(f"Task:{long_name},State:0", max_name_length=32)
    assert len(name) == 32


# ---------------------------------------------------------------------------
# Resource-exhaustion DoS
# ---------------------------------------------------------------------------


def test_store_caps_distinct_tasks():
    store = TaskStateStore(max_tasks=3)
    for i in range(10):
        store.ingest_line(f"Task:T{i},State:0", timestamp=float(i))
    assert len(store.task_states) == 3


def test_store_cap_still_updates_known_tasks():
    store = TaskStateStore(max_tasks=1)
    store.ingest_line("Task:A,State:0", timestamp=0.0)
    store.ingest_line("Task:B,State:0", timestamp=1.0)  # dropped (cap reached)
    store.ingest_line("Task:A,State:2", timestamp=2.0)  # still updates A
    assert set(store.task_states) == {"A"}
    assert store.task_states["A"] == ["Running", "Blocked"]


def test_clamp_line_bounds_length():
    assert clamp_line(b"x" * 100, 10) == b"x" * 10
    assert clamp_line("y" * 100, 10) == "y" * 10
    assert clamp_line(b"short", 10) == b"short"


def test_clamp_line_none_disables_bound():
    assert clamp_line(b"x" * 100, None) == b"x" * 100


def test_serial_connection_clamps_long_line():
    class HugePort:
        def readline(self):
            return b"Task:" + b"A" * 100000 + b",State:0\n"

        def close(self):
            pass

    conn = SerialConnection(url="fake://", max_line_length=128)
    conn._port = HugePort()
    conn.connected = True
    line = conn.readline()
    assert len(line) <= 128
