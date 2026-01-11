"""Multicall support for batching multiple contract calls using Multicall3 contract."""

import time
from typing import Any

from crypto_portfolio_tracker.rpc.retry import RetryConfig


class MulticallBatcher:
    """
    Batches multiple contract calls into a single multicall request using Multicall3.

    This reduces the number of RPC calls needed and improves performance.

    Parameters
    ----------
    provider : Any
        RPC provider instance (Ape provider)

    """

    def __init__(
        self,
        provider: Any,
        retry_config: RetryConfig | None = None,
        *,
        debug: bool = False,
    ) -> None:
        """
        Initialize the multicall batcher.

        Parameters
        ----------
        provider : Any
            Ape provider instance
        retry_config : RetryConfig | None
            Retry configuration for individual calls
        debug : bool
            Enable debug output

        """
        self.provider = provider
        self._calls: list[dict[str, Any]] = []
        self.debug = debug
        self.retry_config = retry_config or RetryConfig(
            max_retries=3,
            base_delay=1.0,
            max_delay=30.0,
            exponential_base=2.0,
        )

    def add_call(self, contract_address: str, method: str, params: list[Any]) -> None:
        """
        Add a contract call to the batch.

        Parameters
        ----------
        contract_address : str
            Target contract address
        method : str
            Method name (e.g., 'balanceOf')
        params : list[Any]
            Method parameters

        """
        self._calls.append(
            {
                "address": contract_address,
                "method": method,
                "params": params,
            }
        )

    def execute(self) -> list[Any]:
        """
        Execute all batched calls using Multicall3.

        Returns
        -------
        list[Any]
            Results for each call in order (None if call failed)

        """
        if not self._calls:
            return []

        # For now, just execute individually until we implement proper Multicall3
        # TODO: Implement proper Multicall3 batching with ABI encoding
        return self._execute_individually()

    def _execute_individually(self) -> list[Any]:
        """
        Execute calls individually with retry logic and exponential backoff.

        Returns
        -------
        list[Any]
            Results for each call in order (None if call failed)

        """
        results = []
        for call in self._calls:
            result = self._execute_single_call_with_retry(call)
            results.append(result)

        self._calls = []
        return results

    def _execute_single_call_with_retry(self, call: dict[str, Any]) -> Any:
        """
        Execute a single call with retry logic.

        Parameters
        ----------
        call : dict[str, Any]
            Call configuration

        Returns
        -------
        Any
            Call result or None if all retries failed

        """

        for attempt in range(self.retry_config.max_retries + 1):
            try:
                contract = self.provider.get_contract(call["address"])
                method = getattr(contract, call["method"])
                result = method(*call["params"])
                return result
            except Exception:
                # Don't retry on last attempt
                if attempt == self.retry_config.max_retries:
                    break

                # Calculate delay and wait
                delay = self.retry_config.get_delay(attempt)

                if self.debug:
                    pass

                time.sleep(delay)

        # All retries exhausted, return None
        if self.debug:
            pass
        return None

    def clear(self) -> None:
        """Clear all pending calls without executing."""
        self._calls = []

    @property
    def call_count(self) -> int:
        """
        Get number of calls in the batch.

        Returns
        -------
        int
            Number of pending calls

        """
        return len(self._calls)
