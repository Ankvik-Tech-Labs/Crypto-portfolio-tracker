"""Tests for protocol registry."""

import pytest

from crypto_portfolio_tracker.core.registry import ProtocolRegistry


def test_protocol_registration():
    """Test that protocols auto-register on import."""
    # Import triggers registration
    from crypto_portfolio_tracker import protocols  # noqa: F401

    registered = ProtocolRegistry.list_protocols()
    
    # Check all protocols are registered
    assert "aave_v3" in registered
    assert "lido" in registered
    assert "morpho" in registered
    assert "etherfi" in registered
    assert "beefy" in registered
    
    # Should have exactly 5 protocols
    assert len(registered) == 5


def test_get_handler():
    """Test retrieving handler by name."""
    from crypto_portfolio_tracker import protocols  # noqa: F401

    handler_class = ProtocolRegistry.get_handler("lido")
    assert handler_class is not None
    assert handler_class.name == "lido"
    
    # Non-existent protocol
    assert ProtocolRegistry.get_handler("nonexistent") is None


def test_get_handlers_for_chain():
    """Test filtering handlers by chain."""
    from crypto_portfolio_tracker import protocols  # noqa: F401

    # Ethereum should have all 5 protocols
    eth_handlers = ProtocolRegistry.get_handlers_for_chain("ethereum")
    assert len(eth_handlers) == 5
    
    # Base should have 3 protocols (aave_v3, morpho, beefy)
    base_handlers = ProtocolRegistry.get_handlers_for_chain("base")
    assert len(base_handlers) == 3

    # Check specific protocols on Base
    base_names = [h.name for h in base_handlers]
    assert "aave_v3" in base_names
    assert "morpho" in base_names
    assert "beefy" in base_names
    assert "lido" not in base_names  # Lido only on Ethereum

    # Arbitrum/Optimism/Polygon should have aave_v3
    for chain in ["arbitrum", "optimism", "polygon"]:
        chain_handlers = ProtocolRegistry.get_handlers_for_chain(chain)
        chain_names = [h.name for h in chain_handlers]
        assert "aave_v3" in chain_names, f"aave_v3 missing on {chain}"


def test_handler_instantiation():
    """Test that handlers can be instantiated."""
    from crypto_portfolio_tracker import protocols  # noqa: F401

    handler_class = ProtocolRegistry.get_handler("lido")
    handler = handler_class()
    
    assert handler.name == "lido"
    assert "ethereum" in handler.supported_chains
    assert len(handler.discovery_events) > 0


def test_discovery_events():
    """Test getting discovery events for a chain."""
    from crypto_portfolio_tracker import protocols  # noqa: F401

    events = ProtocolRegistry.get_discovery_events("ethereum")
    
    # Should have events for all Ethereum protocols
    assert "lido" in events
    assert "aave_v3" in events
    assert isinstance(events["lido"], list)
    assert len(events["lido"]) > 0
