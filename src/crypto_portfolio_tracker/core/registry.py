"""Protocol handler registry with auto-registration pattern."""

from typing import Any, Protocol


class ProtocolHandlerInterface(Protocol):
    """
    Interface that all protocol handlers must implement.

    Attributes
    ----------
    name : str
        Unique protocol identifier (e.g., 'aave_v3', 'lido')
    supported_chains : list[str]
        Chains where this protocol is deployed
    discovery_events : list[str]
        Event signatures for discovering user positions

    Methods
    -------
    matches(contract_address, chain)
        Check if handler can process a specific contract
    get_positions(user_address, chain)
        Fetch all positions for user on this protocol

    """

    name: str
    supported_chains: list[str]
    discovery_events: list[str]

    def matches(self, contract_address: str, chain: str) -> bool:
        """
        Check if this handler can process the given contract.

        Parameters
        ----------
        contract_address : str
            Contract address to check
        chain : str
            Chain name

        Returns
        -------
        bool
            True if handler can process this contract

        """
        ...

    def get_positions(self, user_address: str, chain: str) -> list[Any]:
        """
        Fetch all positions for user on this protocol.

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


class ProtocolRegistry:
    """
    Registry for protocol handlers with auto-registration.

    Handlers register themselves using the @ProtocolRegistry.register decorator.
    The scanner can then query all handlers for protocol discovery.

    """

    _handlers: dict[str, type] = {}

    @classmethod
    def register(cls, handler_class: type) -> type:
        """
        Decorator to register a protocol handler.

        Parameters
        ----------
        handler_class : type
            Handler class to register

        Returns
        -------
        type
            The handler class (for decorator chaining)

        Examples
        --------
        >>> @ProtocolRegistry.register
        ... class LidoHandler:
        ...     name = "lido"
        ...     supported_chains = ["ethereum"]
        ...     discovery_events = [...]

        """
        if not hasattr(handler_class, "name"):
            msg = f"Handler {handler_class.__name__} must define 'name' attribute"
            raise ValueError(msg)

        cls._handlers[handler_class.name] = handler_class
        return handler_class

    @classmethod
    def get_handler(cls, protocol_name: str) -> type | None:
        """
        Get handler class by protocol name.

        Parameters
        ----------
        protocol_name : str
            Protocol identifier

        Returns
        -------
        type | None
            Handler class or None if not found

        """
        return cls._handlers.get(protocol_name)

    @classmethod
    def get_all_handlers(cls) -> list[type]:
        """
        Get all registered handler classes.

        Returns
        -------
        list[type]
            List of all handler classes

        """
        return list(cls._handlers.values())

    @classmethod
    def get_handlers_for_chain(cls, chain: str) -> list[type]:
        """
        Get all handlers that support a specific chain.

        Parameters
        ----------
        chain : str
            Chain name

        Returns
        -------
        list[type]
            List of handler classes supporting this chain

        """
        return [handler_class for handler_class in cls._handlers.values() if chain in handler_class.supported_chains]

    @classmethod
    def get_discovery_events(cls, chain: str) -> dict[str, list[str]]:
        """
        Get all event signatures for protocol discovery on a chain.

        Parameters
        ----------
        chain : str
            Chain name

        Returns
        -------
        dict[str, list[str]]
            Mapping of protocol names to event signature lists

        """
        events = {}
        for handler_class in cls.get_handlers_for_chain(chain):
            events[handler_class.name] = handler_class.discovery_events
        return events

    @classmethod
    def find_handler_for_contract(cls, contract_address: str, chain: str) -> type | None:
        """
        Find handler that matches a specific contract address.

        Parameters
        ----------
        contract_address : str
            Contract address
        chain : str
            Chain name

        Returns
        -------
        type | None
            Handler class if found, None otherwise

        """
        for handler_class in cls.get_handlers_for_chain(chain):
            # Instantiate handler to call matches method
            handler = handler_class()
            if handler.matches(contract_address, chain):
                return handler_class
        return None

    @classmethod
    def clear(cls) -> None:
        """Clear all registered handlers (useful for testing)."""
        cls._handlers.clear()

    @classmethod
    def list_protocols(cls) -> list[str]:
        """
        Get list of all registered protocol names.

        Returns
        -------
        list[str]
            List of protocol identifiers

        """
        return list(cls._handlers.keys())
