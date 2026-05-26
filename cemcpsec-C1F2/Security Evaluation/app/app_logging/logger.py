"""
Logging Configuration for MCP Code Execution

Centralizes ALL logs into ONE file: logs/app.log
"""
import logging
from pathlib import Path


# Create logs directory if it doesn't exist
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

# Single log file for entire application
LOG_FILE = LOGS_DIR / "app.log"

# Global flag to ensure handlers are added only once
_handlers_configured = False


def setup_logger(name: str = __name__) -> logging.Logger:
    """
    Setup and return a logger that writes to ONE shared log file
    
    Args:
        name: Logger name (usually __name__ from the calling module)
    
    Returns:
        Configured logger instance (all loggers share same handlers)
    """
    global _handlers_configured
    
    # Get logger for this module
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Configure root logger handlers only once
    if not _handlers_configured:
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        
        # Clear any existing handlers
        root_logger.handlers.clear()
        
        # Remove noisy third-party loggers
        logging.getLogger("watchfiles.main").setLevel(logging.WARNING)
        logging.getLogger("watchfiles").setLevel(logging.WARNING)
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        
        # Create formatters
        # Clean format for file - just the message
        file_formatter = logging.Formatter('%(message)s')
        
        # Console also clean - just the message
        console_formatter = logging.Formatter('%(message)s')
        
        # File handler - ALL logs go to ONE file
        file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
        
        
        _handlers_configured = True
    
    return logger

