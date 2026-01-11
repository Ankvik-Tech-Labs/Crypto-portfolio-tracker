"""DeFiLlama pricing service for fetching token USD prices."""

from decimal import Decimal

import httpx


class DeFiLlamaPricing:
    """
    Fetches token prices from DeFiLlama API.

    DeFiLlama provides free, decentralized price data for thousands of tokens
    across multiple chains.

    Parameters
    ----------
    base_url : str
        DeFiLlama API base URL

    """

    def __init__(self, base_url: str = "https://coins.llama.fi") -> None:
        self.base_url = base_url
        self.client = httpx.Client(timeout=30.0)

    def get_prices(
        self,
        tokens: list[tuple[str, str]],
    ) -> dict[tuple[str, str], Decimal]:
        """
        Fetch USD prices for multiple tokens.

        Parameters
        ----------
        tokens : list[tuple[str, str]]
            List of (chain, address) tuples

        Returns
        -------
        dict[tuple[str, str], Decimal]
            Mapping of (chain, address) to USD price

        Examples
        --------
        >>> pricing = DeFiLlamaPricing()
        >>> tokens = [
        ...     ("ethereum", "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"),  # USDC
        ...     ("ethereum", "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"),  # WETH
        ... ]
        >>> prices = pricing.get_prices(tokens)

        """
        if not tokens:
            return {}

        # Build coin identifiers in DeFiLlama format: "chain:address"
        coin_ids = [self._format_coin_id(chain, addr) for chain, addr in tokens]

        # Fetch prices in batch
        prices_data = self._fetch_batch_prices(coin_ids)

        # Map back to original format
        result = {}
        for (chain, address), coin_id in zip(tokens, coin_ids, strict=False):
            price_info = prices_data.get(coin_id)
            if price_info and "price" in price_info:
                result[chain, address] = Decimal(str(price_info["price"]))
            else:
                result[chain, address] = Decimal("0")

        return result

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

    def _fetch_batch_prices(self, coin_ids: list[str]) -> dict:
        """
        Fetch prices from DeFiLlama API.

        Parameters
        ----------
        coin_ids : list[str]
            Coin identifiers in "chain:address" format

        Returns
        -------
        dict
            Raw API response with price data

        """
        try:
            # DeFiLlama batch price endpoint
            coins_param = ",".join(coin_ids)
            url = f"{self.base_url}/prices/current/{coins_param}"

            response = self.client.get(url)
            response.raise_for_status()

            data = response.json()
            return data.get("coins", {})

        except httpx.HTTPError:
            return {}
        except Exception:
            return {}

    def _format_coin_id(self, chain: str, address: str) -> str:
        """
        Format coin identifier for DeFiLlama API.

        Parameters
        ----------
        chain : str
            Chain name
        address : str
            Token address

        Returns
        -------
        str
            Formatted coin ID (e.g., "ethereum:0x...")

        """
        # DeFiLlama uses lowercase chain names
        chain_map = {
            "ethereum": "ethereum",
            "base": "base",
            # Add more chain mappings as needed
        }

        llama_chain = chain_map.get(chain.lower(), chain.lower())
        return f"{llama_chain}:{address}"

    def close(self) -> None:
        """Close HTTP client."""
        self.client.close()

    def __enter__(self) -> "DeFiLlamaPricing":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: type, exc_val: Exception, exc_tb: object) -> None:
        """Context manager exit."""
        self.close()
