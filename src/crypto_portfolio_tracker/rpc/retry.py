"""Retry logic with exponential backoff for RPC calls."""

import time
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

T = TypeVar("T")


class RetryConfig:
    """
    Configuration for retry behavior.

    Parameters
    ----------
    max_retries : int
        Maximum number of retry attempts
    base_delay : float
        Initial delay in seconds before first retry
    max_delay : float
        Maximum delay between retries
    exponential_base : float
        Base for exponential backoff calculation

    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
    ) -> None:
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base

    def get_delay(self, attempt: int) -> float:
        """
        Calculate delay for a given retry attempt using exponential backoff.

        Parameters
        ----------
        attempt : int
            Current attempt number (0-indexed)

        Returns
        -------
        float
            Delay in seconds

        """
        delay = self.base_delay * (self.exponential_base**attempt)
        return min(delay, self.max_delay)


def with_retry(config: RetryConfig | None = None) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to add retry logic with exponential backoff to a function.

    Parameters
    ----------
    config : RetryConfig | None
        Retry configuration. Uses default config if None.

    Returns
    -------
    Callable
        Decorated function with retry logic

    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None

            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    # Don't retry on last attempt
                    if attempt == config.max_retries:
                        break

                    # Calculate delay and wait
                    delay = config.get_delay(attempt)
                    time.sleep(delay)

            # All retries exhausted
            raise last_exception  # type: ignore

        return wrapper

    return decorator


class RetryManager:
    """
    Manages retry logic for RPC providers with endpoint rotation.

    Parameters
    ----------
    provider : Any
        RPC provider instance with rotate_endpoint method
    config : RetryConfig | None
        Retry configuration

    """

    def __init__(self, provider: Any, config: RetryConfig | None = None) -> None:
        self.provider = provider
        self.config = config or RetryConfig()

    def execute_with_retry(self, method: str, params: list[Any]) -> Any:
        """
        Execute RPC call with retry and endpoint rotation on failure.

        Parameters
        ----------
        method : str
            RPC method name
        params : list[Any]
            Method parameters

        Returns
        -------
        Any
            RPC response

        Raises
        ------
        Exception
            If all retries and endpoints fail

        """
        last_exception = None

        for attempt in range(self.config.max_retries + 1):
            try:
                return self.provider.make_request(method, params)
            except Exception as e:
                last_exception = e

                # Rotate to next endpoint
                self.provider.rotate_endpoint()

                # Don't retry on last attempt
                if attempt == self.config.max_retries:
                    break

                # Wait before retry
                delay = self.config.get_delay(attempt)
                time.sleep(delay)

        raise last_exception  # type: ignore
