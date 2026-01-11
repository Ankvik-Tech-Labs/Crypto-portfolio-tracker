"""Tests for data loading and configuration."""

import pytest

from crypto_portfolio_tracker.data import (
    get_all_supported_chains,
    get_chain_config,
    get_chain_id,
    get_protocol_addresses,
    get_rpc_endpoints,
)


def test_get_all_supported_chains():
    """Test getting all supported chain names."""
    chains = get_all_supported_chains()
    
    assert isinstance(chains, list)
    assert "ethereum" in chains
    assert "base" in chains
    assert len(chains) >= 2


def test_get_chain_config():
    """Test getting chain configuration."""
    config = get_chain_config("ethereum")
    
    assert "chain_id" in config
    assert "rpc_endpoints" in config
    assert "protocols" in config
    assert config["chain_id"] == 1


def test_get_chain_id():
    """Test getting chain ID."""
    eth_id = get_chain_id("ethereum")
    base_id = get_chain_id("base")
    
    assert eth_id == 1
    assert base_id == 8453


def test_get_rpc_endpoints():
    """Test getting RPC endpoints for a chain."""
    endpoints = get_rpc_endpoints("ethereum")
    
    assert isinstance(endpoints, list)
    assert len(endpoints) > 0
    assert all(endpoint.startswith("https://") for endpoint in endpoints)


def test_get_protocol_addresses():
    """Test getting protocol addresses."""
    # Aave on Ethereum
    aave_eth = get_protocol_addresses("ethereum", "aave_v3")
    assert "pool" in aave_eth
    assert "pool_data_provider" in aave_eth
    assert aave_eth["pool"].startswith("0x")
    
    # Lido on Ethereum
    lido_eth = get_protocol_addresses("ethereum", "lido")
    assert "steth" in lido_eth
    assert "wsteth" in lido_eth
    
    # Aave on Base
    aave_base = get_protocol_addresses("base", "aave_v3")
    assert "pool" in aave_base
    
    # Non-existent protocol should return empty dict
    empty = get_protocol_addresses("ethereum", "nonexistent")
    assert empty == {}


def test_chain_config_structure():
    """Test that chain config has required structure."""
    for chain in get_all_supported_chains():
        config = get_chain_config(chain)
        
        # Required keys
        assert "chain_id" in config
        assert "rpc_endpoints" in config
        assert "protocols" in config
        
        # Types
        assert isinstance(config["chain_id"], int)
        assert isinstance(config["rpc_endpoints"], list)
        assert isinstance(config["protocols"], dict)
        
        # At least one RPC endpoint
        assert len(config["rpc_endpoints"]) > 0
