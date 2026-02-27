"""Octav.fi API client for comprehensive portfolio position fetching."""

from decimal import Decimal
from typing import Any

import httpx

from crypto_portfolio_tracker.core.models import Position, PositionType, Token


class OctavAPIError(Exception):
    """Exception raised for Octav API errors."""


class OctavClient:
    """
    Client for Octav.fi API.

    Fetches portfolio positions across all protocols and chains via the
    Octav REST API. Positions are returned grouped by protocol with USD
    values included.

    :param api_key: Octav API key (Bearer token)
    :param base_url: API base URL
    :param timeout: Request timeout in seconds
    """

    BASE_URL = "https://api.octav.fi/v1"

    # Chain key mapping (Octav uses lowercase identifiers matching ours)
    CHAIN_MAPPING = {
        "ethereum": "ethereum",
        "base": "base",
        "arbitrum": "arbitrum",
        "optimism": "optimism",
        "polygon": "polygon",
    }

    REVERSE_CHAIN_MAPPING = {v: k for k, v in CHAIN_MAPPING.items()}

    # Protocol keys that indicate lending supply positions (aToken patterns)
    _SUPPLY_INDICATORS = ("aave", "aave_v3", "aave_v2", "compound", "spark")

    # Token symbol patterns for borrow/debt positions
    _DEBT_SYMBOL_PATTERNS = ("debt", "variable", "stable")

    # Protocol keys for liquid staking
    _STAKING_PROTOCOLS = ("lido", "rocketpool", "rocket_pool", "coinbase", "frax_ether")

    def __init__(
        self,
        api_key: str,
        base_url: str = BASE_URL,
        timeout: float = 30.0,
    ) -> None:
        """
        Initialize Octav client.

        :param api_key: Octav API key (JWT Bearer token)
        :param base_url: API base URL
        :param timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.base_url = base_url
        self.client = httpx.Client(
            timeout=timeout,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    def get_portfolio(self, wallet_address: str) -> dict[str, Any]:
        """
        Fetch raw portfolio data for a wallet address.

        :param wallet_address: EVM wallet address
        :returns: Raw Octav API response dict
        :raises OctavAPIError: If the API request fails
        """
        params = {"addresses": wallet_address}

        try:
            url = f"{self.base_url}/portfolio"
            response = self.client.get(url, params=params)
            response.raise_for_status()
            return response.json()

        except httpx.TimeoutException as e:
            msg = f"Request timeout: {e}"
            raise OctavAPIError(msg) from e
        except httpx.HTTPStatusError as e:
            msg = f"HTTP error {e.response.status_code}: {e}"
            raise OctavAPIError(msg) from e
        except httpx.HTTPError as e:
            msg = f"HTTP request failed: {e}"
            raise OctavAPIError(msg) from e

    def get_positions(
        self,
        wallet_address: str,
        chains: list[str] | None = None,
    ) -> list[Position]:
        """
        Fetch and convert portfolio positions to Position models.

        :param wallet_address: EVM wallet address
        :param chains: Optional list of chain names to filter by
        :returns: List of Position objects
        :raises OctavAPIError: If the API request fails
        """
        raw_data = self.get_portfolio(wallet_address)
        data = raw_data.get("data", raw_data)

        positions = []
        asset_by_protocols = data.get("assetByProtocols", {})

        for protocol_key, protocol_data in asset_by_protocols.items():
            parsed = self._parse_protocol_positions(protocol_key, protocol_data)
            positions.extend(parsed)

        # Filter by chains if specified
        if chains:
            allowed = {c.lower() for c in chains}
            positions = [p for p in positions if p.chain in allowed]

        return positions

    def get_nav(self, wallet_address: str) -> Decimal:
        """
        Fetch net asset value for a wallet address.

        :param wallet_address: EVM wallet address
        :returns: Net asset value as Decimal (USD)
        :raises OctavAPIError: If the API request fails
        """
        params = {"addresses": wallet_address}

        try:
            url = f"{self.base_url}/nav"
            response = self.client.get(url, params=params)
            response.raise_for_status()
            result = response.json()
            data = result.get("data", result)
            return Decimal(str(data.get("nav", 0)))

        except httpx.TimeoutException as e:
            msg = f"Request timeout: {e}"
            raise OctavAPIError(msg) from e
        except httpx.HTTPStatusError as e:
            msg = f"HTTP error {e.response.status_code}: {e}"
            raise OctavAPIError(msg) from e
        except httpx.HTTPError as e:
            msg = f"HTTP request failed: {e}"
            raise OctavAPIError(msg) from e

    def check_credits(self) -> int:
        """
        Check remaining API credit balance (free endpoint).

        :returns: Number of remaining credits
        :raises OctavAPIError: If the API request fails
        """
        try:
            url = f"{self.base_url}/credits"
            response = self.client.get(url)
            response.raise_for_status()
            result = response.json()
            # Response may be raw int or wrapped in {"data": ...}
            if isinstance(result, (int, float)):
                return int(result)
            return int(result.get("data", result))

        except httpx.TimeoutException as e:
            msg = f"Request timeout: {e}"
            raise OctavAPIError(msg) from e
        except httpx.HTTPStatusError as e:
            msg = f"HTTP error {e.response.status_code}: {e}"
            raise OctavAPIError(msg) from e
        except httpx.HTTPError as e:
            msg = f"HTTP request failed: {e}"
            raise OctavAPIError(msg) from e

    def _parse_protocol_positions(
        self,
        protocol_key: str,
        protocol_data: dict[str, Any],
    ) -> list[Position]:
        """
        Parse assets from a single protocol into Position models.

        :param protocol_key: Octav protocol key (e.g., 'aave_v3', 'wallet')
        :param protocol_data: Protocol data dict with 'assets' list
        :returns: List of Position objects
        """
        positions = []
        assets = protocol_data.get("assets", [])

        for asset in assets:
            position = self._parse_single_asset(protocol_key, asset)
            if position:
                positions.append(position)

        return positions

    def _parse_single_asset(
        self,
        protocol_key: str,
        asset: dict[str, Any],
    ) -> Position | None:
        """
        Parse a single asset dict into a Position model.

        :param protocol_key: Protocol key
        :param asset: Asset data dict
        :returns: Position or None if parsing fails
        """
        try:
            symbol = asset.get("symbol", "UNKNOWN")
            balance_str = asset.get("balance", "0")
            value_str = asset.get("value", "0")
            price_str = asset.get("price", "0")
            contract_address = asset.get("contractAddress", "")
            chain_key = asset.get("chain", "ethereum")

            balance = Decimal(str(balance_str)) if balance_str else Decimal(0)
            usd_value = Decimal(str(value_str)) if value_str else Decimal(0)

            # Skip zero-value, zero-balance positions
            if balance == 0 and usd_value == 0:
                return None

            chain = self.REVERSE_CHAIN_MAPPING.get(chain_key, chain_key)

            token = Token(
                address=contract_address or "",
                symbol=symbol,
                decimals=18,  # Octav doesn't return decimals in portfolio
                name=symbol,
            )

            position_type = self._map_position_type(protocol_key, asset)

            metadata = {
                "octav_protocol": protocol_key,
                "price": str(price_str),
                "source": "octav",
            }

            return Position(
                protocol=protocol_key,
                chain=chain,
                position_type=position_type,
                token=token,
                balance=balance,
                usd_value=usd_value,
                metadata=metadata,
            )

        except Exception:
            return None

    def _map_position_type(
        self,
        protocol_key: str,
        asset: dict[str, Any],
    ) -> PositionType:
        """
        Map Octav protocol key and asset data to a PositionType.

        :param protocol_key: Protocol key (e.g., 'aave_v3')
        :param asset: Asset data dict
        :returns: Mapped PositionType
        """
        symbol = asset.get("symbol", "").lower()

        # Check for debt/borrow positions first
        if any(pattern in symbol for pattern in self._DEBT_SYMBOL_PATTERNS):
            return PositionType.LENDING_BORROW

        # Lending protocols → supply
        if any(protocol_key.startswith(p) for p in self._SUPPLY_INDICATORS):
            return PositionType.LENDING_SUPPLY

        # Staking protocols
        if any(protocol_key.startswith(p) for p in self._STAKING_PROTOCOLS):
            return PositionType.LIQUID_STAKING

        # Default to vault for other DeFi positions
        return PositionType.VAULT

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self) -> "OctavClient":
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
