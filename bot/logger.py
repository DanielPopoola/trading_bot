import logging
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import traceback
from decimal import Decimal

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return super().default(obj)



class JSONFormatter(logging.Formatter):
    """
    Custom formatter that outputs structured JSON logs.
    
    Each log entry becomes a JSON object with consistent fields,
    making it easy to parse and analyze later.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Convert log record to JSON format."""

        # Base log entry structure
        log_entry = {
            'timestamp': datetime.now().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }

        # Add exception information if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }

        # Add any extra fields that were passed into the logger
        if hasattr(record, 'extra_data'):
            log_entry['data'] = record.extra_data

        return json.dumps(log_entry, ensure_ascii=False, cls=CustomJSONEncoder)
    

class TradingBotLogger:
    """
    Centralized logging configuration for the trading bot.
    
    Provides different log outputs:
    - Console: Human-readable for development
    - File: Structured JSON for analysis
    - Error file: Only errors and warnings
    """
    def __init__(self,
                 log_directory: str = "logs",
                 console_level: str = "INFO",
                 file_level: str = "DEBUG",
                 max_file_size: int = 10 * 1024 * 1024,
                 backup_count: int = 5):
        """
        Initialize logging configuration.
        
        Args:
            log_directory: Directory to store log files
            console_level: Minimum level for console output
            file_level: Minimum level for file output
            max_file_size: Maximum size of each log file before rotation
            backup_count: Number of backup files to keep
        """
        self.log_directory = Path(log_directory)
        self.console_level = getattr(logging, console_level.upper())
        self.file_level = getattr(logging, file_level.upper())
        self.max_file_size = max_file_size
        self.backup_count = backup_count

        # Create logs directory if it doesnt' exist
        self.log_directory.mkdir(exist_ok=True)
        
        # Initialize logging
        self._setup_logging()


    def _setup_logging(self) -> None:
        """Configure all logger and handlers."""

        # Get root logger and clear any existing handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        root_logger.setLevel(logging.DEBUG)

        # Console Handler - Human readable for development
        self._setup_console_handler(root_logger)
        
        # Main log file - All logs in JSON format
        self._setup_main_file_handler(root_logger)
        
        # Error log file - Only errors and warnings
        self._setup_error_file_handler(root_logger)
        
        # API-specific log file - Track all API interactions
        self._setup_api_log_handler()

    def _setup_console_handler(self, logger: logging.Logger) -> None:
        """Setup console output with human-readable format"""

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.console_level)

        # Human-readable format for console
        console_format = (
            '%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s'
        )
        console_formatter = logging.Formatter(
            console_format,
            datefmt='%H:%M:%S'
        )
        
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    def _setup_main_file_handler(self, logger: logging.Logger) -> None:
        """Setup main log file with JSON format."""

        from logging.handlers import RotatingFileHandler

        main_log_file = self.log_directory / "trading_bot.log"

        file_handler = RotatingFileHandler(
            main_log_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(self.file_level)
        file_handler.setFormatter(JSONFormatter())

        logger.addHandler(file_handler)

    def _setup_error_file_handler(self, logger: logging.Logger) -> None:
        """Setup error-only log file"""

        from logging.handlers import RotatingFileHandler

        error_log_file = self.log_directory / "errors.log"

        error_handler = RotatingFileHandler(
            error_log_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.WARNING)
        error_handler.setFormatter(JSONFormatter())

        logger.addHandler(error_handler)

    def _setup_api_log_handler(self) -> None:
        """Setup API-specific logging for tracking all API interactions."""

        from logging.handlers import RotatingFileHandler

        # Create separate logger for API calls
        api_logger = logging.getLogger('bot.api_client')
        api_log_file = self.log_directory  / "api_calls.log"

        api_handler = RotatingFileHandler(
            api_log_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        api_handler.setLevel(logging.DEBUG)
        api_handler.setFormatter(JSONFormatter())

        # Don't propagte to root logger (avoid duplicate entries)
        api_logger.propagate = False
        api_logger.addHandler(api_handler)

        # But also add console handler for immediate feedback
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.console_level)
        console_format = (
            '%(asctime)s | API | %(levelname)-8s | %(message)s'
        )
        console_formatter = logging.Formatter(console_format, datefmt='%H:%M:%S')
        console_handler.setFormatter(console_formatter)
        api_logger.addHandler(console_handler)

    
class ContextLogger:
    """
    Logger wrapper that adds consistent context to all log messages.
    
    Usage:
        logger = ContextLogger('my_component', {'user_id': '123', 'symbol': 'BTCUSDT'})
        logger.info("Order placed successfully", {'order_id': '456'})
    """
    def __init__(self, component_name: str, base_context: Optional[Dict[str, Any]] = None):
        """
        Initialize context logger.
        
        Args:
            component_name: Name of the component (e.g., 'api_client', 'validator')
            base_context: Context that will be added to every log message
        """
        self.logger = logging.getLogger(component_name)
        self.component_name = component_name
        self.base_context = base_context or {}

    def _log_with_context(self, level: str, message: str, extra_data: Optional[Dict[str, Any]] = None) -> None:
        """Internal method to log with context."""
        
        # Combine base context with message-specific data
        context = self.base_context.copy()
        if extra_data:
            context.update(extra_data)

        # Add component info
        context['component'] = self.component_name

        # Create log record with extra data
        log_method = getattr(self.logger, level.lower())

        # Create a custom LogRecord with extra data
        if context:
            # Use the 'extra' parameter to pass structured data
            record = self.logger.makeRecord(
                self.logger.name, getattr(logging, level.upper()),
                '', 0, message, (), None
            )
            record.extra_data = context
            self.logger.handle(record)
        else:
            log_method(message)

    def debug(self, message: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Log debug message with context."""
        self._log_with_context('DEBUG', message, data)
    
    def info(self, message: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Log info message with context."""
        self._log_with_context('INFO', message, data)
    
    def warning(self, message: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Log warning message with context."""
        self._log_with_context('WARNING', message, data)

    def error(self, message: str, data: Optional[Dict[str, Any]] = None, exc_info: bool = False) -> None:
        """Log error message with context"""
        if exc_info:
            # Capture current exception info
            import sys
            record = self.logger.makeRecord(
                self.logger.name, logging.ERROR,
                '', 0, message, (), sys.exc_info()
            )
            record.extra_data = {**self.base_context, **(data or {}), 'component': self.component_name}
            self.logger.handle(record)
        else:
            self._log_with_context('ERROR', message, data)


def setup_logging(log_directory: str = "logs", 
                 console_level: str = "INFO",
                 file_level: str = "DEBUG") -> TradingBotLogger:
    """
    Convenience function to setup logging for the entire application.
    
    Returns:
        TradingBotLogger instance for further configuration if needed
    """
    return TradingBotLogger(
        log_directory=log_directory,
        console_level=console_level,
        file_level=file_level
    )

# Utility functions for common logging patterns

def log_order_attempt(logger: ContextLogger, symbol: str, side: str, quantity: str, order_type: str, price: Optional[str] = None, timeInForce: Optional[str] = None) -> None:
    """Log order placement attempt with standard format."""
    log_data = {
        'symbol': symbol,
        'side': side,
        'quantity': quantity,
        'order_type': order_type,
        'action': 'order_attempt'
    }
    if price:
        log_data['price'] = price
    if timeInForce:
        log_data['timeInForce'] = timeInForce
    logger.info("Attempting to place order", log_data)

def log_order_success(logger: ContextLogger, order_result: Dict[str, Any]) -> None:
    """Log successful order placement."""
    logger.info("Order placed successfully", {
        'order_id': order_result.get('order_id'),
        'symbol': order_result.get('symbol'),
        'side': order_result.get('side'),
        'quantity': order_result.get('quantity'),
        'status': order_result.get('status'),
        'action': 'order_success'
    })

def log_order_failure(logger: ContextLogger, error: Exception, order_data: Dict[str, Any]) -> None:
    """Log order failure with context."""
    logger.error("Order placement failed", {
        'symbol': order_data.get('symbol'),
        'side': order_data.get('side'),
        'quantity': order_data.get('quantity'),
        'error_type': type(error).__name__,
        'error_message': str(error),
        'action': 'order_failure'
    }, exc_info=True)

def log_retry_attempt(logger: ContextLogger, operation: str, attempt: int, delay: float) -> None:
    """Log retry attempt."""
    logger.warning("Retrying operation", {
        'operation': operation,
        'attempt': attempt,
        'delay_seconds': delay,
        'action': 'retry_attempt'
    })

def log_api_call(logger: ContextLogger, endpoint: str, method: str, duration: float) -> None:
    """Log API call performance."""
    logger.info("API call completed", {
        'endpoint': endpoint,
        'method': method,
        'duration_seconds': round(duration, 3),
        'action': 'api_call'
    })

