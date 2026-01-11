"""Contract address and configuration loader."""

from pathlib import Path
from typing import Any

import yaml

from crypto_portfolio_tracker.data.addresses import PROTOCOL_ADDRESSES


def load_contracts() -> dict[str, Any]:
    """
    Load centralized contract addresses from contracts.yaml.

    Returns
    -------
    dict[str, Any]
        Contract configuration including chains, protocols, and addresses

    """
    path = Path(__file__).parent / "contracts.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_chain_config(chain: str) -> dict[str, Any]:
    """
    Get configuration for a specific chain.

    Parameters
    ----------
    chain : str
        Chain name (e.g., 'ethereum', 'base')

    Returns
    -------
    dict[str, Any]
        Chain configuration including RPC endpoints and protocols

    Raises
    ------
    KeyError
        If chain is not found in configuration

    """
    contracts = load_contracts()
    return contracts["chains"][chain]


def get_protocol_addresses(chain: str, protocol: str) -> dict[str, str]:
    """
    Get all contract addresses for a protocol on a chain.

    Parameters
    ----------
    chain : str
        Chain name (e.g., 'ethereum', 'base')
    protocol : str
        Protocol name (e.g., 'aave_v3', 'lido')

    Returns
    -------
    dict[str, str]
        Mapping of contract names to addresses

    Raises
    ------
    KeyError
        If chain or protocol is not found

    """
    # Use centralized PROTOCOL_ADDRESSES first
    if protocol in PROTOCOL_ADDRESSES:
        protocol_config = PROTOCOL_ADDRESSES[protocol]
        if chain in protocol_config:
            return protocol_config[chain]

    # Fallback to contracts.yaml for backward compatibility
    try:
        chain_config = get_chain_config(chain)
        return chain_config["protocols"].get(protocol, {})
    except KeyError:
        return {}


def get_rpc_endpoints(chain: str) -> list[str]:
    """
    Get list of RPC endpoints for a chain.

    Parameters
    ----------
    chain : str
        Chain name

    Returns
    -------
    list[str]
        List of RPC endpoint URLs

    """
    chain_config = get_chain_config(chain)
    return chain_config["rpc_endpoints"]


def get_event_signatures(protocol: str) -> dict[str, str]:
    """
    Get event signatures for a protocol.

    Parameters
    ----------
    protocol : str
        Protocol name

    Returns
    -------
    dict[str, str]
        Mapping of event names to signatures

    """
    contracts = load_contracts()
    return contracts.get("event_signatures", {}).get(protocol, {})


def get_all_supported_chains() -> list[str]:
    """
    Get list of all supported chain names.

    Returns
    -------
    list[str]
        List of chain names

    """
    contracts = load_contracts()
    return list(contracts["chains"].keys())


def get_chain_id(chain: str) -> int:
    """
    Get numeric chain ID.

    Parameters
    ----------
    chain : str
        Chain name

    Returns
    -------
    int
        Chain ID

    """
    chain_config = get_chain_config(chain)
    return chain_config["chain_id"]
