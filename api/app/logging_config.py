"""Structured JSON logging: one line per log record, easy to grep or pipe to a
log aggregator. Deliberately stdlib-only - a custom formatter is a dozen lines
and keeps the mechanism visible instead of hiding it behind a library.
"""

import json
import logging
import sys

# Fixed, documented set of attributes every LogRecord carries - anything else on
# a record came from extra={...} in a logger call and is ours to include.
_STANDARD_FIELDS = frozenset(
    {
        "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
        "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
        "created", "msecs", "relativeCreated", "thread", "threadName",
        "processName", "process", "taskName", "message",
    }
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # extra={...} passed to logger calls ends up as plain attributes on the
        # record - anything not part of the standard LogRecord fields is ours.
        for key, value in record.__dict__.items():
            if key not in _STANDARD_FIELDS:
                payload[key] = value
        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)
