import os
import logging
from logging.handlers import RotatingFileHandler
from contextvars import ContextVar
from typing import Optional
from llmwiki.db.store import Store

# Context variables for tracing requests through multiple agents
trace_id: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)
task_type: ContextVar[Optional[str]] = ContextVar("task_type", default="UNKNOWN")

class SystemLogger:
    def __init__(self, vault_path: str = "vault"):
        self.vault_path = vault_path
        self.store = Store(vault_path)
        self.log_file = os.path.join(vault_path, ".llmwiki", "system.log")
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        
        # Configure rotating file handler
        self.py_logger = logging.getLogger("llmwiki")
        self.py_logger.setLevel(logging.INFO)
        if not self.py_logger.handlers:
            # Rotate at 5MB, keep 5 backups
            fh = RotatingFileHandler(self.log_file, maxBytes=5*1024*1024, backupCount=5)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(trace_id)s] [%(task_type)s] %(message)s')
            fh.setFormatter(formatter)
            self.py_logger.addHandler(fh)

    def log(self, category: str, level: str, message: str, task: str = None):
        """Logs a message to both the database and the system log file."""
        tid = trace_id.get() or "no-trace"
        t_type = task or task_type.get() or "UNKNOWN"
        
        # 1. DB Log
        self.store.add_log(category, level, message, trace_id=tid, task_type=t_type)
        
        # 2. File Log with trace info
        extra = {'trace_id': tid, 'task_type': t_type}
        log_msg = f"[{category}] {message}"
        
        if level.upper() == "INFO":
            self.py_logger.info(log_msg, extra=extra)
        elif level.upper() == "WARNING":
            self.py_logger.warning(log_msg, extra=extra)
        elif level.upper() == "ERROR":
            self.py_logger.error(log_msg, extra=extra)
        else:
            self.py_logger.debug(log_msg, extra=extra)

# Global instances
_logger_cache = {}

def get_logger(vault_path: str = "vault") -> SystemLogger:
    if vault_path not in _logger_cache:
        _logger_cache[vault_path] = SystemLogger(vault_path)
    return _logger_cache[vault_path]

def set_trace_id(tid: str):
    trace_id.set(tid)

def set_task_type(t_type: str):
    task_type.set(t_type)
