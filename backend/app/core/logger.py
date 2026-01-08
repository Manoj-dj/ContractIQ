import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime
from app.config import settings

class LoggerSetup:
    """Professional logging configuration with file and console handlers"""
    
    @staticmethod
    def setup_logger(name: str, log_file: str = None, level: str = None) -> logging.Logger:
        """
        Configure and return a logger with file and console handlers
        
        Args:
            name: Logger name (usually __name__)
            log_file: Optional custom log file name
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
        Returns:
            Configured logger instance
        """
        logger = logging.getLogger(name)
        
        # Set log level
        log_level = getattr(logging, (level or settings.LOG_LEVEL).upper(), logging.INFO)
        logger.setLevel(log_level)
        
        # Avoid duplicate handlers
        if logger.handlers:
            return logger
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        simple_formatter = logging.Formatter(
            fmt='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        
        # Console Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)
        logger.addHandler(console_handler)
        
        # File Handler (Rotating)
        if log_file is None:
            log_file = f"app_{datetime.now().strftime('%Y%m%d')}.log"
        
        log_path = Path(settings.LOG_DIR) / log_file
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)
        
        # Error File Handler (Separate file for errors)
        error_log_path = Path(settings.LOG_DIR) / f"errors_{datetime.now().strftime('%Y%m%d')}.log"
        error_handler = RotatingFileHandler(
            error_log_path,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        logger.addHandler(error_handler)
        
        return logger

def get_logger(name: str) -> logging.Logger:
    """Convenience function to get a configured logger"""
    return LoggerSetup.setup_logger(name)
