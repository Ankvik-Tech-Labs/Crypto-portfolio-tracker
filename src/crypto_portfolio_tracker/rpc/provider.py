"""RPC provider wrapper using Ape's network management."""

import logging
import time
from typing import Any

from ape import Contract, networks

from crypto_portfolio_tracker.rpc.retry import RetryConfig

logger = logging.getLogger(__name__)


class ApeRPCProvider:
    """
    RPC provider using Ape's network management system.

    This provider uses Ape's built-in network switching and provider management,
    which automatically uses Infura when configured via environment variables.

    Parameters
    ----------
    chain : str
        Chain name (e.g., 'ethereum', 'base')
    network : str
        Network name (default: 'mainnet')

    """

    def __init__(
        self,
        chain: str,
        network: str = "mainnet",
        retry_config: RetryConfig | None = None,
        *,
        debug: bool = False,
    ) -> None:
        self.chain = chain
        self.network = network
        self._network_context = None
        self._provider = None
        self.debug = debug
        self.retry_config = retry_config or RetryConfig(
            max_retries=3,
            base_delay=1.0,
            max_delay=30.0,
            exponential_base=2.0,
        )

    def connect(self) -> None:
        """Connect to the network using Ape's network management."""
        try:
            # Use Ape's network context manager
            ecosystem = self.chain
            network_choice = f"{ecosystem}:{self.network}"

            self._network_context = networks.parse_network_choice(network_choice)
            self._network_context.__enter__()
            self._provider = networks.provider

        except Exception as e:
            error_msg = f"Failed to connect to {self.chain}:{self.network}: {e}"
            raise RuntimeError(error_msg) from e

    def disconnect(self) -> None:
        """Disconnect from the network."""
        if self._network_context:
            try:
                self._network_context.__exit__(None, None, None)
            except Exception as e:
                logger.debug("Error during network context cleanup: %s", e)
            self._network_context = None
        self._provider = None

    def make_request(self, method: str, params: list[Any]) -> Any:
        """
        Make an RPC request with retry logic and exponential backoff.

        Parameters
        ----------
        method : str
            RPC method name (e.g., 'eth_call', 'eth_getLogs')
        params : list[Any]
            Method parameters

        Returns
        -------
        Any
            RPC response

        Raises
        ------
        RuntimeError
            If provider is not connected
        Exception
            If all retry attempts fail

        """
        if not self._provider:
            error_msg = "Provider not connected. Call connect() first."
            raise RuntimeError(error_msg)

        last_exception = None

        for attempt in range(self.retry_config.max_retries + 1):
            try:
                return self._provider.make_request(method, params)
            except Exception as e:
                last_exception = e

                # Don't retry on last attempt
                if attempt == self.retry_config.max_retries:
                    break

                # Calculate delay and wait
                delay = self.retry_config.get_delay(attempt)

                if self.debug:
                    max_attempts = self.retry_config.max_retries + 1
                    logger.debug(
                        "RPC call %s failed (attempt %d/%d), retrying in %.1fs...",
                        method,
                        attempt + 1,
                        max_attempts,
                        delay,
                    )

                time.sleep(delay)

        # All retries exhausted
        if self.debug:
            max_attempts = self.retry_config.max_retries + 1
            logger.debug("RPC call %s failed after %d attempts", method, max_attempts)
        raise last_exception  # type: ignore

    def get_contract(self, address: str, abi: list | None = None):
        """
        Get a contract instance.

        Parameters
        ----------
        address : str
            Contract address
        abi : list | None
            Contract ABI (if None, will try to fetch from Etherscan)

        Returns
        -------
        Contract
            Ape contract instance

        """
        if not self._provider:
            error_msg = "Provider not connected. Call connect() first."
            raise RuntimeError(error_msg)

        if abi:
            return Contract(address, abi=abi)
        else:
            # Ape will automatically fetch ABI from Etherscan if configured
            return Contract(address)

    def __enter__(self) -> "ApeRPCProvider":
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type: type, exc_val: Exception, exc_tb: object) -> None:
        """Context manager exit."""
        self.disconnect()


# Backwards compatibility - MultiRPCProvider is an alias for ApeRPCProvider
# The old multi-RPC fallback logic is now handled by Ape's provider system
MultiRPCProvider = ApeRPCProvider
