"""Data loading and configuration management."""

from crypto_portfolio_tracker.data.addresses import (
    CHAINLINK_PRICE_FEEDS,
    MULTICALL3_ADDRESS,
    PROTOCOL_ADDRESSES,
    TOKEN_ADDRESSES,
)
from crypto_portfolio_tracker.data.loader import (
    get_all_supported_chains,
    get_chain_config,
    get_chain_id,
    get_event_signatures,
    get_protocol_addresses,
    get_rpc_endpoints,
    load_contracts,
)

__all__ = [
    # Centralized address constants
    "CHAINLINK_PRICE_FEEDS",
    "MULTICALL3_ADDRESS",
    "PROTOCOL_ADDRESSES",
    "TOKEN_ADDRESSES",
    "get_all_supported_chains",
    "get_chain_config",
    "get_chain_id",
    "get_event_signatures",
    "get_protocol_addresses",
    "get_rpc_endpoints",
    # Loader functions
    "load_contracts",
]
