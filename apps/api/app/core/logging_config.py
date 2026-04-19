"""Logging configuration"""

import logging
from typing import Any

# Setup basic logging
def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )


# Audit logger stub
class AuditLogger:
    """Audit logger stub"""
    def log_security(self, event: str, severity: str = "info", details: Any = None):
        """Log security event"""
        logging.info(f"Audit [{severity}]: {event} - {details}")

    def log_access(self, user_id: str, resource: str, action: str, success: bool = True):
        """Log access event"""
        logging.info(f"Access: {user_id} {action} {resource} - {'success' if success else 'failed'}")


# Global audit instance
audit = AuditLogger()
