"""
mplog - Simplified logging for multiprocessing and asyncio programs

This library provides easy-to-use logging that works correctly with:
- Multiple processes (using queue-based logging)
- Asyncio coroutines
- Both synchronous and asynchronous contexts

Usage:
    from mplog import setup_logging, get_logger
    
    # In main process, before spawning workers
    setup_logging(level='INFO', log_file='app.log')
    
    # In any process/coroutine
    logger = get_logger(__name__)
    logger.info("This works from anywhere!")
"""

import logging
import logging.handlers
import multiprocessing as mp
import sys
import atexit
import threading
from typing import Optional, Union
from pathlib import Path


class MPLogger:
    """
    Multiprocessing-safe logger manager that uses queue-based logging.
    
    This class handles the complexity of setting up QueueHandler/QueueListener
    for safe logging across multiple processes.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the logger manager (singleton pattern)."""
        if self._initialized:
            return
            
        self._initialized = True
        self.queue = None
        self.listener = None
        self.handlers = []
        self._is_setup = False
        
    def setup(
        self,
        level: Union[int, str] = logging.INFO,
        log_file: Optional[Union[str, Path]] = None,
        log_to_stderr: bool = True,
        format_string: Optional[str] = None,
        date_format: Optional[str] = None,
        file_mode: str = 'a',
        file_encoding: str = 'utf-8',
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
    ):
        """
        Set up multiprocessing-safe logging.
        
        Args:
            level: Logging level (e.g., 'INFO', 'DEBUG', logging.INFO)
            log_file: Optional file path for file logging
            log_to_stderr: Whether to log to stderr (default: True)
            format_string: Custom format string for log messages
            date_format: Custom date format string
            file_mode: File mode for file handler ('a' for append, 'w' for write)
            file_encoding: Encoding for log file
            max_bytes: Maximum bytes before rotating log file (0 to disable rotation)
            backup_count: Number of backup files to keep when rotating
        """
        if self._is_setup:
            # Allow reconfiguration
            self.shutdown()
        
        # Convert string level to int if needed
        if isinstance(level, str):
            level = getattr(logging, level.upper())
        
        # Default format
        if format_string is None:
            format_string = (
                '%(asctime)s - %(processName)s[%(process)d] - '
                '%(threadName)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        if date_format is None:
            date_format = '%Y-%m-%d %H:%M:%S'
        
        formatter = logging.Formatter(format_string, datefmt=date_format)
        
        # Create queue for multiprocessing-safe logging
        self.queue = mp.Manager().Queue(-1)
        
        # Set up handlers that will actually write logs
        self.handlers = []
        
        if log_to_stderr:
            stderr_handler = logging.StreamHandler(sys.stderr)
            stderr_handler.setFormatter(formatter)
            self.handlers.append(stderr_handler)
        
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            if max_bytes > 0:
                # Use rotating file handler
                file_handler = logging.handlers.RotatingFileHandler(
                    log_path,
                    mode=file_mode,
                    maxBytes=max_bytes,
                    backupCount=backup_count,
                    encoding=file_encoding,
                )
            else:
                # Use regular file handler
                file_handler = logging.FileHandler(
                    log_path,
                    mode=file_mode,
                    encoding=file_encoding,
                )
            
            file_handler.setFormatter(formatter)
            self.handlers.append(file_handler)
        
        # Create and start the listener that processes log records from the queue
        self.listener = logging.handlers.QueueListener(
            self.queue, *self.handlers, respect_handler_level=True
        )
        self.listener.start()
        
        # Configure root logger to use queue handler
        queue_handler = logging.handlers.QueueHandler(self.queue)
        root = logging.getLogger()
        root.addHandler(queue_handler)
        root.setLevel(level)
        
        self._is_setup = True
        
        # Register shutdown on exit
        atexit.register(self.shutdown)
    
    def shutdown(self):
        """
        Shut down the logging system gracefully.
        
        This should be called when the program exits to ensure all
        log messages are flushed.
        """
        if self.listener:
            self.listener.stop()
            self.listener = None
        
        for handler in self.handlers:
            handler.close()
        
        self.handlers = []
        self._is_setup = False
    
    def get_logger(self, name: Optional[str] = None) -> logging.Logger:
        """
        Get a logger instance.
        
        Args:
            name: Logger name (typically __name__ of the module)
            
        Returns:
            A logging.Logger instance that works safely with multiprocessing
        """
        if not self._is_setup:
            # Set up with defaults if not already configured
            self.setup()
        
        return logging.getLogger(name)
    
    def is_setup(self) -> bool:
        """Check if logging has been set up."""
        return self._is_setup


# Global instance
_mp_logger = MPLogger()


# Convenience functions for the public API
def setup_logging(
    level: Union[int, str] = logging.INFO,
    log_file: Optional[Union[str, Path]] = None,
    log_to_stderr: bool = True,
    format_string: Optional[str] = None,
    date_format: Optional[str] = None,
    file_mode: str = 'a',
    file_encoding: str = 'utf-8',
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
):
    """
    Set up multiprocessing-safe logging.
    
    Call this once in your main process before spawning worker processes.
    
    Args:
        level: Logging level (e.g., 'INFO', 'DEBUG', logging.INFO)
        log_file: Optional file path for file logging
        log_to_stderr: Whether to log to stderr (default: True)
        format_string: Custom format string for log messages
        date_format: Custom date format string
        file_mode: File mode for file handler ('a' for append, 'w' for write)
        file_encoding: Encoding for log file
        max_bytes: Maximum bytes before rotating log file (0 to disable rotation)
        backup_count: Number of backup files to keep when rotating
    
    Example:
        setup_logging(level='INFO', log_file='app.log')
    """
    _mp_logger.setup(
        level=level,
        log_file=log_file,
        log_to_stderr=log_to_stderr,
        format_string=format_string,
        date_format=date_format,
        file_mode=file_mode,
        file_encoding=file_encoding,
        max_bytes=max_bytes,
        backup_count=backup_count,
    )


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance that works safely with multiprocessing and asyncio.
    
    Args:
        name: Logger name (typically __name__ of the module)
        
    Returns:
        A logging.Logger instance
        
    Example:
        logger = get_logger(__name__)
        logger.info("Hello from process %d", os.getpid())
    """
    return _mp_logger.get_logger(name)


def shutdown_logging():
    """
    Shut down the logging system gracefully.
    
    This is automatically called on program exit, but you can call it
    manually if needed.
    """
    _mp_logger.shutdown()


def is_logging_setup() -> bool:
    """
    Check if logging has been set up.
    
    Returns:
        True if setup_logging() has been called, False otherwise
    """
    return _mp_logger.is_setup()
