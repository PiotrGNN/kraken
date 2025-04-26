"""
DeepAgent Kraken trading bot application.
"""
import logging
from logging.handlers import RotatingFileHandler
import os
import sys

# Configure logging
def setup_logging(log_level="INFO"):
    """
    Set up logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Set up logging format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level),
        format=log_format,
        handlers=[
            # Console handler
            logging.StreamHandler(sys.stdout),
            # File handler with rotation
            RotatingFileHandler(
                "logs/deepagent_kraken.log",
                maxBytes=10 * 1024 * 1024,  # 10 MB
                backupCount=5
            )
        ]
    )
    
    # Set third-party loggers to a higher level to reduce noise
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("websocket").setLevel(logging.WARNING)
    
    logging.info(f"Logging configured with level: {log_level}")

# Version
__version__ = "0.1.0"
