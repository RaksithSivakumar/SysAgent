import os
import json
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)

def setup_logger(level_name: str = "INFO") -> logging.Logger:
    """Configures and returns the sysagent root logger."""
    logger = logging.getLogger("sysagent")
    
    # Avoid duplicate handlers if already configured
    if logger.handlers:
        return logger

    # Resolve log file path
    home = os.path.expanduser("~")
    sysagent_dir = os.path.join(home, ".sysagent")
    os.makedirs(sysagent_dir, exist_ok=True)
    log_file = os.path.join(sysagent_dir, "sysagent.log")

    level = getattr(logging, level_name.upper(), logging.INFO)
    logger.setLevel(level)

    # Rotating handler: 5MB, keep 3 backups
    handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    
    return logger
