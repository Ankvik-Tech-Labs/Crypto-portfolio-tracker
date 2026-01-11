"""Beefy Finance yield optimizer protocol handler."""

import os

from crypto_portfolio_tracker.core.models import Position
from crypto_portfolio_tracker.core.registry import ProtocolRegistry
from crypto_portfolio_tracker.integrations.zerion import ZerionAPIError, ZerionClient
from crypto_portfolio_tracker.protocols.base import BaseProtocolHandler
from crypto_portfolio_tracker.protocols.beefy_api import BeefyAPIClient, BeefyAPIError


@ProtocolRegistry.register
class BeefyHandler(BaseProtocolHandler):
    """
    Handler for Beefy Finance vault positions.

    Beefy has hundreds of vaults across multiple chains, so position
    discovery will rely heavily on event scanning.

    """

    name = "beefy"
    supported_chains = ["ethereum", "base"]

    # Event signatures for discovery
    discovery_events = [
        "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",  # Transfer (vault tokens)
    ]

    def get_positions(self, user_address: str, chain: str) -> list[Position]:
        """
        Fetch Beefy vault positions for a user.

        Uses Zerion API first (fast, includes USD values).
        Falls back to Beefy API + RPC if Zerion doesn't return positions.

        Parameters
        ----------
        user_address : str
            User wallet address
        chain : str
            Chain name

        Returns
        -------
        list[Position]
            List of Beefy vault positions

        """
        if chain not in self.supported_chains:
            return []

        # Try Zerion API first
        api_key = os.getenv("ZERION_API_KEY")
        if api_key:
            try:
                with ZerionClient(api_key) as client:
                    # Fetch all positions from Zerion
                    all_positions = client.get_positions_as_models(user_address, [chain])

                    # Filter for Beefy positions only
                    beefy_positions = [
                        pos for pos in all_positions if pos.protocol.lower() == "beefy" and pos.chain == chain
                    ]

                    if beefy_positions:
                        return beefy_positions

            except ZerionAPIError:
                pass
            except Exception:
                pass

        # Fallback to Beefy API + RPC
        if not self.rpc_provider:
            return []

        try:
            with BeefyAPIClient() as client:
                return client.get_vault_positions(user_address, chain, self.rpc_provider)
        except BeefyAPIError:
            return []
        except Exception:
            return []

    def _get_vault_position(
        self,
        user_address: str,
        vault_address: str,
        chain: str,
    ) -> Position | None:
        """
        Get position in a specific Beefy vault.

        Parameters
        ----------
        user_address : str
            User address
        vault_address : str
            Vault contract address
        chain : str
            Chain name

        Returns
        -------
        Position | None
            Vault position if balance > 0

        """
        # TODO: Implement actual contract calls
        # shares_balance = self._make_contract_call(
        #     vault_address,
        #     "balanceOf(address)",
        #     [user_address],
        #     chain,
        # )
        #
        # price_per_share = self._make_contract_call(
        #     vault_address,
        #     "getPricePerFullShare()",
        #     [],
        #     chain,
        # )
        #
        # want_token_address = self._make_contract_call(
        #     vault_address,
        #     "want()",
        #     [],
        #     chain,
        # )
        #
        # underlying_balance = shares_balance * price_per_share / 1e18

        # Placeholder
        return None

    def matches(self, contract_address: str, chain: str) -> bool:
        """
        Check if contract is a Beefy vault.

        Since Beefy has dynamic vaults, we can't use the default matches().
        We need to check if the contract implements Beefy vault interface.

        Parameters
        ----------
        contract_address : str
            Contract address
        chain : str
            Chain name

        Returns
        -------
        bool
            True if this is a Beefy vault

        """
        if chain not in self.supported_chains:
            return False

        # TODO: Check if contract has Beefy vault methods
        # Try calling getPricePerFullShare() and want()
        # If both exist, it's likely a Beefy vault

        return False
