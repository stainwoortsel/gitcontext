"""Logging configuration for GitContext."""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime
from rich.logging import RichHandler
from rich.console import Console
from rich.traceback import install

# Install rich traceback handler
install(show_locals=True)

# Console for rich output
console = Console()


class Logger:
    """Centralized logging for GitContext."""

    _instance: Optional['Logger'] = None
    _logger: Optional[logging.Logger] = None
    _debug_mode: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._logger is None:
            self.setup_logger()

    def setup_logger(self, debug: bool = False, log_file: Optional[Path] = None):
        """Setup the logger with appropriate handlers."""
        self._debug_mode = debug

        # Create logger
        self._logger = logging.getLogger("gitcontext")
        self._logger.setLevel(logging.DEBUG if debug else logging.INFO)
        self._logger.handlers.clear()

        # Console handler with rich formatting
        console_handler = RichHandler(
            console=console,
            show_time=True,
            show_path=debug,
            rich_tracebacks=True,
            tracebacks_show_locals=debug
        )
        console_handler.setLevel(logging.DEBUG if debug else logging.INFO)
        self._logger.addHandler(console_handler)

        # File handler if log_file specified
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            self._logger.addHandler(file_handler)

    @classmethod
    def debug(cls, message: str, *args, **kwargs):
        """Log debug message."""
        if cls._instance and cls._instance._logger:
            cls._instance._logger.debug(message, *args, **kwargs)

    @classmethod
    def info(cls, message: str, *args, **kwargs):
        """Log info message."""
        if cls._instance and cls._instance._logger:
            cls._instance._logger.info(message, *args, **kwargs)

    @classmethod
    def warning(cls, message: str, *args, **kwargs):
        """Log warning message."""
        if cls._instance and cls._instance._logger:
            cls._instance._logger.warning(message, *args, **kwargs)

    @classmethod
    def error(cls, message: str, *args, **kwargs):
        """Log error message."""
        if cls._instance and cls._instance._logger:
            cls._instance._logger.error(message, *args, **kwargs)

    @classmethod
    def critical(cls, message: str, *args, **kwargs):
        """Log critical message."""
        if cls._instance and cls._instance._logger:
            cls._instance._logger.critical(message, *args, **kwargs)

    @classmethod
    def exception(cls, message: str, *args, **kwargs):
        """Log exception with traceback."""
        if cls._instance and cls._instance._logger:
            cls._instance._logger.exception(message, *args, **kwargs)

    @classmethod
    def success(cls, message: str):
        """Log success message (using rich)."""
        console.print(f"✅ {message}", style="green")

    @classmethod
    def fail(cls, message: str):
        """Log failure message (using rich)."""
        console.print(f"❌ {message}", style="red")

    @classmethod
    def print(cls, message: str, style: str = None):
        """Print using rich."""
        if style:
            console.print(message, style=style)
        else:
            console.print(message)
