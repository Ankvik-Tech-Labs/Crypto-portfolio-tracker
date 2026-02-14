"""Diagnostic tests for AAVE v3 position fetching across all supported chains."""

import pytest

from crypto_portfolio_tracker.data import (
    get_all_supported_chains,
    get_protocol_addresses,
)

TARGET_ADDRESS = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"  # vitalik.eth

AAVE_CHAINS = ["ethereum", "base", "arbitrum", "optimism", "polygon"]


class TestAaveChainSupport:
    """Verify AAVE v3 is properly configured across all supported chains."""

    def test_aave_chains_in_supported_chains(self):
        """All AAVE chains should appear in get_all_supported_chains."""
        supported = get_all_supported_chains()
        for chain in AAVE_CHAINS:
            assert chain in supported, f"{chain} missing from supported chains"

    @pytest.mark.parametrize("chain", AAVE_CHAINS)
    def test_aave_pool_address_configured(self, chain):
        """Each AAVE chain must have a pool address in protocol addresses."""
        addresses = get_protocol_addresses(chain, "aave_v3")
        assert "pool" in addresses, f"pool address missing for {chain}"
        assert addresses["pool"].startswith("0x"), f"invalid pool address on {chain}"

    @pytest.mark.parametrize("chain", AAVE_CHAINS)
    def test_aave_pool_data_provider_configured(self, chain):
        """Each AAVE chain must have a pool_data_provider address."""
        addresses = get_protocol_addresses(chain, "aave_v3")
        assert "pool_data_provider" in addresses, f"pool_data_provider missing for {chain}"
        assert addresses["pool_data_provider"].startswith("0x"), f"invalid pool_data_provider on {chain}"

    def test_handler_supported_chains(self):
        """AaveHandler.supported_chains should include all AAVE chains."""
        from crypto_portfolio_tracker.protocols.aave import AaveHandler

        for chain in AAVE_CHAINS:
            assert chain in AaveHandler.supported_chains, f"{chain} missing from AaveHandler.supported_chains"

    @pytest.mark.parametrize("chain", AAVE_CHAINS)
    def test_handler_does_not_reject_chain(self, chain):
        """AaveHandler.get_positions should not return [] due to unsupported chain."""
        from crypto_portfolio_tracker.protocols.aave import AaveHandler

        handler = AaveHandler()
        # Without an RPC provider, get_positions will fail at the contract call level,
        # but it should NOT return [] at the chain check on line 45-46.
        assert chain in handler.supported_chains

    def test_handler_chain_address_consistency(self):
        """Every chain in AaveHandler.supported_chains should have addresses in both sources."""
        from crypto_portfolio_tracker.protocols.aave import AaveHandler

        handler = AaveHandler()
        for chain in handler.supported_chains:
            addresses = handler.get_contract_addresses(chain)
            assert len(addresses) > 0, f"No contract addresses for {chain}"
            assert "pool" in addresses, f"pool missing in addresses for {chain}"
