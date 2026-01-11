"""Base protocol handler class with common functionality."""

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from crypto_portfolio_tracker.core.models import Position
from crypto_portfolio_tracker.data import get_protocol_addresses


class BaseProtocolHandler(ABC):
    """
    Abstract base class for protocol handlers.

    All protocol handlers should inherit from this class and implement
    the required abstract methods.

    Attributes
    ----------
    name : str
        Unique protocol identifier (must be set in subclass)
    supported_chains : list[str]
        Chains where protocol is deployed (must be set in subclass)
    discovery_events : list[str]
        Event signatures for position discovery (must be set in subclass)

    """

    name: ClassVar[str] = ""
    supported_chains: ClassVar[list[str]] = []
    discovery_events: ClassVar[list[str]] = []

    def __init__(self, rpc_provider: Any | None = None) -> None:
        """
        Initialize the protocol handler.

        Parameters
        ----------
        rpc_provider : Any | None
            RPC provider for making contract calls

        """
        if not self.name:
            msg = f"{self.__class__.__name__} must define 'name' attribute"
            raise ValueError(msg)
        if not self.supported_chains:
            msg = f"{self.__class__.__name__} must define 'supported_chains' attribute"
            raise ValueError(msg)
        self.rpc_provider = rpc_provider

    def get_contract_addresses(self, chain: str) -> dict[str, str]:
        """
        Get all contract addresses for this protocol on a chain.

        Parameters
        ----------
        chain : str
            Chain name

        Returns
        -------
        dict[str, str]
            Mapping of contract names to addresses

        """
        return get_protocol_addresses(chain, self.name)

    def matches(self, contract_address: str, chain: str) -> bool:
        """
        Check if this handler can process the given contract.

        Default implementation checks if address matches any known protocol contract.
        Override for custom matching logic.

        Parameters
        ----------
        contract_address : str
            Contract address to check (checksummed)
        chain : str
            Chain name

        Returns
        -------
        bool
            True if handler can process this contract

        """
        if chain not in self.supported_chains:
            return False

        addresses = self.get_contract_addresses(chain)
        # Case-insensitive comparison
        contract_lower = contract_address.lower()
        return any(addr.lower() == contract_lower for addr in addresses.values())

    @abstractmethod
    def get_positions(self, user_address: str, chain: str) -> list[Position]:
        """
        Fetch all positions for user on this protocol.

        Must be implemented by subclasses.

        Parameters
        ----------
        user_address : str
            User wallet address
        chain : str
            Chain name

        Returns
        -------
        list[Position]
            List of positions found

        """
        ...

    def _make_contract_call(
        self,
        contract_address: str,
        method: str,
        params: list[Any] | None = None,
        chain: str | None = None,
    ) -> Any:
        """
        Make a contract call using the RPC provider.

        Parameters
        ----------
        contract_address : str
            Target contract address
        method : str
            Method name (e.g., 'balanceOf', 'totalSupply')
        params : list[Any] | None
            Method parameters (default: None)
        chain : str | None
            Chain name (optional, for future multi-chain support)

        Returns
        -------
        Any
            Call result

        Raises
        ------
        RuntimeError
            If RPC provider is not configured

        """
        if not self.rpc_provider:
            msg = "RPC provider not configured for this handler"
            raise RuntimeError(msg)

        if params is None:
            params = []

        try:
            # Get contract instance using Ape
            contract = self.rpc_provider.get_contract(contract_address)

            # Call the method
            result = getattr(contract, method)(*params)

            return result
        except Exception as e:
            msg = f"Contract call failed: {e}"
            raise RuntimeError(msg) from e

    def is_supported_on_chain(self, chain: str) -> bool:
        """
        Check if protocol is supported on a chain.

        Parameters
        ----------
        chain : str
            Chain name

        Returns
        -------
        bool
            True if supported

        """
        return chain in self.supported_chains
