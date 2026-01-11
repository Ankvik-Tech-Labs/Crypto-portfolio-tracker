"""Morpho Blue lending protocol handler."""

from crypto_portfolio_tracker.core.models import Position
from crypto_portfolio_tracker.core.registry import ProtocolRegistry
from crypto_portfolio_tracker.protocols.base import BaseProtocolHandler
from crypto_portfolio_tracker.protocols.morpho_api import MorphoAPIError, MorphoGraphQLClient


@ProtocolRegistry.register
class MorphoHandler(BaseProtocolHandler):
    """
    Handler for Morpho Blue lending positions.

    Uses Morpho GraphQL API to fetch market and vault positions with USD values.

    """

    name = "morpho"
    supported_chains = ["ethereum", "base"]

    # Event signatures for discovery - using generic Transfer events
    # since Morpho positions are better discovered via API
    discovery_events = [
        "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",  # Transfer
    ]

    def get_positions(self, user_address: str, chain: str) -> list[Position]:
        """
        Fetch Morpho positions for a user via GraphQL API.

        Parameters
        ----------
        user_address : str
            User wallet address
        chain : str
            Chain name

        Returns
        -------
        list[Position]
            List of Morpho positions (markets and vaults)

        """
        if chain not in self.supported_chains:
            return []

        try:
            with MorphoGraphQLClient() as client:
                return client.get_positions_as_models(user_address, chain)
        except MorphoAPIError:
            return []
        except Exception:
            return []
