from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from app.core.config import settings


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            'ts': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        for attr in ('request_id', 'method', 'path', 'status_code', 'duration_ms', 'client_ip', 'user_id'):
            value = getattr(record, attr, None)
            if value is not None:
                payload[attr] = value
        if record.exc_info:
            payload['exc_info'] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


class TextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        extras = []
        for label, attr in (
            ('request_id', 'request_id'),
            ('method', 'method'),
            ('path', 'path'),
            ('status', 'status_code'),
            ('duration_ms', 'duration_ms'),
            ('client_ip', 'client_ip'),
            ('user_id', 'user_id'),
        ):
            value = getattr(record, attr, None)
            if value is not None:
                extras.append(f'{label}={value}')
        suffix = f" | {' '.join(extras)}" if extras else ''
        base = f"%(asctime)s %(levelname)s [%(name)s] %(message)s"
        formatter = logging.Formatter(base + suffix)
        return formatter.format(record)


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        for attr in ('request_id', 'method', 'path', 'status_code', 'duration_ms', 'client_ip', 'user_id'):
            if not hasattr(record, attr):
                setattr(record, attr, None)
        return True


def setup_logging() -> None:
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(settings.log_level.upper())

    handler = logging.StreamHandler()
    handler.addFilter(RequestContextFilter())
    handler.setFormatter(JsonFormatter() if settings.log_json else TextFormatter())
    root.addHandler(handler)
