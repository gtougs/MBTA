"""Logging utilities for MBTA Data Pipeline."""

import logging
import sys
from typing import Optional
from datetime import datetime

import structlog


def setup_logging(
    level: str = "INFO",
    format_string: Optional[str] = None,
    enable_json: bool = False
) -> None:
    """Setup structured logging for the application."""
    
    # Configure structlog
    if enable_json:
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
    else:
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.dev.ConsoleRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
    
    # Configure standard library logging
    logging.basicConfig(
        format=format_string or "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=getattr(logging, level.upper()),
        stream=sys.stdout
    )
    
    # Set specific logger levels
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    # Log startup message
    logger = get_logger(__name__)
    logger.info("Logging system initialized", level=level, json_output=enable_json)


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


def log_function_call(func_name: str, **kwargs):
    """Decorator to log function calls with parameters."""
    def decorator(func):
        def wrapper(*args, **func_kwargs):
            logger = get_logger(func.__module__)
            logger.info(
                f"Calling {func_name}",
                function=func_name,
                args_count=len(args),
                kwargs=func_kwargs,
                **kwargs
            )
            try:
                result = func(*args, **func_kwargs)
                logger.info(
                    f"Completed {func_name}",
                    function=func_name,
                    success=True
                )
                return result
            except Exception as e:
                logger.error(
                    f"Error in {func_name}",
                    function=func_name,
                    error=str(e),
                    success=False,
                    exc_info=True
                )
                raise
        return wrapper
    return decorator


def log_async_function_call(func_name: str, **kwargs):
    """Decorator to log async function calls with parameters."""
    def decorator(func):
        async def wrapper(*args, **func_kwargs):
            logger = get_logger(func.__module__)
            logger.info(
                f"Calling async {func_name}",
                function=func_name,
                args_count=len(args),
                kwargs=func_kwargs,
                **kwargs
            )
            try:
                result = await func(*args, **func_kwargs)
                logger.info(
                    f"Completed async {func_name}",
                    function=func_name,
                    success=True
                )
                return result
            except Exception as e:
                logger.error(
                    f"Error in async {func_name}",
                    function=func_name,
                    error=str(e),
                    success=False,
                    exc_info=True
                )
                raise
        return wrapper
    return decorator


class LogContext:
    """Context manager for adding context to logs."""
    
    def __init__(self, **context):
        self.context = context
        self.logger = structlog.get_logger()
    
    def __enter__(self):
        self.logger = self.logger.bind(**self.context)
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.logger.error(
                "Context exited with exception",
                exc_type=exc_type.__name__,
                exc_value=str(exc_val),
                **self.context
            )
        return False
