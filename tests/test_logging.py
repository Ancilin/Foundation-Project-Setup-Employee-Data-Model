"""Tests for structured JSON logging (Task 18)."""

import json
import logging
from app.core.logging import JSONFormatter


def test_json_formatter_outputs_valid_json():
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="ledgerforge.test",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Test message for structured logging",
        args=(),
        exc_info=None,
    )
    record.custom_field = "custom_value"
    record.duration_ms = 45.2

    output = formatter.format(record)
    parsed = json.loads(output)

    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "ledgerforge.test"
    assert parsed["message"] == "Test message for structured logging"
    assert parsed["custom_field"] == "custom_value"
    assert parsed["duration_ms"] == 45.2
    assert "timestamp" in parsed
