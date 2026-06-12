"""Structured logging configuration with correlation ID support"""

import logging
import sys
import time
from typing import Any, Optional
from contextvars import ContextVar

# Context variable for correlation ID (request tracing)
correlation_id: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


class CorrelationIdFilter(logging.Filter):
    """Inject correlation ID into log records"""

    def filter(self, record: logging.LogRecord) -> bool:
        cid = correlation_id.get()
        record.correlation_id = cid or "-"
        return True


class JsonFormatter(logging.Formatter):
    """JSON structured log formatter for production environments"""

    def format(self, record: logging.LogRecord) -> str:
        import json

        log_obj = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", "-"),
        }

        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        # Add any extra fields
        for key, value in record.__dict__.items():
            if key not in {
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "exc_info", "exc_text", "stack_info",
                "lineno", "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process",
                "message", "asctime", "correlation_id",
            }:
                log_obj[key] = value

        return json.dumps(log_obj, default=str, ensure_ascii=False)


# Setup basic logging
def setup_logging(json_format: bool = False):
    """Setup logging configuration

    Args:
        json_format: If True, output structured JSON logs (recommended for production)
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(CorrelationIdFilter())

    if json_format:
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(correlation_id)s %(name)s: %(message)s"
        )

    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = []
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    # Reduce noise from third-party libraries
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def set_correlation_id(cid: str):
    """Set correlation ID for current context"""
    correlation_id.set(cid)


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID"""
    return correlation_id.get()


def clear_correlation_id():
    """Clear correlation ID from current context"""
    correlation_id.set(None)


# Audit logger
class AuditLogger:
    """Audit logger for security and access events"""

    def log_security(self, event: str, severity: str = "info", details: Any = None):
        """Log security event"""
        cid = get_correlation_id()
        logging.info(
            "Audit [%s]: %s - %s",
            severity,
            event,
            details,
            extra={"correlation_id": cid, "event_type": "security", "severity": severity}
        )

    def log_access(self, user_id: str, resource: str, action: str, success: bool = True):
        """Log access event"""
        cid = get_correlation_id()
        logging.info(
            "Access: %s %s %s - %s",
            user_id,
            action,
            resource,
            "success" if success else "failed",
            extra={
                "correlation_id": cid,
                "event_type": "access",
                "user_id": user_id,
                "resource": resource,
                "action": action,
                "success": success,
            }
        )


# Global audit instance
audit = AuditLogger()
