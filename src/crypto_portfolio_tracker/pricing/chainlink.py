"""Chainlink pricing service for fetching on-chain token USD prices."""

from decimal import Decimal
from typing import Any

from crypto_portfolio_tracker.data.addresses import CHAINLINK_PRICE_FEEDS
from crypto_portfolio_tracker.rpc.multicall import MulticallBatcher


class ChainlinkPricing:
    """
    Fetches token prices from Chainlink price feeds.

    Chainlink provides decentralized, on-chain price oracles with high reliability
    and accuracy, particularly for stablecoins.

    Parameters
    ----------
    rpc_provider : Any
        RPC provider for contract calls
    fallback_pricing : Any | None
        Fallback pricing service (e.g., DeFiLlama) for tokens without Chainlink feeds

    """

    def __init__(
        self,
        rpc_provider: Any,
        fallback_pricing: Any | None = None,
    ) -> None:
        """
        Initialize Chainlink pricing service.

        Parameters
        ----------
        rpc_provider : Any
            RPC provider for contract calls
        fallback_pricing : Any | None
            Fallback pricing service for tokens without Chainlink feeds

        """
        self.rpc_provider = rpc_provider
        self.fallback_pricing = fallback_pricing

    def get_prices(
        self,
        tokens: list[tuple[str, str]],
    ) -> dict[tuple[str, str], Decimal]:
        """
        Fetch USD prices for multiple tokens.

        Uses Chainlink feeds when available, falls back to DeFiLlama otherwise.

        Parameters
        ----------
        tokens : list[tuple[str, str]]
            List of (chain, address) tuples

        Returns
        -------
        dict[tuple[str, str], Decimal]
            Mapping of (chain, address) to USD price

        """
        if not tokens:
            return {}

        prices = {}

        # Separate tokens with Chainlink feeds from those without
        chainlink_tokens = []
        fallback_tokens = []

        for chain, address in tokens:
            feed_address = self._get_feed_address(chain, address)
            if feed_address:
                chainlink_tokens.append((chain, address, feed_address))
            else:
                fallback_tokens.append((chain, address))

        # Fetch prices from Chainlink using multicall
        if chainlink_tokens:
            chainlink_prices = self._fetch_chainlink_prices(chainlink_tokens)
            prices.update(chainlink_prices)

        # Fetch remaining prices from fallback service
        if fallback_tokens and self.fallback_pricing:
            fallback_prices = self.fallback_pricing.get_prices(fallback_tokens)
            prices.update(fallback_prices)
        elif fallback_tokens:
            # No fallback, return 0 for unknown tokens
            for chain, address in fallback_tokens:
                prices[chain, address] = Decimal("0")

        return prices

    def get_price(self, chain: str, address: str) -> Decimal:
        """
        Fetch USD price for a single token.

        Parameters
        ----------
        chain : str
            Chain name
        address : str
            Token contract address

        Returns
        -------
        Decimal
            USD price

        """
        prices = self.get_prices([(chain, address)])
        return prices.get((chain, address), Decimal("0"))

    def _fetch_chainlink_prices(
        self,
        tokens: list[tuple[str, str, str]],
    ) -> dict[tuple[str, str], Decimal]:
        """
        Fetch prices from Chainlink price feeds using multicall.

        Parameters
        ----------
        tokens : list[tuple[str, str, str]]
            List of (chain, token_address, feed_address) tuples

        Returns
        -------
        dict[tuple[str, str], Decimal]
            Mapping of (chain, address) to USD price

        """
        prices = {}

        # Group by chain to batch calls
        by_chain: dict[str, list[tuple[str, str]]] = {}
        for chain, token_address, feed_address in tokens:
            if chain not in by_chain:
                by_chain[chain] = []
            by_chain[chain].append((token_address, feed_address))

        # Fetch prices per chain
        for chain, chain_tokens in by_chain.items():
            try:
                multicall = MulticallBatcher(self.rpc_provider)

                # Add all latestAnswer() calls to multicall
                indices = {}
                for token_address, feed_address in chain_tokens:
                    idx = multicall.call_count
                    multicall.add_call(feed_address, "latestAnswer", [])
                    indices[token_address] = idx

                # Execute batch
                results = multicall.execute()

                # Process results
                for token_address, feed_address in chain_tokens:
                    idx = indices[token_address]
                    price_raw = results[idx]

                    if price_raw and price_raw > 0:
                        # Chainlink price feeds return prices in 8 decimals
                        price = Decimal(str(price_raw)) / Decimal(10**8)
                        prices[chain, token_address] = price
                    else:
                        prices[chain, token_address] = Decimal("0")

            except Exception:
                # Silently fail and return 0 for all tokens on this chain
                # Fallback pricing will be used
                for token_address, _ in chain_tokens:
                    prices[chain, token_address] = Decimal("0")

        return prices

    def _get_feed_address(self, chain: str, token_address: str) -> str | None:
        """
        Get Chainlink price feed address for a token.

        Parameters
        ----------
        chain : str
            Chain name
        token_address : str
            Token contract address

        Returns
        -------
        str | None
            Price feed address, or None if not available

        """
        chain_feeds = CHAINLINK_PRICE_FEEDS.get(chain.lower())
        if not chain_feeds:
            return None

        # Normalize address to checksum format
        normalized_address = token_address
        return chain_feeds.get(normalized_address)

    def close(self) -> None:
        """Close pricing service (delegate to fallback if available)."""
        if self.fallback_pricing and hasattr(self.fallback_pricing, "close"):
            self.fallback_pricing.close()

    def __enter__(self) -> "ChainlinkPricing":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: type, exc_val: Exception, exc_tb: object) -> None:
        """Context manager exit."""
        self.close()
