"""Zerion API client for comprehensive position aggregation."""

from decimal import Decimal
from typing import Any

import httpx

from crypto_portfolio_tracker.core.models import Position, PositionType, Token


class ZerionAPIError(Exception):
    """Exception raised for Zerion API errors."""


class ZerionClient:
    """
    Client for Zerion API.

    Fetches comprehensive position data across all protocols and chains.

    Parameters
    ----------
    api_key : str
        Zerion API key
    base_url : str
        API base URL

    """

    BASE_URL = "https://api.zerion.io/v1"

    # Chain ID mapping (Zerion uses string identifiers)
    CHAIN_MAPPING = {
        "ethereum": "ethereum",
        "base": "base",
        "arbitrum": "arbitrum",
        "optimism": "optimism",
        "polygon": "polygon",
    }

    # Reverse mapping for converting Zerion chain IDs to our chain names
    REVERSE_CHAIN_MAPPING = {v: k for k, v in CHAIN_MAPPING.items()}

    def __init__(
        self,
        api_key: str,
        base_url: str = BASE_URL,
        timeout: float = 30.0,
    ) -> None:
        """
        Initialize Zerion client.

        Parameters
        ----------
        api_key : str
            Zerion API key (format: zk_dev_xxx or zk_prod_xxx)
        base_url : str
            API base URL
        timeout : float
            Request timeout in seconds

        """
        self.api_key = api_key
        self.base_url = base_url
        self.client = httpx.Client(
            timeout=timeout,
            auth=(api_key, ""),  # Zerion uses HTTP basic auth with key as username
        )

    def get_positions(
        self,
        wallet_address: str,
        chains: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Fetch all positions for a wallet across specified chains.

        Parameters
        ----------
        wallet_address : str
            Wallet address
        chains : list[str] | None
            List of chain names to query (None = all supported chains)

        Returns
        -------
        dict[str, Any]
            Raw Zerion API response with positions

        Raises
        ------
        ZerionAPIError
            If the API request fails

        """
        # Convert chain names to Zerion chain IDs
        chain_ids = []
        if chains:
            for chain in chains:
                zerion_chain = self.CHAIN_MAPPING.get(chain.lower())
                if zerion_chain:
                    chain_ids.append(zerion_chain)
        else:
            # Use all supported chains
            chain_ids = list(self.CHAIN_MAPPING.values())

        # Build query parameters
        params = {
            "filter[chain_ids]": ",".join(chain_ids),
            "currency": "usd",
        }

        try:
            url = f"{self.base_url}/wallets/{wallet_address}/positions/"
            response = self.client.get(url, params=params)
            response.raise_for_status()
            return response.json()

        except httpx.TimeoutException as e:
            msg = f"Request timeout: {e}"
            raise ZerionAPIError(msg) from e
        except httpx.HTTPStatusError as e:
            msg = f"HTTP error {e.response.status_code}: {e}"
            raise ZerionAPIError(msg) from e
        except httpx.HTTPError as e:
            msg = f"HTTP request failed: {e}"
            raise ZerionAPIError(msg) from e

    def get_positions_as_models(
        self,
        wallet_address: str,
        chains: list[str] | None = None,
    ) -> list[Position]:
        """
        Fetch and convert positions to Position models.

        Parameters
        ----------
        wallet_address : str
            Wallet address
        chains : list[str] | None
            List of chain names to query

        Returns
        -------
        list[Position]
            List of Position objects

        """
        raw_data = self.get_positions(wallet_address, chains)
        positions = []

        for item in raw_data.get("data", []):
            position = self._parse_position(item)
            if position:
                positions.append(position)

        return positions

    def _parse_position(self, item: dict[str, Any]) -> Position | None:
        """
        Parse a Zerion position into a Position model.

        Parameters
        ----------
        item : dict[str, Any]
            Raw position data from Zerion

        Returns
        -------
        Position | None
            Position object or None if invalid

        """
        try:
            attributes = item.get("attributes", {})
            relationships = item.get("relationships", {})

            # Extract basic position info
            position_type_str = attributes.get("position_type", "wallet")
            quantity_data = attributes.get("quantity", {})

            # Handle quantity - use numeric or float
            quantity_str = quantity_data.get("numeric") or str(quantity_data.get("float", 0))
            quantity = Decimal(quantity_str) if quantity_str else Decimal(0)

            # Handle value_usd - it might be None or a complex object
            # Keep full precision, formatting will be done at display time
            value_raw = attributes.get("value", 0)
            try:
                value_usd = Decimal(str(value_raw)) if value_raw is not None else Decimal(0)
            except (ValueError, TypeError):
                value_usd = Decimal(0)

            # Skip positions with zero value (unless it's a protocol position with quantity)
            if value_usd == 0 and quantity == 0:
                return None

            # Extract chain info
            chain_data = relationships.get("chain", {}).get("data", {})
            zerion_chain_id = chain_data.get("id", "ethereum")
            chain = self.REVERSE_CHAIN_MAPPING.get(zerion_chain_id, zerion_chain_id)

            # Extract fungible (token) info from attributes.fungible_info
            fungible_info = attributes.get("fungible_info", {})

            # Get token address for this chain
            token_address = ""
            implementations = fungible_info.get("implementations", [])
            for impl in implementations:
                if impl.get("chain_id") == zerion_chain_id:
                    token_address = impl.get("address") or ""
                    break

            token = Token(
                address=token_address or "",  # Ensure not None
                symbol=fungible_info.get("symbol", "UNKNOWN"),
                decimals=quantity_data.get("decimals", 18),
                name=fungible_info.get("name", ""),
            )

            # Determine position type
            position_type = self._map_position_type(position_type_str, attributes)

            # Extract protocol info - first from attributes, then infer from token symbol/name
            protocol_name = self._detect_protocol(attributes, fungible_info)

            # Build metadata
            metadata = {
                "zerion_position_type": position_type_str,
                "zerion_protocol": protocol_name,
                "source": "zerion",
            }

            # Add any additional attributes
            if "name" in attributes:
                metadata["position_name"] = attributes["name"]

            # Add parent info if available (for nested positions like LP tokens in vaults)
            if attributes.get("parent"):
                metadata["parent"] = attributes["parent"]

            return Position(
                protocol=protocol_name,
                chain=chain,
                position_type=position_type,
                token=token,
                balance=quantity,
                usd_value=value_usd,
                metadata=metadata,
            )

        except Exception:
            # Skip positions that can't be parsed

            return None

    def _map_position_type(
        self,
        zerion_type: str,
        attributes: dict[str, Any],
    ) -> PositionType:
        """
        Map Zerion position type to our PositionType enum.

        Parameters
        ----------
        zerion_type : str
            Zerion position type
        attributes : dict[str, Any]
            Position attributes

        Returns
        -------
        PositionType
            Mapped position type

        """
        # Zerion position types: asset, deposit, loan, staked, etc.
        type_mapping = {
            "deposit": PositionType.LENDING_SUPPLY,
            "loan": PositionType.LENDING_BORROW,
            "staked": PositionType.LIQUID_STAKING,
            "locked": PositionType.VAULT,
        }

        # Check if it's a vault/pool position
        if "name" in attributes:
            name = attributes["name"].lower()
            if "vault" in name or "pool" in name:
                return PositionType.VAULT

        return type_mapping.get(zerion_type, PositionType.VAULT)

    def _detect_protocol(
        self,
        attributes: dict[str, Any],
        fungible_info: dict[str, Any],
    ) -> str:
        """
        Detect protocol from attributes, token symbol, or position name.

        Parameters
        ----------
        attributes : dict[str, Any]
            Position attributes from Zerion
        fungible_info : dict[str, Any]
            Token fungible_info from attributes

        Returns
        -------
        str
            Protocol name

        """
        # First check explicit protocol field
        if attributes.get("protocol"):
            return attributes["protocol"]

        # Get token symbol and position name for inference
        token_symbol = fungible_info.get("symbol", "").lower()
        position_name = attributes.get("name", "").lower()

        # Protocol detection patterns based on token symbols
        protocol_patterns = {
            # Aave: aTokens (aEthUSDC, aBasUSDC, etc.)
            "aave": ["abas", "aeth", "aopt", "apol", "aarb"],
            # Morpho: Various vault tokens (steakUSDC, sparkUSDC, etc.)
            "morpho": ["steak", "spark", "steakhouse", "morpho"],
            # Beefy: mooTokens
            "beefy": ["moo"],
            # Ether.fi: eETH, weETH, liquidUSD
            "etherfi": ["eeth", "weeth", "liquidusd"],
            # Lido: stETH, wstETH
            "lido": ["steth", "wsteth"],
        }

        # Check token symbol against patterns
        for protocol, patterns in protocol_patterns.items():
            for pattern in patterns:
                if pattern in token_symbol:
                    return protocol

        # Check position name against patterns
        for protocol, patterns in protocol_patterns.items():
            for pattern in patterns:
                if pattern in position_name:
                    return protocol

        # Check for generic protocol indicators in position name
        if "vault" in position_name or "pool" in position_name:
            # Try to extract protocol from position name
            # e.g., "Spark USDC Vault" -> "spark"
            words = position_name.split()
            if len(words) > 0:
                first_word = words[0].lower()
                # Check if first word matches a known protocol
                for protocol, patterns in protocol_patterns.items():
                    if first_word in patterns or first_word == protocol:
                        return protocol

        # Default to wallet if can't determine protocol
        return "wallet"

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self) -> "ZerionClient":
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: type | None,
        exc_val: Exception | None,
        exc_tb: object | None,
    ) -> None:
        """Context manager exit."""
        self.close()
