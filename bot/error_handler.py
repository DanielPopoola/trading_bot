import time
import logging
from typing import Callable, Any, Dict, Optional
from functools import wraps
from enum import Enum
import random

from .api_client import APIError, APIConnectionError, APIAuthenticationError, APIOrderError

class ErrorCategory(Enum):
    """Categories of errors for different handling strategies."""
    RETRYABLE = "retryable"          # Network issues, temporary server problems
    RATE_LIMITED = "rate_limited"     # Rate limiting - needs longer delays
    BUSINESS_LOGIC = "business_logic" # Invalid orders, insufficient balance
    AUTHENTICATION = "authentication" # Invalid API keys
    UNKNOWN = "unknown"               # Unclassified errors


class RetryConfig:
    """Configuration for retry behaviour"""

    def __init__(self):
        # Basic retry settings
        self.max_retries = 3
        self.base_delay = 1.0
        self.backoff_factor = 2.0
        self.max_delay = 60.0
        
        # Rate limiting settings
        self.rate_limit_delay = 10.0
        self.rate_limit_max_delay = 300.0
        
        # Add some randomness to avoid thundering herd
        self.jitter = True


class ErrorHandler:
    """
    Handles errors with intelligent retry logic.
    """

    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
        self.logger = logging.getLogger(__name__)

    def with_retry(self, operation_name: str = "API operation"):
        """
        Decorator that adds retry logic to any function.
        
        Usage:
            @error_handler.with_retry("place_order")
            def place_order():
                return api_client.place_order(data)
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, *kwargs):
                return self._execute_with_retry(func, operation_name, *args, **kwargs)
            return wrapper
        return decorator
    
    def _execute_with_retry(self, func: Callable, operation_name: str, *args, **kwargs) -> Any:
        """
        Execute a function with retry logic.
        Args:
            func: Function to execute
            operation_name: Description for logging
            *args, **kwargs: Arguments to pass to the function
        Returns:
            Function result if successful
        Raises:
            The final exception if all retries exhausted
        """
        last_exception = None

        for attempt in range(self.config.max_retries + 1):
            try:
                self.logger.info(f"Executing {operation_name}  (attempt {attempt + 1})")

                result = func(*args, *kwargs)

                if attempt > 0:
                    self.logger.info(f"{operation_name} succeeded after {attempt} retries")
                
                return result
            
            except Exception as e:
                last_exception = e
                error_category = self._categorize_error(e)

                self.logger.warning(
                    f"{operation_name} failed on attempt {attempt + 1}: {e} "
                    f"(category: {error_category.value})"
                )

                # Check if we should retry
                if not self._should_retry(error_category, attempt):
                    self.logger.error(
                        f"{operation_name} failed permanently: {e} "
                        f"(category: {error_category.value})"
                    )
                    raise e
                
                # Calculate delay and wait
                delay = self._calculate_delay(error_category, attempt)
                self.logger.info(f"Retrying {operation_name} in {delay:.2f} seconds...")
                
                time.sleep(delay)

        # If we get here, all retries were exhausted
        self.logger.error(f"{operation_name} failed after {self.config.max_retries} retries")
        raise last_exception
    
    def _categorize_error(self, error: Exception) -> ErrorCategory:
        """
        Categorize errors to determine retry strategy.
        
        This is the "brain" that decides what kind of problem we're dealing with.
        """
        # API-specific errors (from api_client.py)
        if isinstance(error, APIConnectionError):
            return ErrorCategory.RETRYABLE
        elif isinstance(error, APIAuthenticationError):
            return ErrorCategory.AUTHENTICATION
        elif isinstance(error, APIOrderError):
            # Check if it's a rate limiting issue
            error_msg = str(error).lower()
            if "rate limit" in error_msg or "too many requests" in error_msg:
                return ErrorCategory.RATE_LIMITED
            else:
                return ErrorCategory.BUSINESS_LOGIC
        
        # Standard Python exceptions
        elif isinstance(error, (ConnectionError, TimeoutError)):
            return ErrorCategory.RETRYABLE
        
        # HTTP-related errors (if using requests directly)
        elif hasattr(error, 'response') and hasattr(error.response, 'status_code'):
            status_code = error.response.status_code
            if status_code == 429:
                return ErrorCategory.RATE_LIMITED
            elif 500 <= status_code < 600:
                return ErrorCategory.RETRYABLE
            elif status_code in [401, 403]:
                return ErrorCategory.AUTHENTICATION
            elif 400 <= status_code < 500:
                return ErrorCategory.BUSINESS_LOGIC
        
        # Default for unknown errors
        self.logger.warning(f"Unknown error type: {type(error).__name__}: {error}")
        return ErrorCategory.UNKNOWN
    
    def _should_retry(self, error_category: ErrorCategory, attempt: int) -> bool:
        """
        Determine if we should retry based on error type and attempt number.
        
        Args:
            error_category: Type of error we encountered
            attempt: Current attempt number (0-based)
        
        Returns:
            True if we should retry, False if we should give up
        """
        # Never retry if we've hit max attempts
        if attempt >= self.config.max_retries:
            return False
        
        # Retry logic based on error category
        if error_category == ErrorCategory.RETRYABLE:
            return True
        
        elif error_category == ErrorCategory.RATE_LIMITED:
            return True
        
        elif error_category == ErrorCategory.BUSINESS_LOGIC:
            return False
        
        elif error_category == ErrorCategory.AUTHENTICATION:
            return False
        
        elif error_category == ErrorCategory.UNKNOWN:
            return attempt == 0
        
        return False
    
    def _calculate_delay(self, error_category: ErrorCategory, attempt: int) -> float:
        """
        Calculate how long to wait before the next retry.
        
        Different error types get different delay strategies.
        """
        if error_category == ErrorCategory.RATE_LIMITED:
            # For rate limits, use longer delays
            base_delay = self.config.rate_limit_delay
            max_delay = self.config.rate_limit_max_delay
        else:
            # Standard exponential backoff
            base_delay = self.config.base_delay
            max_delay = self.config.max_delay

        delay = base_delay * (self.config.backoff_factor ** attempt)
        
        delay = min(delay, max_delay)
        
        # Add jitter to avoid thundering herd problem
        if self.config.jitter:
            jitter_amount = delay * 0.2
            jitter = random.uniform(-jitter_amount, jitter_amount)
            delay = max(0.1, delay + jitter)  # Ensure minimum 0.1s delay
        
        return delay
    
    def execute_with_context(self, func: Callable, operation_name: str, 
                           context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute function with retry logic and return detailed results.

        Returns:
            Dict with:
            - success: bool
            - result: function result (if successful) 
            - error: exception (if failed)
            - attempts: number of attempts made
            - duration: total time spent
        """
        start_time = time.time()
        context = context or {}
        attempts = 0
        
        try:
            result = self._execute_with_retry(func, operation_name)
            
            return {
                'success': True,
                'result': result,
                'error': None,
                'attempts': attempts + 1,
                'duration': time.time() - start_time,
                'context': context
            }
            
        except Exception as e:
            return {
                'success': False,
                'result': None,
                'error': e,
                'attempts': self.config.max_retries + 1,
                'duration': time.time() - start_time,
                'context': context
            }
