"""Morpho GraphQL API client for fetching user positions."""

from decimal import Decimal
from typing import Any

import httpx

from crypto_portfolio_tracker.core.models import Position, PositionType, Token


class MorphoAPIError(Exception):
    """Exception raised for Morpho API errors."""


class MorphoGraphQLClient:
    """
    Client for Morpho GraphQL API.

    Fetches user positions from Morpho Blue markets and vaults across
    Ethereum and Base chains.

    Parameters
    ----------
    base_url : str
        GraphQL API endpoint URL
    timeout : float
        Request timeout in seconds

    """

    # Chain ID mapping
    CHAIN_IDS = {
        "ethereum": 1,
        "base": 8453,
    }

    # GraphQL query for user positions
    USER_POSITIONS_QUERY = """
    query GetUserPositions($chainId: Int!, $address: String!) {
      userByAddress(chainId: $chainId, address: $address) {
        address
        marketPositions {
          market {
            uniqueKey
            loanAsset {
              address
              symbol
              decimals
            }
            collateralAsset {
              address
              symbol
              decimals
            }
          }
          supplyShares
          supplyAssets
          supplyAssetsUsd
          borrowShares
          borrowAssets
          borrowAssetsUsd
          collateral
          collateralUsd
        }
        vaultPositions {
          vault {
            address
            name
            symbol
          }
          assets
          assetsUsd
          shares
        }
      }
    }
    """

    def __init__(
        self,
        base_url: str = "https://api.morpho.org/graphql",
        timeout: float = 30.0,
    ) -> None:
        """
        Initialize the Morpho GraphQL client.

        Parameters
        ----------
        base_url : str
            GraphQL API endpoint URL
        timeout : float
            Request timeout in seconds

        """
        self.base_url = base_url
        self.client = httpx.Client(timeout=timeout)

    def _execute_query(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Execute a GraphQL query.

        Parameters
        ----------
        query : str
            GraphQL query string
        variables : dict[str, Any] | None
            Query variables

        Returns
        -------
        dict[str, Any]
            Query response data

        Raises
        ------
        MorphoAPIError
            If the API request fails

        """
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        try:
            response = self.client.post(
                self.base_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            result = response.json()

            # Check for GraphQL errors
            if "errors" in result:
                error_messages = [e.get("message", "Unknown error") for e in result["errors"]]
                msg = f"GraphQL errors: {'; '.join(error_messages)}"
                raise MorphoAPIError(msg)

            return result.get("data", {})

        except httpx.TimeoutException as e:
            msg = f"Request timeout: {e}"
            raise MorphoAPIError(msg) from e
        except httpx.HTTPStatusError as e:
            msg = f"HTTP error {e.response.status_code}: {e}"
            raise MorphoAPIError(msg) from e
        except httpx.HTTPError as e:
            msg = f"HTTP request failed: {e}"
            raise MorphoAPIError(msg) from e

    def get_user_positions(
        self,
        user_address: str,
        chain: str,
    ) -> dict[str, Any]:
        """
        Fetch all Morpho positions for a user on a specific chain.

        Parameters
        ----------
        user_address : str
            User wallet address
        chain : str
            Chain name ('ethereum' or 'base')

        Returns
        -------
        dict[str, Any]
            Raw API response with user positions

        Raises
        ------
        ValueError
            If chain is not supported
        MorphoAPIError
            If the API request fails

        """
        chain_id = self.CHAIN_IDS.get(chain.lower())
        if chain_id is None:
            msg = f"Unsupported chain: {chain}. Supported: {list(self.CHAIN_IDS.keys())}"
            raise ValueError(msg)

        variables = {
            "chainId": chain_id,
            "address": user_address,
        }

        data = self._execute_query(self.USER_POSITIONS_QUERY, variables)
        return data.get("userByAddress", {})

    def get_positions_as_models(
        self,
        user_address: str,
        chain: str,
    ) -> list[Position]:
        """
        Fetch and convert Morpho positions to Position models.

        Parameters
        ----------
        user_address : str
            User wallet address
        chain : str
            Chain name ('ethereum' or 'base')

        Returns
        -------
        list[Position]
            List of Position objects

        """
        raw_data = self.get_user_positions(user_address, chain)
        positions = []

        # Process market positions (direct lending/borrowing)
        for market_pos in raw_data.get("marketPositions", []):
            positions.extend(self._parse_market_position(market_pos, chain))

        # Process vault positions
        for vault_pos in raw_data.get("vaultPositions", []):
            position = self._parse_vault_position(vault_pos, chain)
            if position:
                positions.append(position)

        return positions

    def _parse_market_position(
        self,
        market_pos: dict[str, Any],
        chain: str,
    ) -> list[Position]:
        """
        Parse a market position into Position models.

        Parameters
        ----------
        market_pos : dict[str, Any]
            Raw market position data
        chain : str
            Chain name

        Returns
        -------
        list[Position]
            List of positions (supply and/or borrow)

        """
        positions = []
        market = market_pos.get("market", {})
        market_key = market.get("uniqueKey", "")

        # Parse supply position
        supply_assets = market_pos.get("supplyAssets")
        if supply_assets and int(supply_assets) > 0:
            loan_asset = market.get("loanAsset", {})
            token = Token(
                address=loan_asset.get("address", ""),
                symbol=loan_asset.get("symbol", "UNKNOWN"),
                decimals=loan_asset.get("decimals", 18),
            )
            decimals = token.decimals
            balance = Decimal(supply_assets) / Decimal(10**decimals)
            usd_value = Decimal(str(market_pos.get("supplyAssetsUsd", 0)))

            positions.append(
                Position(
                    protocol="morpho",
                    chain=chain,
                    position_type=PositionType.LENDING_SUPPLY,
                    token=token,
                    balance=balance,
                    underlying_token=token,
                    underlying_balance=balance,
                    usd_value=usd_value,
                    metadata={
                        "market_id": market_key,
                        "supply_shares": market_pos.get("supplyShares"),
                        "position_type": "market_supply",
                    },
                )
            )

        # Parse borrow position
        borrow_assets = market_pos.get("borrowAssets")
        if borrow_assets and int(borrow_assets) > 0:
            loan_asset = market.get("loanAsset", {})
            token = Token(
                address=loan_asset.get("address", ""),
                symbol=loan_asset.get("symbol", "UNKNOWN"),
                decimals=loan_asset.get("decimals", 18),
            )
            decimals = token.decimals
            balance = Decimal(borrow_assets) / Decimal(10**decimals)
            usd_value = Decimal(str(market_pos.get("borrowAssetsUsd", 0)))

            positions.append(
                Position(
                    protocol="morpho",
                    chain=chain,
                    position_type=PositionType.LENDING_BORROW,
                    token=token,
                    balance=balance,
                    underlying_token=token,
                    underlying_balance=balance,
                    usd_value=usd_value,
                    metadata={
                        "market_id": market_key,
                        "borrow_shares": market_pos.get("borrowShares"),
                        "collateral": market_pos.get("collateral"),
                        "collateral_usd": market_pos.get("collateralUsd"),
                        "position_type": "market_borrow",
                    },
                )
            )

        return positions

    def _parse_vault_position(
        self,
        vault_pos: dict[str, Any],
        chain: str,
    ) -> Position | None:
        """
        Parse a vault position into a Position model.

        Parameters
        ----------
        vault_pos : dict[str, Any]
            Raw vault position data
        chain : str
            Chain name

        Returns
        -------
        Position | None
            Position object or None if no assets

        """
        assets = vault_pos.get("assets")
        if not assets or int(assets) == 0:
            return None

        vault = vault_pos.get("vault", {})

        # Vault token (the receipt token)
        vault_token = Token(
            address=vault.get("address", ""),
            symbol=vault.get("symbol", vault.get("name", "VAULT")),
            decimals=18,  # Vault shares typically use 18 decimals
            name=vault.get("name"),
        )

        shares = Decimal(str(vault_pos.get("shares", 0))) / Decimal(10**18)
        assets_decimal = Decimal(str(assets)) / Decimal(10**6)  # USDC has 6 decimals
        usd_value = Decimal(str(vault_pos.get("assetsUsd", 0)))

        return Position(
            protocol="morpho",
            chain=chain,
            position_type=PositionType.VAULT,
            token=vault_token,
            balance=shares,
            underlying_balance=assets_decimal,
            usd_value=usd_value,
            metadata={
                "vault_address": vault.get("address"),
                "vault_name": vault.get("name"),
                "shares_raw": vault_pos.get("shares"),
                "assets_raw": assets,
                "position_type": "vault",
            },
        )

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self) -> "MorphoGraphQLClient":
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
